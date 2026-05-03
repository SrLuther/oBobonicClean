# cogs/xp.py
import discord
from discord.ext import commands, tasks
import json
import os
from operator import itemgetter
import config
from typing import Optional, Any, Dict, Tuple, List
import asyncio
import time
import random
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

XP_MIN = config.XP_MIN
XP_MAX = config.XP_MAX
XP_COOLDOWN = config.XP_COOLDOWN
LEVEL_REWARDS = config.LEVEL_REWARDS
VOICE_XP_GAIN = config.VOICE_XP_GAIN
VOICE_XP_INTERVAL_MIN = config.VOICE_XP_INTERVAL_MIN
MOD_ROLE_IDS: List[int] = config.MOD_ROLE_IDS

XP_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".bancos", "xp.json")
_OLD_XP_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "xp.json")

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
    @commands.command(name="add_xp")
    @commands.has_permissions(administrator=True)
    async def add_xp(self, ctx: commands.Context, membro: discord.Member, xp: int):
        """Adiciona XP manualmente a um membro. Uso: !add_xp @membro 5000"""
        if xp <= 0:
            await ctx.send("❌ O valor de XP deve ser positivo.", delete_after=10)
            return
        new_level, leveled_up = await self.add_xp_and_check_level(membro, xp, source="admin")
        await ctx.send(f"✅ {xp} XP adicionados para {membro.mention}. Nível atual: {new_level}.")
        try:
            await membro.send(f"Você recebeu **{xp} XP** de um administrador no servidor!")
        except Exception:
            pass

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.xp_file: str = XP_FILE
        self.rewards: Dict[int, int] = {int(k): int(v) for k, v in LEVEL_REWARDS.items()}
        self.cooldowns: Dict[int, float] = {}
        # Batch save para evitar escritas excessivas
        self._pending_saves: Dict[str, Dict[str, Any]] = {}
        self._save_task: Optional[asyncio.Task] = None
        # XP por voz: controla quando cada membro entrou no canal (timestamp)
        self._voice_join_times: Dict[int, float] = {}
        # Task de startup
        self._startup_task: Optional[asyncio.Task] = None

    async def cog_load(self) -> None:
        """Inicia a task de startup ao cog ser carregado."""
        self._startup_task = asyncio.create_task(self._startup())
        print("[xp] 🚀 Task de startup criada.")

    async def cog_unload(self) -> None:
        """Cleanup ao descarregar o cog."""
        if self._startup_task and not self._startup_task.done():
            self._startup_task.cancel()
        if self.voice_xp_task.is_running():
            self.voice_xp_task.cancel()
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

    async def _startup(self) -> None:
        """Task de startup: aguarda bot pronto, envia painel e inicia tasks."""
        try:
            await self.bot.wait_until_ready()
            print("[xp] ⏳ Bot pronto! Iniciando XP startup...")

            # Migra xp.json antigo para .bancos/xp.json se necessário
            if os.path.isfile(_OLD_XP_FILE) and not os.path.isfile(self.xp_file):
                try:
                    import shutil
                    os.makedirs(os.path.dirname(self.xp_file), exist_ok=True)
                    shutil.copy2(_OLD_XP_FILE, self.xp_file)
                    # Invalida cache para forçar leitura do novo arquivo
                    global _xp_data_cache
                    _xp_data_cache = None
                    print(f"[xp] 📦 xp.json migrado para {self.xp_file}")
                except Exception as e:
                    print(f"[xp] ⚠️ Falha ao migrar xp.json: {e}")

            # Registra membros já em voz
            for guild in self.bot.guilds:
                for vc in guild.voice_channels:
                    for member in vc.members:
                        if not member.bot:
                            self._voice_join_times.setdefault(member.id, time.time())

            # Inicia task de auto-save
            if not self._save_task or self._save_task.done():
                self._save_task = asyncio.create_task(self._auto_save_task())

            # Inicia tasks
            if not self.voice_xp_task.is_running():
                self.voice_xp_task.start()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[xp] ❌ Erro no startup: {e}")
            import traceback
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_ready(self):
        """Reinicia tasks se o bot reconectar (apenas voz — ranking é gerido pelo _startup)."""
        if not self.voice_xp_task.is_running():
            self.voice_xp_task.start()

    # ─────────────────────────────────────────────────────────────
    # XP POR VOZ — a cada VOICE_XP_INTERVAL_MIN minutos
    # ─────────────────────────────────────────────────────────────

    @tasks.loop(minutes=VOICE_XP_INTERVAL_MIN)
    async def voice_xp_task(self) -> None:
        """Concede XP a todos os membros em canais de voz a cada intervalo."""
        now = time.time()
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                # Filtra: ignora bots e membros sozinhos (opcional: pode remover essa regra)
                humans = [m for m in vc.members if not m.bot]
                if not humans:
                    continue
                for member in humans:
                    # Garante que o membro está registrado (pode ter entrado antes do on_ready)
                    self._voice_join_times.setdefault(member.id, now)
                    _, leveled_up = await self.add_xp_and_check_level(member, random.randint(30, 60), source="voice")
                    if leveled_up:
                        try:
                            await member.send(
                                f"🎙️ Você subiu de nível enquanto estava em voz! "
                                f"Use `!xp` no servidor para ver seu progresso."
                            )
                        except discord.Forbidden:
                            pass

    @voice_xp_task.before_loop
    async def before_voice_xp_task(self):
        await self.bot.wait_until_ready()

    # ─────────────────────────────────────────────────────────────
    # EVENTOS DE VOZ — rastreia entrada/saída
    # ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot:
            return
        # Entrou em um canal de voz
        if before.channel is None and after.channel is not None:
            self._voice_join_times[member.id] = time.time()
        # Saiu de todos os canais
        elif before.channel is not None and after.channel is None:
            self._voice_join_times.pop(member.id, None)

    async def get_user_data(self, user_id: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Obtém dados do usuário com cache otimizado."""
        data: Dict[str, Any] = await load_xp_data_async(self.xp_file)
        user_data: Dict[str, Any] = data.get(str(user_id), {"xp": 0, "level": 0})
        return data, user_data

    async def save_user_data(self, data: Dict[str, Any]) -> None:
        """Salva dados do usuário de forma assíncrona otimizada."""
        await save_xp_data_async(self.xp_file, data)

    async def add_xp_and_check_level(self, member: discord.Member, amount: int, source: str = "message") -> Tuple[int, bool]:
        user_id = member.id
        all_data, user_data = await self.get_user_data(user_id)
        old_level = user_data["level"]
        user_data["xp"] += amount
        # Rastreia totais separados por fonte (para ranking ponderado)
        if source == "voice":
            user_data["voice_xp_total"] = user_data.get("voice_xp_total", 0) + amount
        else:
            user_data["message_xp_total"] = user_data.get("message_xp_total", 0) + amount
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
            # Notifica o RankingCog para atualizar o painel
            ranking_cog = self.bot.get_cog("RankingCog")
            if ranking_cog:
                try:
                    await ranking_cog.update(member.guild)  # type: ignore
                except Exception:
                    pass
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

    # ─────────────────────────────────────────────────────────────
    # XP POR MENSAGEM
    # ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        if not isinstance(message.author, discord.Member):
            return

        user_id = message.author.id
        now = time.time()
        last = self.cooldowns.get(user_id, 0.0)

        if now - last < XP_COOLDOWN:
            return

        self.cooldowns[user_id] = now
        xp_gain = random.randint(XP_MIN, XP_MAX)
        new_level, leveled_up = await self.add_xp_and_check_level(message.author, xp_gain)

        if leveled_up:
            try:
                await message.channel.send(
                    f"🎉 Parabéns {message.author.mention}! Você atingiu o **Nível {new_level}**!",
                    delete_after=15,
                )
            except discord.Forbidden:
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
        faltam = next_req - xp
        pct = 0 if next_req <= 0 else min(int((xp / next_req) * 100), 100)
        bar_len = 20
        filled = max(int((pct / 100) * bar_len), 0)
        bar = "█" * filled + "─" * (bar_len - filled)

        # Posição no ranking geral
        posicao = None
        if guild:
            from cogs.ranking import compute_scores, RANKING_EXCLUDED_IDS
            all_scores = compute_scores(guild)
            scores = [s for s in all_scores if s[0] not in RANKING_EXCLUDED_IDS]
            for idx, (uid, *_) in enumerate(scores):
                if uid == target.id:
                    posicao = idx + 1
                    break

        titulo = f"🏅 {target.display_name}"
        if posicao:
            titulo += f"  —  #{posicao}º no ranking"

        embed = discord.Embed(title=titulo, color=discord.Color.dark_orange())
        embed.add_field(name="Nível", value=f"**{level}**", inline=True)
        embed.add_field(name="XP atual", value=f"**{xp}** / {next_req}", inline=True)
        embed.add_field(name="Falta para o próximo nível", value=f"**{faltam} XP** ({pct}%)\n`{bar}`", inline=False)
        embed.set_footer(text="Use o chat e voz para ganhar XP.")
        await ctx.send(embed=embed)

    @commands.command(name="xphelp", aliases=["ajudaxp", "xpajuda"])
    async def xp_help(self, ctx: commands.Context[Any]):
        """
        Mostra explicação detalhada de como funciona o sistema de XP, níveis e ranking.
        """
        texto = (
            "**Como funciona o XP e Ranking:**\n"
            "\n"
            "**XP por Mensagens:**\n"
            "- Cada mensagem enviada (máx. 1 por minuto) concede um valor aleatório entre **15 e 25 XP**.\n"
            "- Se enviar várias mensagens em menos de 1 minuto, só a primeira conta para XP.\n"
            "\n"
            "**XP por Voz:**\n"
            "- A cada 5 minutos, todos que estiverem em um canal de voz ganham um valor aleatório entre **30 e 60 XP**.\n"
            "- Basta estar presente no momento da varredura para receber.\n"
            "- Não precisa estar desde a varredura anterior.\n"
            "\n"
            "**Indicações (Convites):**\n"
            "- Cada indicação aprovada (quando alguém usa seu convite e é validado) vale **5.000 pontos** no ranking.\n"
            "- Indicações só contam após aprovação manual pela staff.\n"
            "- Veja seu total de indicações no painel do ranking.\n"
            "\n"
            "**Evento Rotativo:**\n"
            "- Durante eventos especiais (ex: Treasure Hunt), você pode acumular pontos participando das atividades do evento.\n"
            "- Cada ponto de evento conquistado vale **500 pontos** no ranking.\n"
            "- Quanto mais você participar e pontuar no evento, mais pontos de ranking irá ganhar.\n"
            "- Os eventos são anunciados no Discord e têm regras próprias.\n"
            "- Sua pontuação de evento aparece no ranking enquanto durar o evento.\n"
            "\n"
            "**Cálculo do Ranking:**\n"
            "- O ranking soma: XP de mensagens, XP de voz (com peso 0,3), indicações aprovadas e pontos de evento.\n"
            "- Fórmula: (nível × 100.000) + XP mensagens + (XP voz × 0,3) + indicações × 5.000 + evento × 500.\n"
            "\n"
            "**Premiação:**\n"
            "- Top 10 do ranking recebe pontos na loja do jogo todo mês.\n"
            "- Premiação entregue entre os dias 1 e 3 de cada mês.\n"
            "\n"
            "Use `!xp` para ver seu progresso ou `!ranking` para ver o painel geral."
        )
        # Sempre envia no canal, menciona o usuário e apaga após 60s
        try:
            msg = await ctx.send(f"{ctx.author.mention} {texto}")
            await asyncio.sleep(60)
            await msg.delete()
            try:
                await ctx.message.delete()
            except Exception:
                pass
        except Exception:
            pass
        return

async def setup(bot: commands.Bot):
    await bot.add_cog(XPSystem(bot))

# ============================================================
# Atualizado em: 2025-11-23 22:41:53 (Horário de Brasília)
# ============================================================
