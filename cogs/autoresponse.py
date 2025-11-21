from discord.ext import commands
from config import CANAL_STATUS_ID

class AutoResponse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gatilhos = {
            "oi bot": "Oi! 😄",
            "como vai?": "Eu vou bem, e você?",
            "bobonicado": "Se o impossível aconteceu… foi coisa dele. 😎"
        }

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        conteudo = message.content.lower()
        for gatilho, resposta in self.gatilhos.items():
            if gatilho in conteudo:
                await message.channel.send(resposta)

async def setup(bot):
    await bot.add_cog(AutoResponse(bot))
