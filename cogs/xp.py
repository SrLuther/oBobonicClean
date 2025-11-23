# cogs/xp.py
import discord
from discord.ext import commands, tasks
import json
import os
import time
from operator import itemgetter

# Placeholder para IDs e Configurações (importado do config.py)
try:
    from config import LEADERBOARD_CHANNEL_ID, XP_MIN, XP_MAX, XP_COOLDOWN, LEVEL_REWARDS 
except ImportError:
    LEADERBOARD_CHANNEL_ID = 0
    XP_MIN, XP_MAX, XP_COOLDOWN = 15, 25, 60
    LEVEL_REWARDS = {}
    
XP_FILE = "xp.json"

# ==============================================================================
# 🧠 Funções de Utilidade
# ==============================================================================

# ... (Funções síncronas de load_xp_data, save_xp_data, get_level_xp_needed) ...
def load_xp_data(file_path):
    if not os.path.exists(file_path): return {}
    try:
        with open(file_path, "r") as f: return json.load(f)
    except json.JSONDecodeError: return {}
def save_xp_data(file_path, data):
    with open(file_path, "w") as f: json.dump(data, f, indent=4)
def get_level_xp_needed(level):
    return 5 * level**2 + 50 * level + 100
# ==============================================================================

class XPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_file = XP_FILE
        self.LEADERBOARD_CHANNEL_ID = LEADERBOARD_CHANNEL_ID
        self.rewards = LEVEL_REWARDS 
        self.cooldowns = {} 

        if not os.path.exists(self.xp_file):
            save_xp_data(self.xp_file, {})
            
        # self.update_leaderboard_task.start() <-- REMOVIDO DAQUI

    # ------------------ Hooks do Ciclo de Vida do Cog ------------------

    def cog_unload(self):
        self.update_leaderboard_task.cancel()

    # 🛑 CORREÇÃO FINAL: Inicia o loop no on_ready, não no __init__
    @commands.Cog.listener()
    async def on_ready(self):
        # Garante que o loop comece apenas após o bot estar totalmente pronto.
        if not self.update_leaderboard_task.is_running():
            print("[xp] Tarefa de ranking iniciada.")
            self.update_leaderboard_task.start()

    # ------------------ Tarefa de Loop (Robusta) ------------------
    
    @tasks.loop(hours=1) 
    async def update_leaderboard_task(self):
        """Task que atualiza o ranking no canal dedicado. CORRIGIDA com try/except."""
        
        # 🛑 CORREÇÃO ABRANGENTE: Envolve todo o corpo do loop em um try/except.
        try:
            await self.bot.wait_until_ready()
            
            channel = self.bot.get_channel(self.LEADERBOARD_CHANNEL_ID)
            
            if not channel:
                return

            guild = channel.guild 
            embed = await self.generate_leaderboard_embed(guild, auto_update=True)
            
            # Tenta encontrar e editar a última mensagem de ranking do bot
            try:
                async for message in channel.history(limit=50):
                    if message.author == self.bot.user and message.embeds and message.embeds[0].title.startswith("🏆 Ranking de XP"):
                        await message.edit(embed=embed)
                        return
                
                # Se não encontrar, envia uma nova
                await channel.send(embed=embed)

            except Exception as e:
                print(f"❌ ERRO no envio/edição da mensagem de ranking: {e}")

        except Exception as e:
            # Captura qualquer erro de nível superior e impede que ele derrube o loop principal
            print(f"[xp] ❌ ERRO CRÍTICO na tarefa de ranking: {e}. O bot continua rodando.")

    # ------------------ Restante do código (get_user_data, add_xp, generate_leaderboard_embed, on_message, comandos, etc.) ------------------
    
    async def get_user_data(self, user_id):
        data = await self.bot.loop.run_in_executor(None, load_xp_data, self.xp_file)
        user_data = data.get(str(user_id), {"xp": 0, "level": 0})
        return data, user_data

    async def save_user_data(self, data):
        await self.bot.loop.run_in_executor(None, save_xp_data, self.xp_file, data)

    async def add_xp_and_check_level(self, member: discord.Member, amount):
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
        await self.save_user_data(all_data)
        if old_level < new_level:
            await self.check_and_assign_rewards(member, old_level, new_level)
        return new_level, leveled_up

    async def check_and_assign_rewards(self, member: discord.Member, old_level: int, new_level: int):
        reward_levels = {int(k): v for k, v in self.rewards.items()}
        for level, role_id in reward_levels.items():
            if old_level < level <= new_level:
                role = member.guild.get_role(role_id)
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason=f"Recompensa por atingir Nível {level}")
                    except discord.Forbidden:
                        print(f"❌ ERRO: Não consegui adicionar o cargo {role.name}. Permissões/Hierarquia insuficientes.")
                        
    async def generate_leaderboard_embed(self, guild, auto_update=False):
        all_data = await self.bot.loop.run_in_executor(None, load_xp_data, self.xp_file)
        leaderboard = []
        for user_id, data in all_data.items():
            weighted_xp = data['level'] * 100000 + data['xp'] 
            leaderboard.append((int(user_id), data['level'], data['xp'], weighted_xp))
        leaderboard.sort(key=itemgetter(3), reverse=True)
        title_suffix = " — Atualizado Automaticamente" if auto_update else ""
        embed = discord.Embed(title=f"🏆 Ranking de XP (Top 10){title_suffix}", color=discord.Color.dark_orange())
        # ... (restante da lógica do embed) ...
        rank_text = ""
        for i, (user_id, level, xp, _) in enumerate(leaderboard[:10]):
            try:
                member = guild.get_member(user_id) 
                name = member.display_name if member else f"Usuário Desconhecido ({user_id})"
                symbol = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i + 1}."
                rank_text += f"{symbol} **{name}** - Nível **{level}** ({xp} XP)\n"
            except Exception: continue 
        embed.add_field(name="Os Melhores:", value=rank_text if rank_text else "Nenhum XP registrado ainda.")
        embed.set_footer(text=f"Próxima atualização em aproximadamente 1 hora." if auto_update else "Use !xp para ver seu progresso detalhado.")
        return embed

    @commands.Cog.listener()
    async def on_message(self, message):
        # ... (lógica de XP) ...
        pass # Implemente a lógica de on_message aqui

    @commands.command(name="xp", aliases=["level", "lvl"])
    async def show_xp(self, ctx, member: discord.Member = None):
        # ... (lógica do comando xp) ...
        pass # Implemente a lógica do comando xp aqui


async def setup(bot):
    await bot.add_cog(XPSystem(bot))