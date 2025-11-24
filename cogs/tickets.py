# cogs/tickets.py
import discord
from discord.ext import commands, tasks
import asyncio
import io
import time
from datetime import datetime
import pytz
import config

# Mantém registro da última atividade de cada ticket
ticket_activity = {}

# Pega o timezone de São Paulo
tz = pytz.timezone("America/Sao_Paulo")

def now_str():
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(self, "check_inatividade") or not self.check_inatividade.is_running():
            self.check_inatividade.start()

    def cog_unload(self):
        if hasattr(self, "check_inatividade") and self.check_inatividade.is_running():
            self.check_inatividade.cancel()

    # ------------------------
    # Verifica inatividade
    # ------------------------
    @tasks.loop(hours=1)
    async def check_inatividade(self):
        try:
            await self.bot.wait_until_ready()
            INACTIVITY_LIMIT = config.EXPIRACAO_TICKET_HORAS * 3600
            current_time = time.time()
            guild = self.bot.get_guild(config.GUILD_ID)
            if not guild:
                return
            category = guild.get_channel(config.TICKET_CATEGORY_ID)
            if not category:
                return
            for channel in category.channels:
                if channel.id in ticket_activity:
                    last_activity = ticket_activity[channel.id]
                    if (current_time - last_activity) > INACTIVITY_LIMIT:
                        await channel.send(
                            f"⚠️ **Aviso de Inatividade:** Este ticket está inativo há mais de {config.EXPIRACAO_TICKET_HORAS} horas.\n"
                            "Ele será arquivado em breve se não houver resposta."
                        )
                        del ticket_activity[channel.id]
        except Exception as e:
            print(f"[tickets] ❌ ERRO CRÍTICO na tarefa de inatividade: {e}. O bot continua rodando.")

    # ------------------------
    # Atualiza atividade
    # ------------------------
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.category_id == config.TICKET_CATEGORY_ID:
            ticket_activity[message.channel.id] = time.time()

    # ------------------------
    # Criação de transcript
    # ------------------------
    async def create_transcript(self, channel: discord.TextChannel, feedback: str = None, closed_by: str = None):
        header = f"Transcript do Ticket: {channel.name}\nCriado em: {channel.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"Fechado por: {closed_by or 'N/A'}\nFeedback: {feedback or 'N/A'}\n\n"
        transcript = header
        messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
        for msg in messages:
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            transcript += f"[{timestamp}] {msg.author.display_name}: {msg.content}\n"
            for attachment in msg.attachments:
                transcript += f"  (Anexo: {attachment.url})\n"
        file = discord.File(io.StringIO(transcript), filename=f"transcript-{channel.name}.txt")
        return file

    # ------------------------
    # Logs
    # ------------------------
    async def send_log(self, action: str, channel: discord.TextChannel, user: discord.Member):
        log_channel = self.bot.get_channel(config.CANAL_LOGS_ID)
        if log_channel:
            embed = discord.Embed(title="🎫 Log de Ticket", color=discord.Color.dark_green())
            embed.add_field(name="Ação", value=action, inline=True)
            embed.add_field(name="Ticket", value=f"#{channel.name}", inline=True)
            embed.add_field(name="Responsável", value=user.mention, inline=True)
            embed.set_footer(text=f"{now_str()} | Ticket ID: {channel.id}")
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                print("❌ Falha ao enviar log. Verifique permissões do canal de logs.")

    # ------------------------
    # Comando painel principal
    # ------------------------
    @commands.command(name="ticketpanel")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx):
        embed = discord.Embed(
            title="🎫 Sistema de Suporte e Tickets",
            description=(
                "Bem-vindo ao sistema de tickets!\n\n"
                "✅ Para abrir um ticket, clique no botão **Abrir Ticket**.\n"
                "📌 No ticket, você poderá conversar com nossa equipe de suporte.\n"
                "📝 Quando finalizar, clique em **Fechar** para enviar seu feedback e gerar a transcrição.\n"
                "⚠️ O painel STAFF está disponível **apenas para moderadores** e permite ações adicionais.\n\n"
                f"⏰ Data/Hora: {now_str()}"
            ),
            color=discord.Color.blue()
        )
        view = TicketView(self.bot, config.TICKET_CATEGORY_ID, config.STAFF_ROLE_ID)
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()
        await self.send_log("Painel de Tickets enviado", ctx.channel, ctx.author)

# ------------------------
# Botão Fechar / Abrir Ticket
# ------------------------
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
        for channel in category.channels:
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
            staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }

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

# ------------------------
# Botões dentro do ticket
# ------------------------
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
        if self.member != interaction.user and self.staff_role not in interaction.user.roles:
            return await interaction.response.send_message(
                "Você não tem permissão para fechar este ticket.", ephemeral=True
            )

        await interaction.response.send_modal(FeedbackModal(self.ticket_channel, interaction.user, self.bot))

    # --- Botão STAFF (somente moderador) ---
    @discord.ui.button(label="STAFF", style=discord.ButtonStyle.gray, custom_id="staff_ticket_button")
    async def staff_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.staff_role not in interaction.user.roles:
            return await interaction.response.send_message(
                "Somente moderadores podem acessar este painel.", ephemeral=True
            )

        # Painel secundário para STAFF
        view = StaffPanelView(self.bot, self.ticket_channel, self.member)
        await interaction.response.send_message("Painel STAFF aberto:", view=view, ephemeral=True)

# ------------------------
# Modal para Feedback
# ------------------------
class FeedbackModal(discord.ui.Modal):
    def __init__(self, channel, user, bot):
        super().__init__(title="Feedback do Ticket")
        self.channel = channel
        self.user = user
        self.bot = bot
        self.feedback_input = discord.ui.TextInput(
            label="Escreva seu feedback:",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1024
        )
        self.add_item(self.feedback_input)

    async def on_submit(self, interaction: discord.Interaction):
        feedback_text = self.feedback_input.value
        file = await TicketsCog(self.bot).create_transcript(
            self.channel,
            feedback=feedback_text,
            closed_by=self.user.display_name
        )
        await self.channel.send(f"✅ Ticket fechado por {self.user.mention} com feedback enviado.")
        archive_channel = self.channel.guild.get_channel(config.TICKET_ARCHIVE_CHANNEL_ID)
        if archive_channel:
            await archive_channel.send(f"📜 Transcript do ticket {self.channel.name}", file=file)
        await TicketsCog(self.bot).send_log(self.bot.get_cog("TicketsCog"), "Ticket Fechado", self.channel, self.user)

# ------------------------
# Painel STAFF
# ------------------------
class StaffPanelView(discord.ui.View):
    def __init__(self, bot, ticket_channel, member):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_channel = ticket_channel
        self.member = member

    @discord.ui.button(label="SOLUCIONADO ✅", style=discord.ButtonStyle.green, custom_id="staff_solved")
    async def solved(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FeedbackModal(self.ticket_channel, interaction.user, self.bot))

    @discord.ui.button(label="+ EQUIPE ⚠️", style=discord.ButtonStyle.blurple, custom_id="staff_team")
    async def extra_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"O ticket {self.ticket_channel.name} será revisado por outro moderador.",
            ephemeral=True
        )

    @discord.ui.button(label="ABANDONO 🚫", style=discord.ButtonStyle.red, custom_id="staff_abandon")
    async def abandon(self, interaction: discord.Interaction, button: discord.ui.Button):
        file = await TicketsCog(self.bot).create_transcript(
            self.ticket_channel,
            feedback="Ticket encerrado por abandono.",
            closed_by=interaction.user.display_name
        )
        archive_channel = self.ticket_channel.guild.get_channel(config.TICKET_ARCHIVE_CHANNEL_ID)
        if archive_channel:
            await archive_channel.send(f"📜 Transcript do ticket {self.ticket_channel.name}", file=file)
        await TicketsCog(self.bot).send_log(self.bot.get_cog("TicketsCog"), "Ticket Encerrado (Abandono)", self.ticket_channel, interaction.user)
        await interaction.response.send_message("Ticket encerrado por abandono.", ephemeral=True)

# ------------------------
# Setup Cog
# ------------------------
async def setup(bot):
    await bot.add_cog(TicketsCog(bot))

# ============================================================
# Atualizado em: 2025-11-24 01:35:00 (Horário de Brasília)
# ============================================================
