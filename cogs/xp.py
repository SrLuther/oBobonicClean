# cogs/xp.py
import discord
from discord.ext import commands, tasks
import json
import os
from operator import itemgetter
import config
from typing import Optional, Any, Dict, Tuple, List
import asyncio
try:
    from utils.json_utils import load_json_async, save_json_async, load_json_sync, save_json_sync
except ImportError:
    # Fallback caso utils não esteja disponível
    def load_json_sync(file_path: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return default or {}
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception:
            return default or {}
    
    async def load_json_async(file_path: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return load_json_sync(file_path, default)
    
    def save_json_sync(file_path: str, data: Dict[str, Any], ensure_dir: bool = True) -> bool:
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False
    
    async def save_json_async(file_path: str, data: Dict[str, Any], ensure_dir: bool = True) -> bool:
        return save_json_sync(file_path, data, ensure_dir)

LEADERBOARD_CHANNEL_ID = config.LEADERBOARD_CHANNEL_ID
XP_MIN = config.XP_MIN
XP_MAX = config.XP_MAX
XP_COOLDOWN = config.XP_COOLDOWN
LEVEL_REWARDS = config.LEVEL_REWARDS

XP_FILE = "xp.json"

# Cache em memória para dados de XP (evita múltiplas leituras)
_xp_data_cache: Optional[Dict[str, Any]] = None
_xp_dirty = False
_xp_lock = asyncio.Lock()

def load_xp_data(file_path: str) -> Dict[str, Any]:
    """Versão síncrona para uso em thread executor."""
    global _xp_data_cache
    if _xp_data_cache is not None:
        return _xp_data_cache
    
    _xp_data_cache = load_json_sync(file_path, {})
    return _xp_data_cache

async def load_xp_data_async(file_path: str) -> Dict[str, Any]:
    """Versão assíncrona otimizada."""
    global _xp_data_cache
    if _xp_data_cache is not None:
        return _xp_data_cache
    
    _xp_data_cache = await load_json_async(file_path, {})
    return _xp_data_cache

async def save_xp_data_async(file_path: str, data: Dict[str, Any]) -> None:
    """Salva dados de XP de forma assíncrona com cache."""
    global _xp_data_cache, _xp_dirty
    async with _xp_lock:
        _xp_data_cache = data.copy()
        _xp_dirty = True
        await save_json_async(file_path, data)
        _xp_dirty = False

def save_xp_data(file_path: str, data: Dict[str, Any]) -> None:
    """Versão síncrona para uso em thread executor."""
    global _xp_data_cache, _xp_dirty
    _xp_data_cache = data.copy()
    _xp_dirty = True
    save_json_sync(file_path, data)
    _xp_dirty = False
def get_level_xp_needed(level: int) -> int:
    return 5 * level**2 + 50 * level + 100

class XPSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.xp_file: str = XP_FILE
        self.LEADERBOARD_CHANNEL_ID: int = LEADERBOARD_CHANNEL_ID
        self.rewards: Dict[int, int] = {int(k): int(v) for k, v in LEVEL_REWARDS.items()}
        self.cooldowns: Dict[int, float] = {}
        # Batch save para evitar escritas excessivas
        self._pending_saves: Dict[str, Dict[str, Any]] = {}
        self._save_task: Optional[asyncio.Task] = None

    async def cog_unload(self) -> None:
        """Cleanup ao descarregar o cog."""
        if hasattr(self, "update_leaderboard_task") and self.update_leaderboard_task.is_running():  # type: ignore
            self.update_leaderboard_task.cancel()  # type: ignore
        # Salva dados pendentes
        if self._pending_saves:
            await self._flush_pending_saves()
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass
    
    async def _flush_pending_saves(self) -> None:
        """Salva todos os dados pendentes."""
        if not self._pending_saves:
            return
        
        data = await load_xp_data_async(self.xp_file)
        data.update(self._pending_saves)
        await save_xp_data_async(self.xp_file, data)
        self._pending_saves.clear()
    
    async def _auto_save_task(self) -> None:
        """Task para salvar periodicamente os dados pendentes."""
        while True:
            try:
                await asyncio.sleep(60)  # Salva a cada minuto
                await self._flush_pending_saves()
            except asyncio.CancelledError:
                await self._flush_pending_saves()
                break
            except Exception as e:
                print(f"[xp] Erro no auto-save: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Inicia tasks ao bot ficar pronto."""
        if not hasattr(self, "update_leaderboard_task") or not self.update_leaderboard_task.is_running():  # type: ignore
            print("[xp] Tarefa de ranking iniciada.")
            self.update_leaderboard_task.start()  # type: ignore
        
        # Inicia task de auto-save
        if not self._save_task or self._save_task.done():
            self._save_task = asyncio.create_task(self._auto_save_task())

    @tasks.loop(hours=1)
    async def update_leaderboard_task(self) -> None:
        try:
            await self.bot.wait_until_ready()
            channel = self.bot.get_channel(self.LEADERBOARD_CHANNEL_ID)
            if not isinstance(channel, discord.TextChannel):
                return
            guild = channel.guild
            embed = await self.generate_leaderboard_embed(guild, auto_update=True)
            try:
                async for message in channel.history(limit=50):
                    if message.author == self.bot.user:
                        eb = message.embeds[0] if message.embeds else None
                        title = eb.title if eb else None
                        if isinstance(title, str) and title.startswith("🏆 Ranking de XP"):
                            await message.edit(embed=embed)
                            return
                await channel.send(embed=embed)
            except Exception as e:
                print(f"❌ ERRO no envio/edição da mensagem de ranking: {e}")
        except Exception as e:
            print(f"[xp] ❌ ERRO CRÍTICO na tarefa de ranking: {e}. O bot continua rodando.")

    async def get_user_data(self, user_id: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Obtém dados do usuário com cache otimizado."""
        data: Dict[str, Any] = await load_xp_data_async(self.xp_file)
        user_data: Dict[str, Any] = data.get(str(user_id), {"xp": 0, "level": 0})
        return data, user_data

    async def save_user_data(self, data: Dict[str, Any]) -> None:
        """Salva dados do usuário de forma assíncrona otimizada."""
        await save_xp_data_async(self.xp_file, data)

    async def add_xp_and_check_level(self, member: discord.Member, amount: int) -> Tuple[int, bool]:
        user_id = member.id
        all_data, user_data = await self.get_user_data(user_id)
        old_level = user_data["level"]
        user_data["xp"] += amount
        leveled_up = False
        while user_data["xp"] >= get_level_xp_needed(user_data["level"]):
            xp_needed = get_level_xp_needed(user_data["level"])
            user_data["xp"] -= xp_needed
            user_data["level"] += 1
            leveled_up = True
        new_level = user_data["level"]
        all_data[str(user_id)] = user_data
        # Usa save pendente para melhor performance
        self._pending_saves[str(user_id)] = user_data
        # Salva imediatamente apenas se subiu de nível (importante)
        if old_level < new_level:
            await self.save_user_data(all_data)
            await self.check_and_assign_rewards(member, old_level, new_level)
        return new_level, leveled_up

    async def check_and_assign_rewards(self, member: discord.Member, old_level: int, new_level: int) -> None:
        reward_levels = {int(k): v for k, v in self.rewards.items()}
        for level, role_id in reward_levels.items():
            if old_level < level <= new_level:
                role = member.guild.get_role(role_id)
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason=f"Recompensa por atingir Nível {level}")
                    except discord.Forbidden:
                        print(f"❌ ERRO: Não consegui adicionar o cargo {role.name}. Permissões/Hierarquia insuficientes.")

    async def generate_leaderboard_embed(self, guild: discord.Guild, auto_update: bool = False) -> discord.Embed:
        """Gera embed do leaderboard com cache otimizado."""
        all_data: Dict[str, Any] = await load_xp_data_async(self.xp_file)
        leaderboard: List[Tuple[int, int, int, int]] = []
        for user_id_str, data in all_data.items():
            uid = int(user_id_str)
            level = int(data.get('level', 0))
            xp = int(data.get('xp', 0))
            weighted_xp = level * 100000 + xp
            leaderboard.append((uid, level, xp, weighted_xp))
        leaderboard.sort(key=itemgetter(3), reverse=True)
        title_suffix = " — Atualizado Automaticamente" if auto_update else ""
        embed = discord.Embed(title=f"🏆 Ranking de XP (Top 10){title_suffix}", color=discord.Color.dark_orange())
        rank_text = ""
        for i, (user_id, level, xp, _) in enumerate(leaderboard[:10]):
            try:
                member = guild.get_member(user_id)
                name = member.display_name if member else f"Usuário Desconhecido ({user_id})"
                symbol = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i + 1}."
                rank_text += f"{symbol} **{name}** - Nível **{level}** ({xp} XP)\n"
            except Exception:
                continue
        embed.add_field(name="Os Melhores:", value=rank_text if rank_text else "Nenhum XP registrado ainda.")
        embed.set_footer(text=("Próxima atualização em aproximadamente 1 hora." if auto_update else "Use !xp para ver seu progresso detalhado."))
        return embed

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Implementação de XP deve ser adicionada conforme sua lógica original.
        pass

    @commands.command(name="xp", aliases=["level", "lvl"])
    async def show_xp(self, ctx: commands.Context[Any], member: Optional[discord.Member] = None):
        guild = getattr(ctx, "guild", None)
        target: Optional[discord.Member]
        if isinstance(member, discord.Member):
            target = member
        elif isinstance(ctx.author, discord.Member):
            target = ctx.author
        elif guild:
            target = guild.get_member(ctx.author.id)
        else:
            target = None
        if target is None:
            await ctx.send("❌ Não foi possível identificar o membro alvo.")
            return
        _data, user_data = await self.get_user_data(target.id)
        level = int(user_data.get("level", 0))
        xp = int(user_data.get("xp", 0))
        next_req = int(get_level_xp_needed(level))
        pct = 0 if next_req <= 0 else min(int((xp / next_req) * 100), 100)
        bar_len = 20
        filled = max(int((pct / 100) * bar_len), 0)
        bar = "█" * filled + "─" * (bar_len - filled)
        embed = discord.Embed(
            title=f"🏅 XP de {target.display_name}",
            color=discord.Color.dark_orange()
        )
        embed.add_field(name="Nível", value=str(level), inline=True)
        embed.add_field(name="XP", value=f"{xp}/{next_req}", inline=True)
        embed.add_field(name="Progresso", value=f"{pct}%\n`{bar}`", inline=False)
        embed.set_footer(text="Use o chat e voz para ganhar XP.")
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(XPSystem(bot))

# ============================================================
# Atualizado em: 2025-11-23 22:41:53 (Horário de Brasília)
# ============================================================
