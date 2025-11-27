# cogs/tickets/views/staff_actions.py
import discord
import asyncio
import config
from ..utils.transcript import build_transcript

class StaffPanelView(discord.ui.View):
    def __init__(self, bot, ticket_channel, member):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_channel = ticket_channel
        self.member = member

    @discord.ui.button(label="SOLUCIONADO ✅", style=discord.ButtonStyle.green, custom_id="staff_solved")
    async def solved(self, interaction: discord.Interaction, button: discord.ui.Button):
        # abrir modal para feedback via STAFF (reaproveitar modal)
        await interaction.response.send_modal(await self._make_feedback_modal(interaction.user))

    @discord.ui.button(label="+ EQUIPE ⚠️", style=discord.ButtonStyle.blurple, custom_id="staff_team")
    async def extra_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"O ticket {self.ticket_channel.name} será revisado por outro moderador.",
            ephemeral=True
        )

    @discord.ui.button(label="ABANDONO 🚫", style=discord.ButtonStyle.red, custom_id="staff_abandon")
    async def abandon(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog("TicketsCog")
        if not cog:
            return await interaction.response.send_message("Cog não encontrado.", ephemeral=True)

        transcript_file = await cog.create_transcript(
            self.ticket_channel,
            feedback="Ticket encerrado por abandono.",
            closed_by=interaction.user.display_name
        )
        archive_channel = self.ticket_channel.guild.get_channel(config.TICKET_ARCHIVE_CHANNEL_ID)
        if archive_channel:
            await archive_channel.send(f"📜 Transcript do ticket {self.ticket_channel.name}", file=transcript_file)
        await cog.send_log("Ticket Encerrado (Abandono)", self.ticket_channel, interaction.user)
        await interaction.response.send_message("Ticket encerrado por abandono.", ephemeral=True)

    # Helper to create a modal similar to FeedbackModal but simple (avoids import circular)
    async def _make_feedback_modal(self, user):
        # Import local modal dinamicamente para evitar ciclo de import
        from ..modals.feedback_modal import FeedbackModal
        return FeedbackModal(self.ticket_channel, user, self.bot)
