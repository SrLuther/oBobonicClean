from discord.ext import commands
import openai
import os
from config import CANAL_STATUS_ID

openai.api_key = os.getenv("OPENAI_API_KEY")

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ia")
    async def ai(self, ctx, *, prompt):
        await ctx.send("🤖 Processando...")

        try:
            resposta = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            conteudo = resposta["choices"][0]["message"]["content"]
            await ctx.send(conteudo)
        except Exception as e:
            await ctx.send(f"❌ Ocorreu um erro: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))
