import discord
from discord.ext import commands
from datetime import datetime
import re

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Carregar palavrões do arquivo
        with open("palavroes.txt", "r", encoding="utf8") as f:
            self.badwords = [w.strip().lower() for w in f.readlines()]

    def get_log_channel(self, guild):
        return discord.utils.get(guild.text_channels, name="config")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignora o bot
        if message.author.bot:
            return
        
        log_channel = self.get_log_channel(message.guild)
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Filtro de convites
        convite_regex = r"(discord\.gg/|discord\.com/invite/)"
        if re.search(convite_regex, message.content.lower()):
            await message.delete()

            if log_channel:
                await log_channel.send(
                    f"🚫 **Convite bloqueado** ({now})\n"
                    f"👤 Usuário: {message.author.mention}\n"
                    f"📄 Mensagem:\n```{message.content}```"
                )

            await message.channel.send(f"{message.author.mention}, enviar convites é proibido.")
            return
        
        # Filtro de palavrões
        if any(bad in message.content.lower() for bad in self.badwords):
            await message.delete()

            if log_channel:
                await log_channel.send(
                    f"⚠ **Palavrão detectado** ({now})\n"
                    f"👤 Usuário: {message.author.mention}\n"
                    f"📄 Conteúdo removido:\n```{message.content}```"
                )

async def setup(bot):
    await bot.add_cog(Moderation(bot))
