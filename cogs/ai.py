from discord.ext import commands
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ia")
    async def ai(self, ctx, *, prompt):
        await ctx.send("🤖 Processando...")

        resposta = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        await ctx.send(resposta["choices"][0]["message"]["content"])

async def setup(bot):
    await bot.add_cog(AIChat(bot))
