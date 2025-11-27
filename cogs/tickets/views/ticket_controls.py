# cogs/tickets/views/ticket_controls.py
import discord
import asyncio
from .staff_actions import StaffPanelView
from ..modals.feedback_modal import FeedbackModal
import config

class TicketControlView(discord.ui.View):
    def __init__(self, bot, ticket_channel, member, staff_role):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_channel = ticket_channel
        self.member = member
        self.staff_role = staff_role

    # --- Botão Fechar ---
    @discord.ui.button(label="Fechar", style=discord.ButtonStyle.red, custom_id="close_ticket_button")
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Somente membro dono do ticket ou staff
        is_staff = False
        if self.staff_role:
            is_staff = self.staff_role in interaction.user.roles

        if self.member != interaction.user and not is_staff:
            return await interaction.response.send_message(
                "Você não tem permissão para fechar este ticket.", ephemeral=True
            )

        # Abre modal para feedback
        await interaction.response.send_modal(FeedbackModal(self.ticket_channel, interaction.user, self.bot))

    # --- Botão STAFF (somente moderador) ---
    @discord.ui.button(label="STAFF", style=discord.ButtonStyle.gray, custom_id="staff_ticket_button")
    async def staff_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_staff = False
        if self.staff_role:
            is_staff = self.staff_role in interaction.user.roles

        if not is_staff:
            return await interaction.response.send_message(
                "Somente moderadores podem acessar este painel.", ephemeral=True
            )

        view = StaffPanelView(self.bot, self.ticket_channel, self.member)
        await interaction.response.send_message("Painel STAFF aberto:", view=view, ephemeral=True)
