from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def reload(self, ctx, nome):
        await self.bot.reload_extension(f"cogs.{nome}")
        await ctx.send(f"♻️ Cog `{nome}` recarregado!")

async def setup(bot):
    await bot.add_cog(Admin(bot))
