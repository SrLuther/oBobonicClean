import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
from config import (
    TICKET_CATEGORY_ID,
    TICKET_ARCHIVE_CHANNEL_ID,
    STAFF_ROLE_ID
)

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tickets = {}  # {channel_id: {"user": user_id, "opened_at": datetime, "claimed": moderator_id}}

    # Painel simples
    @app_commands.command(name="paineltickets", description="Envia o painel de tickets.")
    async def paineltickets(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="🎫 Sistema de Tickets",
            description=(
                "• **Para abrir um ticket**, clique no botão abaixo.\n"
                "• **Moderadores**: use o botão para ver tickets aguardando.\n\n"
                "Tempo máximo de inatividade: **48 horas**."
            ),
            color=discord.Color.blurple()
        )

        view = TicketPanelView()

        await interaction.response.send_message(embed=embed, view=view)

    # Comando oculto para moderadores abrirem a lista
    async def list_tickets(self, interaction: discord.Interaction):
        open_tickets = [
            f"<#{ch_id}> — Usuário: <@{info['user']}>"
            for ch_id, info in self.active_tickets.items()
            if info.get("claimed") is None
        ]

        if not open_tickets:
            await interaction.response.send_message("Nenhum ticket aguardando atendimento.", ephemeral=True)
            return

        msg = "**Tickets aguardando moderação:**\n" + "\n".join(open_tickets)
        await interaction.response.send_message(msg, ephemeral=True)

    # Criar o ticket
    async def create_ticket(self, interaction: discord.Interaction):

        category = interaction.guild.get_channel(TICKET_CATEGORY_ID)
        if category is None:
            await interaction.response.send_message("Categoria de tickets não encontrada!", ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await category.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites
        )

        self.active_tickets[channel.id] = {
            "user": interaction.user.id,
            "opened_at": datetime.now(),
            "claimed": None
        }

        # Botões dentro do ticket
        view = TicketRoomView(self, channel.id)

        embed = discord.Embed(
            title="🎫 Ticket Aberto",
            description="Aguarde um moderador aceitar seu ticket.\n\n"
                        "Moderadores: use o botão abaixo para aceitar.",
            color=discord.Color.green()
        )

        await channel.send(embed=embed, view=view)

        await interaction.response.send_message(
            f"Seu ticket foi criado: {channel.mention}",
            ephemeral=True
        )

        # Auto-fechamento por inatividade
        asyncio.create_task(self.auto_close_ticket(channel.id))

    # Moderador aceita
    async def claim_ticket(self, interaction: discord.Interaction, channel_id: int):

        if STAFF_ROLE_ID not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message("Somente moderadores podem aceitar tickets.", ephemeral=True)
            return

        ticket = self.active_tickets.get(channel_id)
        if ticket is None:
            await interaction.response.send_message("Ticket não encontrado!", ephemeral=True)
            return

        if ticket["claimed"] is not None:
            await interaction.response.send_message("Este ticket já foi aceito por outro moderador.", ephemeral=True)
            return

        ticket["claimed"] = interaction.user.id

        channel = interaction.guild.get_channel(channel_id)
        await channel.send(
            f"🔔 **Ticket aceito por:** <@{interaction.user.id}>"
        )

        await interaction.response.send_message("Você aceitou este ticket.", ephemeral=True)

    # Fechar manualmente
    async def close_ticket(self, interaction: discord.Interaction, channel_id: int):

        if STAFF_ROLE_ID not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message("Somente moderadores podem fechar tickets.", ephemeral=True)
            return

        await self.finish_ticket(interaction.guild, channel_id)
        await interaction.response.send_message("Ticket encerrado e arquivado.", ephemeral=True)

    # Função que realmente fecha e arquiva
    async def finish_ticket(self, guild, channel_id: int):

        ticket = self.active_tickets.pop(channel_id, None)
        if ticket is None:
            return

        channel = guild.get_channel(channel_id)
        if channel is None:
            return

        archive = guild.get_channel(TICKET_ARCHIVE_CHANNEL_ID)
        if archive:
            await archive.send(
                f"🗂️ Ticket encerrado: {channel.name}\n"
                f"Usuário: <@{ticket['user']}>"
            )

        await channel.delete()

    # Fechamento automático
    async def auto_close_ticket(self, channel_id: int):

        await asyncio.sleep(48 * 3600)

        ticket = self.active_tickets.get(channel_id)
        if ticket is None:
            return

        guild = self.bot.get_guild(list(self.bot.guilds)[0].id)
        await self.finish_ticket(guild, channel_id)


# -------------------- UI COMPONENTS --------------------

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green)
    async def open_ticket(self, interaction, button):
        await interaction.client.get_cog("TicketSystem").create_ticket(interaction)

    @discord.ui.button(label="Tickets Aguardando", style=discord.ButtonStyle.blurple)
    async def waiting(self, interaction, button):
        await interaction.client.get_cog("TicketSystem").list_tickets(interaction)


class TicketRoomView(discord.ui.View):
    def __init__(self, cog, channel_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id

    @discord.ui.button(label="Aceitar Ticket", style=discord.ButtonStyle.green)
    async def claim(self, interaction, button):
        await self.cog.claim_ticket(interaction, self.channel_id)

    @discord.ui.button(label="Fechar (Moderação)", style=discord.ButtonStyle.red)
    async def close(self, interaction, button):
        await self.cog.close_ticket(interaction, self.channel_id)


# -------------------- SETUP --------------------
async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
