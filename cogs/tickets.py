import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime
from config import TICKET_CATEGORY_ID, TICKET_ARCHIVE_CHANNEL_ID, STAFF_ROLE_ID, CANAL_STATUS_ID

# ID do canal específico para enviar o painel de tickets
TICKET_CHANNEL_ID = 1440909767974453328

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tickets = {}

    # -------------------- Comando prefixado apenas para moderadores --------------------
    @commands.command(name="ticket")
    @commands.has_role(STAFF_ROLE_ID)
    async def ticket(self, ctx):
        if ctx.channel.id != TICKET_CHANNEL_ID:
            await ctx.send(f"❌ Este comando só pode ser usado no canal <#{TICKET_CHANNEL_ID}>.", delete_after=10)
            await ctx.message.delete()
            return

        embed = discord.Embed(
            title="🎫 Sistema de Tickets",
            description=(
                "• Clique no botão abaixo para abrir um ticket.\n"
                "• Moderadores podem aceitar e fechar tickets.\n"
                "• Tempo máximo de inatividade: 48h.\n\n"
                "Se precisar de ajuda, aguarde um moderador aceitar seu ticket."
            ),
            color=discord.Color.blurple()
        )
        view = TicketPanelView()
        message = await ctx.send(embed=embed, view=view)
        await message.pin()
        await ctx.message.delete()

    # -------------------- Comando slash --------------------
    @app_commands.command(name="paineltickets", description="Envia o painel de tickets.")
    async def paineltickets(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎫 Sistema de Tickets",
            description="• Clique para abrir um ticket.\n• Moderadores podem aceitar tickets.\nTempo máximo de inatividade: 48h.",
            color=discord.Color.blurple()
        )
        view = TicketPanelView()
        await interaction.response.send_message(embed=embed, view=view)

    # -------------------- Funções internas --------------------
    async def create_ticket(self, interaction: discord.Interaction):
        category = interaction.guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("Categoria de tickets não encontrada!", ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True)
        }

        channel = await category.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites
        )
        self.active_tickets[channel.id] = {"user": interaction.user.id, "opened_at": datetime.now(), "claimed": None}

        view = TicketRoomView(self, channel.id)
        embed = discord.Embed(title="🎫 Ticket Aberto", description="Aguarde um moderador aceitar seu ticket.", color=discord.Color.green())
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Seu ticket foi criado: {channel.mention}", ephemeral=True)

        # Log
        log_channel = self.bot.get_channel(CANAL_STATUS_ID)
        if log_channel:
            await log_channel.send(f"🟢 Ticket criado: {channel.name} por {interaction.user.mention}")

        asyncio.create_task(self.auto_close_ticket(channel.id))

    async def claim_ticket(self, interaction: discord.Interaction, channel_id: int):
        ticket = self.active_tickets.get(channel_id)
        if not ticket:
            await interaction.response.send_message("Ticket não encontrado!", ephemeral=True)
            return
        if ticket["claimed"] is not None:
            await interaction.response.send_message("Este ticket já foi aceito.", ephemeral=True)
            return

        ticket["claimed"] = interaction.user.id
        channel = interaction.guild.get_channel(channel_id)
        await channel.send(f"🔔 Ticket aceito por {interaction.user.mention}")
        await interaction.response.send_message("Você aceitou este ticket.", ephemeral=True)

        log_channel = self.bot.get_channel(CANAL_STATUS_ID)
        if log_channel:
            await log_channel.send(f"🟡 Ticket {channel.name} aceito por {interaction.user.mention}")

    async def close_ticket(self, interaction: discord.Interaction, channel_id: int):
        ticket = self.active_tickets.get(channel_id)
        if not ticket:
            await interaction.response.send_message("Ticket não encontrado!", ephemeral=True)
            return

        await self.finish_ticket(interaction.guild, channel_id)
        await interaction.response.send_message("Ticket encerrado e arquivado.", ephemeral=True)

    async def finish_ticket(self, guild, channel_id: int):
        ticket = self.active_tickets.pop(channel_id, None)
        if not ticket:
            return

        channel = guild.get_channel(channel_id)
        archive = guild.get_channel(TICKET_ARCHIVE_CHANNEL_ID)
        if archive:
            await archive.send(f"🗂️ Ticket encerrado: {channel.name}\nUsuário: <@{ticket['user']}>")
        if channel:
            await channel.delete()

        # Log
        log_channel = self.bot.get_channel(CANAL_STATUS_ID)
        if log_channel:
            await log_channel.send(f"🔴 Ticket {channel.name} fechado e arquivado.")

    async def auto_close_ticket(self, channel_id: int):
        await asyncio.sleep(48 * 3600)
        ticket = self.active_tickets.get(channel_id)
        if ticket:
            guild = self.bot.get_guild(list(self.bot.guilds)[0].id)
            await self.finish_ticket(guild, channel_id)

# -------------------- UI --------------------
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green)
    async def open_ticket(self, interaction, button):
        await interaction.client.get_cog("TicketSystem").create_ticket(interaction)

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

# -------------------- Setup --------------------
async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
