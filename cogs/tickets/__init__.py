from .tickets_controller import TicketsController

async def setup(bot):
    await bot.add_cog(TicketsController(bot))
