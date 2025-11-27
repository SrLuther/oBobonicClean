# ============================================================
# cogs/tickets/tickets_controls.py
# Cog principal de Tickets
# ============================================================

import discord
from discord.ext import commands
import config
from .tickets_service import TicketsService
from .tickets_views import gerar_embed_painel, gerar_view_painel

class TicketsController(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.service = TicketsService(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        canal_painel = self.bot.get_channel(config.CANAL_PAINEL_ID)
        if canal_painel:
            await canal_painel.purge(limit=5)
            await canal_painel.send(embed=gerar_embed_painel(), view=gerar_view_painel())

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id")

        # Abrir ticket
        if custom_id == "abrir_ticket":
            await interaction.response.send_modal(
                self.service.FeedbackModal("novo_ticket", self.service)  # usa modal para descrição
            )

        # Fechar ticket
        elif custom_id == "fechar_ticket":
            ticket_id = interaction.channel.name.split(" ")[1]
            await self.service.fechar_ticket(interaction, ticket_id)

        # Assumir ticket
        elif custom_id == "assumir_ticket":
            ticket_id = interaction.channel.name.split(" ")[1]
            await self.service.assumir_ticket(interaction, ticket_id)
