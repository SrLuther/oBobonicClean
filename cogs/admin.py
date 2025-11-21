from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def reload(self, ctx, cog_name: str):
        """Recarrega um cog."""
        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await ctx.send(f"♻️ Cog `{cog_name}` recarregado com sucesso!")
            # Log para canal de status
            from config import CANAL_STATUS_ID
            canal_status = self.bot.get_channel(CANAL_STATUS_ID)
            if canal_status:
                await canal_status.send(f"🔄 Cog `{cog_name}` recarregado manualmente por {ctx.author.mention}")
        except Exception as e:
            await ctx.send(f"❌ Falha ao recarregar `{cog_name}`: {e}")

async def setup(bot):
    await bot.add_cog(Admin(bot))
