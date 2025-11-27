# cogs/tickets/views/ticket_view.py
import discord
from discord.ext import commands
import config
from .ticket_controls import TicketControlView

class TicketView(discord.ui.View):
    def __init__(self, bot, category_id, staff_role_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.category_id = category_id
        self.staff_role_id = staff_role_id

    # --- Botão Abrir ---
    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket_button")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        category = guild.get_channel(self.category_id)
        member = interaction.user

        # Checa se já existe ticket
        if category:
            for channel in category.channels:
                # evita false positive: buscar por "-{member.id}"
                if f"-{member.id}" in channel.name:
                    return await interaction.followup.send(
                        "Você já possui um ticket aberto. Feche o anterior antes de abrir outro.",
                        ephemeral=True
                    )

        # Permissões
        staff_role = guild.get_role(self.staff_role_id)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        ticket_channel = await category.create_text_channel(
            name=f"ticket-{member.display_name.lower().replace(' ', '-')}-{member.id}",
            topic=f"Ticket de {member.display_name} | ID: {member.id}",
            overwrites=overwrites
        )

        # Embed de boas-vindas com botão fechar e staff
        embed = discord.Embed(
            title="👋 Ticket Aberto",
            description=(
                f"{member.mention}, este canal foi criado para suporte.\n\n"
                "Clique em **Fechar** quando finalizar para enviar seu feedback e gerar a transcrição.\n"
                "Moderadores podem acessar o painel STAFF para ações especiais."
            ),
            color=discord.Color.green()
        )
        view = TicketControlView(self.bot, ticket_channel, member, staff_role)
        await ticket_channel.send(embed=embed, view=view)

        await interaction.followup.send(f"Ticket criado: {ticket_channel.mention}", ephemeral=True)
        cog = self.bot.get_cog("TicketsCog")
        if cog:
            await cog.send_log("Ticket Aberto", ticket_channel, member)
