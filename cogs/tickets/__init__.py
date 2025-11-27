# ============================================================
# cogs/tickets/__init__.py
# Inicializa o pacote tickets
# ============================================================

from .tickets_controls import TicketsController

async def setup(bot):
    await bot.add_cog(TicketsController(bot))
