import discord
from discord.ext import commands
from discord import app_commands

from .tickets_service import TicketsService
from .tickets_views import gerar_embed_ticket, gerar_view_ticket
from .tickets_utils import gerar_id_ticket_formato

class TicketsController(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.service = TicketsService(bot)

    # ============================================
    # Slash Command principal: /ticket
    # ============================================
    @app_commands.command(name="ticket", description="Abre um ticket privado com a staff.")
    async def abrir_ticket(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        canal = await self.service.criar_ticket(interaction)

        if canal:
            await interaction.followup.send(
                f"Seu ticket foi criado: {canal.mention}",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ Ocorreu um erro ao criar seu ticket.", ephemeral=True
            )

    # ============================================
    # Botão: Encerrar ticket
    # ============================================
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id")

            if custom_id == "fechar_ticket":
                await self.service.encerrar_ticket(interaction)
            elif custom_id == "confirmar_encerramento":
                await self.service.confirmar_fechamento(interaction)
