import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
import random
import time
from operator import itemgetter
# Importa todas as configurações de XP e Ranking do config.py
from config import LEADERBOARD_CHANNEL_ID, XP_MIN, XP_MAX, XP_COOLDOWN, LEVEL_REWARDS 

# Nome do arquivo de dados (Será criado na pasta raiz)
XP_FILE = "xp.json"

# ==============================================================================
# 🧠 Funções de Utilidade (Síncronas para Executor)
# ==============================================================================

def load_xp_data(file_path):
    """Carrega dados de XP de forma síncrona."""
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_xp_data(file_path, data):
    """Salva dados de XP de forma síncrona."""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def get_level_xp_needed(level):
    """Fórmula de XP necessária para o próximo nível (5*L^2 + 50*L + 100)."""
    return 5 * level**2 + 50 * level + 100

# ==============================================================================
# ⭐ CLASSE PRINCIPAL: XPSystem
# ==============================================================================
class XPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_file = XP_FILE
        self.LEADERBOARD_CHANNEL_ID = LEADERBOARD_CHANNEL_ID
        self.rewards = LEVEL_REWARDS 
        
        # Dicionário para rastrear o último momento em que um usuário ganhou XP
        self.cooldowns = {} 

        if not os.path.exists(self.xp_file):
            save_xp_data(self.xp_file, {})
            
        self.update_leaderboard_task.start()

    # ------------------ Hooks do Ciclo de Vida do Cog ------------------

    def cog_unload(self):
        self.update_leaderboard_task.cancel()

    @tasks.loop(hours=1) # Executa a cada 1 hora
    async def update_leaderboard_task(self):
        """Task que atualiza o ranking no canal dedicado."""
        
        await self.bot.wait_until_ready()
        
        channel = self.bot.get_channel(self.LEADERBOARD_CHANNEL_ID)
        
        if not channel:
            return

        guild = channel.guild 
        embed = await self.generate_leaderboard_embed(guild, auto_update=True)
        
        try:
            # Tenta encontrar e editar a última mensagem de ranking do bot
            async for message in channel.history(limit=50):
                if message.author == self.bot.user and message.embeds and message.embeds[0].title.startswith("🏆 Ranking de XP"):
                    await message.edit(embed=embed)
                    return
            
            # Se não encontrar, envia uma nova
            await channel.send(embed=embed)

        except Exception as e:
            print(f"❌ ERRO no loop de atualização de ranking: {e}")

    # ------------------ Operações de Dados ------------------

    async def get_user_data(self, user_id):
        data = await self.bot.loop.run_in_executor(None, load_xp_data, self.xp_file)
        user_data = data.get(str(user_id), {"xp": 0, "level": 0})
        return data, user_data

    async def save_user_data(self, data):
        await self.bot.loop.run_in_executor(None, save_xp_data, self.xp_file, data)

    # ------------------ Lógica de Level Up com Recompensas ------------------

    async def add_xp_and_check_level(self, member: discord.Member, amount):
        """Adiciona XP, verifica o nível e aplica as recompensas de cargo."""
        
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
        
        # 🏅 Lógica de Atribuição de Cargo 
        if old_level < new_level:
            await self.check_and_assign_rewards(member, old_level, new_level)
        
        return new_level, leveled_up

    async def check_and_assign_rewards(self, member: discord.Member, old_level: int, new_level: int):
        """Verifica quais cargos o membro deve receber."""
        
        reward_levels = {int(k): v for k, v in self.rewards.items()}
        
        for level, role_id in reward_levels.items():
            if old_level < level <= new_level:
                role = member.guild.get_role(role_id)
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason=f"Recompensa por atingir Nível {level}")
                        await member.send(f"🎉 **Parabéns!** Você atingiu o Nível **{level}** e recebeu o cargo **{role.name}** no servidor {member.guild.name}!")
                    except discord.Forbidden:
                        print(f"❌ ERRO: Não consegui adicionar o cargo {role.name}. Permissões/Hierarquia insuficientes.")
                        
    # ------------------ Lógica de Geração do Ranking ------------------
    
    async def generate_leaderboard_embed(self, guild, auto_update=False):
        """Função reutilizável para gerar o Embed do Top 10."""
        all_data = await self.bot.loop.run_in_executor(None, load_xp_data, self.xp_file)

        leaderboard = []
        for user_id, data in all_data.items():
            weighted_xp = data['level'] * 100000 + data['xp'] 
            leaderboard.append((int(user_id), data['level'], data['xp'], weighted_xp))

        leaderboard.sort(key=itemgetter(3), reverse=True)
        
        title_suffix = " — Atualizado Automaticamente" if auto_update else ""
        
        embed = discord.Embed(
            title=f"🏆 Ranking de XP (Top 10){title_suffix}",
            description=(
                f"O XP é conquistado por **atividade no chat**. Você ganha **{XP_MIN} a {XP_MAX} XP** "
                f"a cada **{XP_COOLDOWN} segundos** que envia uma mensagem."
            ),
            color=discord.Color.dark_orange()
        )
        
        rank_text = ""
        for i, (user_id, level, xp, _) in enumerate(leaderboard[:10]):
            try:
                member = guild.get_member(user_id) 
                name = member.display_name if member else f"Usuário Desconhecido ({user_id})"
                
                if i == 0: symbol = "🥇"
                elif i == 1: symbol = "🥈"
                elif i == 2: symbol = "🥉"
                else: symbol = f"{i + 1}."

                rank_text += f"{symbol} **{name}** - Nível **{level}** ({xp} XP)\n"
            except Exception:
                continue 
        
        embed.add_field(name="Os Melhores:", value=rank_text if rank_text else "Nenhum XP registrado ainda.")
        embed.set_footer(text=f"Próxima atualização em aproximadamente 1 hora." if auto_update else "Use !xp para ver seu progresso detalhado.")
        
        return embed

    # ------------------ Listener de Mensagens com Cooldown ------------------

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.startswith(self.bot.command_prefix) or len(message.content) < 3:
            return
        
        user_id = message.author.id
        current_time = time.time()
        
        # Verifica o cooldown
        if user_id in self.cooldowns and (current_time - self.cooldowns[user_id] < XP_COOLDOWN):
            return
            
        self.cooldowns[user_id] = current_time
        xp_gain = random.randint(XP_MIN, XP_MAX)
        
        # Chama a função passando o objeto Member para a lógica de recompensa
        new_level, leveled_up = await self.add_xp_and_check_level(message.author, xp_gain)
        
        if leveled_up:
            xp_next = get_level_xp_needed(new_level)
            await message.channel.send(
                f"🎉 **PARABÉNS** {message.author.mention}! Você alcançou o **Nível {new_level}**! "
                f"Próximo nível em {xp_next} XP."
            )

    # ------------------ Comandos ------------------

    @commands.command(name="xp", aliases=["level", "lvl"])
    async def show_xp(self, ctx, member: discord.Member = None):
        """Mostra o nível e o XP de um usuário ou o seu próprio."""
        member = member or ctx.author
        
        _, user_data = await self.get_user_data(member.id)
        
        level = user_data["level"]
        xp_current = user_data["xp"]
        xp_needed = get_level_xp_needed(level)

        if level == 0 and xp_current == 0:
            await ctx.send(f"**{member.display_name}** ainda não ganhou XP.")
            return

        embed = discord.Embed(
            title=f"⭐ Progresso de XP de {member.display_name}",
            color=discord.Color.gold()
        )
        embed.add_field(name="Nível Atual", value=f"**{level}**", inline=True)
        embed.add_field(name="XP Acumulado", value=f"**{xp_current}**", inline=True)
        embed.add_field(name="XP Total para o Nível", value=f"**{xp_needed}**", inline=False)
        
        progress = int((xp_current / xp_needed) * 20)
        bar = "█" * progress + "░" * (20 - progress)
        embed.add_field(name="Progresso", value=f"`{bar}` ({xp_current}/{xp_needed} XP)", inline=False)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)


    @commands.command(name="rank", aliases=["topxp", "ranking"])
    async def show_rank(self, ctx):
        """Mostra os usuários com mais XP no servidor (Top 10) sob demanda."""
        await ctx.send("⏳ Gerando ranking...")
        embed = await self.generate_leaderboard_embed(ctx.guild)
        await ctx.send(embed=embed)
        
    @commands.command(name="xpinfo", aliases=["regrasxp"])
    async def xp_rules(self, ctx):
        """Explica as regras de contabilização do XP e do sistema de níveis."""
        xp_next_lvl = get_level_xp_needed(0)
        
        embed = discord.Embed(
            title="📜 Regras do Sistema de XP e Nível",
            description="Entenda como você pode subir no ranking do servidor!",
            color=discord.Color.dark_teal()
        )
        
        embed.add_field(
            name="Ganhando XP (Atividade)",
            value=(
                f"Você ganha **{XP_MIN} a {XP_MAX} XP** ao enviar uma mensagem válida no chat.\n"
                f"**Regra Anti-Spam:** Você só pode ganhar XP novamente após **{XP_COOLDOWN} segundos** da última vez que ganhou."
            ),
            inline=False
        )
        
        embed.add_field(
            name="Subindo de Nível",
            value=(
                f"O XP necessário para subir de nível é crescente, seguindo a fórmula `5*L² + 50*L + 100`.\n"
                f"Para ir do Nível 0 ao Nível 1, são necessários **{xp_next_lvl} XP**."
            ),
            inline=False
        )
        
        embed.add_field(
            name="Onde Ver?",
            value="Use `!xp` para ver seu progresso e `!rank` para ver o Top 10 atual."
        )
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(XPSystem(bot))