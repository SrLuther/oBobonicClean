# cogs/moderation.py
import discord
from discord.ext import commands
import os
from datetime import datetime

PALAVROES_FILE = "palavroes.txt"
CONFIG_CHANNEL_NAME = "config"  # nome do canal de logs

def carregar_palavroes():
    if not os.path.exists(PALAVROES_FILE):
        return []
    with open(PALAVROES_FILE, "r", encoding="utf-8") as f:
        return [l.strip().lower() for l in f if l.strip()]

def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.palavroes = carregar_palavroes()

    @commands.Cog.listener()
    async def on_message(self, message):
        # evita processar mensagens de bots
        if message.author.bot:
            return

        content = message.content or ""
        content_lower = content.lower()

        # recarrega lista a cada mensagem (permitir editar arquivo sem reiniciar)
        self.palavroes = carregar_palavroes()

        log_channel = discord.utils.get(message.guild.text_channels, name=CONFIG_CHANNEL_NAME)

        # Verifica convites do discord
        if "discord.gg/" in content_lower or "discord.com/invite/" in content_lower:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            except Exception:
                pass

            try:
                await message.channel.send(f"🚫 {message.author.mention}, é proibido enviar convites para outros servidores aqui.")
            except:
                pass

            if log_channel:
                await log_channel.send(f"[{agora()}] 🔗 Convite bloqueado por {message.author} ({message.author.id}) em {message.channel.mention}:\n`{content}`")
            return

        # Verifica palavrões (substring match)
        if any(p in content_lower for p in self.palavroes if p):
            try:
                await message.delete()
            except:
                pass

            try:
                await message.channel.send(f"🧹 {message.author.mention} Calma lá, pega leve nas palavras! 😊")
            except:
                pass

            if log_channel:
                await log_channel.send(f"[{agora()}] 🚨 Palavra proibida detectada por {message.author} ({message.author.id}) em {message.channel.mention}:\n`{content}`")
            return

        # permite que comandos sejam processados por outros handlers
        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
