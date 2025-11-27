# ============================================================
# cogs/tickets/__init__.py
# Inicializa o pacote tickets
# ============================================================

from .tickets_controls import TicketsController  # agora aponta para o arquivo correto

async def setup(bot):
    await bot.add_cog(TicketsController(bot))
