from discord.ext import commands
import discord
import re
from datetime import datetime
from config import CANAL_STATUS_ID

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("palavroes.txt", "r", encoding="utf8") as f:
            self.badwords = [w.strip().lower() for w in f.readlines()]

    def get_log_channel(self, guild):
        return self.bot.get_channel(CANAL_STATUS_ID)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        log_channel = self.get_log_channel(message.guild)
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Bloqueio de convites
        convite_regex = r"(discord\.gg/|discord\.com/invite/)"
        if re.search(convite_regex, message.content.lower()):
            await message.delete()
            if log_channel:
                await log_channel.send(f"🚫 Convite bloqueado ({now}) de {message.author.mention}:\n`{message.content}`")
            await message.channel.send(f"{message.author.mention}, enviar convites é proibido.")
            return

        # Bloqueio de palavrões
        if any(bad in message.content.lower() for bad in self.badwords):
            await message.delete()
            if log_channel:
                await log_channel.send(f"⚠ Palavrão detectado ({now}) de {message.author.mention}:\n`{message.content}`")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
