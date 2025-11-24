# cogs/tickets.py
import discord
from discord.ext import commands, tasks
import asyncio
import time
import io
from datetime import datetime
import pytz
try:
    from config import TICKET_CATEGORY_ID, TICKET_ARCHIVE_CHANNEL_ID, TICKET_NOTIFY_CHANNEL_ID, STAFF_ROLE_ID, GUILD_ID
except ImportError:
    TICKET_CATEGORY_ID = 0
    TICKET_ARCHIVE_CHANNEL_ID = 0
    TICKET_NOTIFY_CHANNEL_ID = 0
    STAFF_ROLE_ID = []
    GUILD_ID = 0

ticket_activity = {}
TIMEZONE = pytz.timezone("America/Sao_Paulo")

class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        if hasattr(self, "check_inactivity") and self.check_inactivity.is_running():
            self.check_inactivity.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        if not hasattr(self, "check_inactivity") or not self.check_inactivity.is_running():
            print("[tickets] Tarefa de inatividade iniciada.")
            self.check_inactivity.start()

    @tasks.loop(hours=1)
    async def check_inactivity(self):
        try:
            await self.bot.wait_until_ready()
            INACTIVITY_LIMIT = 48 * 3600
            current_time = time.time()
            guild = self.bot.get_guild(GUILD_ID)
            if not guild:
                return
            category = guild.get_channel(TICKET_CATEGORY_ID)
            if not category:
                return
            for channel in category.channels:
                if channel.id in ticket_activity:
                    last_activity = ticket_activity[channel.id]
                    if (current_time - last_activity) > INACTIVITY_LIMIT:
                        await channel.send(
                            "⚠️ **Aviso de Inatividade:** Este ticket está inativo há mais de 48 horas. "
                            "Ele será arquivado em breve se não houver resposta."
                        )
                        del ticket_activity[channel.id]
        except Exception as e:
            print(f"[tickets] ❌ ERRO CRÍTICO na tarefa de inatividade: {e}. O bot continua rodando.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.category_id == TICKET_CATEGORY_ID:
            ticket_activity[message.channel.id] = time.time()

    async def create_transcript(self, channel: discord.TextChannel):
        transcript = f"Transcript do Ticket: {channel.name}\nCriado em: {channel.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
        for msg in messages:
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            transcript += f"[{timestamp}] {msg.author.display_name}: {msg.content}\n"
            for attachment in msg.attachments:
                transcript += f"  (Anexo: {attachment.url})\n"
        file = discord.File(io.StringIO(transcript), filename=f"transcript-{channel.name}.txt")
        return file

    async def send_log(self, action: str, channel: discord.TextChannel, user: discord.Member, feedback: str = None):
        log_channel = self.bot.get_channel(TICKET_ARCHIVE_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title="🎫 Log de Ticket", color=discord.Color.dark_green())
            embed.add_field(name="Ação", value=action, inline=True)
            embed.add_field(name="Ticket", value=f"#{channel.name}", inline=True)
            embed.add_field(name="Responsável", value=user.mention, inline=True)
            if feedback:
                embed.add_field(name="Feedback", value=feedback, inline=False)
            embed.set_footer(text=f"Data/Hora: {datetime.now(TIMEZONE).strftime('%d/%m/%Y %H:%M:%S')}")
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                print("❌ Falha ao enviar log. Verifique permissões do canal de arquivos.")

    @commands.command(name="ticketpanel")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx):
        embed = discord.Embed(
            title="📌 Suporte e Ajuda",
            description=(
                "Clique no botão abaixo para abrir um novo ticket de suporte.\n\n"
                "**Como funciona:**\n"
                "1️⃣ Um canal privado será criado apenas para você e a equipe de suporte.\n"
                "2️⃣ No canal, você pode escrever sua dúvida ou problema.\n"
                "3️⃣ Clique em **Fechar Ticket** quando tiver concluído; você será solicitado a fornecer um feedback.\n"
                "4️⃣ O histórico será salvo e enviado para arquivamento.\n\n"
                "Para ações exclusivas da equipe de moderação, utilize o botão **STAFF** no canal do ticket."
            ),
            color=discord.Color.blue()
        )
        view = TicketView(self.bot, TICKET_CATEGORY_ID, STAFF_ROLE_ID[1])
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()

class TicketView(discord.ui.View):
    def __init__(self, bot, category_id, staff_role_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.category_id = category_id
        self.staff_role_id = staff_role_id

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket_button")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        category = guild.get_channel(self.category_id)
        member = interaction.user

        # Verifica se já existe ticket
        for channel in category.channels:
            if f"-{member.id}" in channel.name:
                return await interaction.followup.send(
                    "Você já possui um ticket aberto. Por favor, feche o ticket anterior antes de abrir um novo.",
                    ephemeral=True
                )

        # Permissões
        staff_role = guild.get_role(self.staff_role_id)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }

        # Criação do canal
        ticket_channel = await category.create_text_channel(
            name=f"ticket-{member.display_name.lower().replace(' ', '-')}-{member.id}",
            topic=f"Ticket de {member.display_name} | ID: {member.id}",
            overwrites=overwrites
        )

        # Embed inicial no canal
        embed = discord.Embed(
            title="👋 Novo Ticket Criado",
            description=(
                f"Olá {member.mention}! Um moderador irá ajudá-lo em breve.\n\n"
                "**Botões Disponíveis:**\n"
                "🔹 **Fechar Ticket:** Encerrar o ticket e enviar feedback.\n"
                "🔹 **STAFF:** (Apenas para moderadores) abrir painel de ações especiais."
            ),
            color=discord.Color.green()
        )
        view = TicketChannelView(self.bot, ticket_channel, member, staff_role)
        await ticket_channel.send(embed=embed, view=view)

        await interaction.followup.send(f"Ticket aberto em {ticket_channel.mention}", ephemeral=True)

class TicketChannelView(discord.ui.View):
    def __init__(self, bot, channel, member, staff_role):
        super().__init__(timeout=None)
        self.bot = bot
        self.channel = channel
        self.member = member
        self.staff_role = staff_role

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FeedbackModal(self.channel, self.member, interaction.user, self.bot))

    @discord.ui.button(label="STAFF", style=discord.ButtonStyle.gray, custom_id="staff_ticket_button")
    async def staff_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.staff_role.id not in [role.id for role in interaction.user.roles]:
            return await interaction.response.send_message("❌ Apenas moderadores podem acessar esse painel.", ephemeral=True)
        view = StaffPanelView(self.channel, interaction.user, self.bot)
        await interaction.response.send_message("Painel de ações STAFF:", view=view, ephemeral=True)

class FeedbackModal(discord.ui.Modal, title="Feedback do Ticket"):
    feedback = discord.ui.TextInput(label="Digite seu feedback", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, channel, member, closer, bot):
        super().__init__()
        self.channel = channel
        self.member = member
        self.closer = closer
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        file = await TicketsCog(self.bot).create_transcript(self.channel)
        archive_channel = self.bot.get_channel(TICKET_ARCHIVE_CHANNEL_ID)
        feedback_text = self.feedback.value
        await archive_channel.send(
            f"📁 Ticket fechado por {self.closer.mention}\nFeedback: {feedback_text}", file=file
        )
        await TicketsCog(self.bot).send_log(self=self.bot.get_cog("TicketsCog"), action="Ticket Fechado", channel=self.channel, user=self.closer, feedback=feedback_text)
        await self.channel.delete()
        await interaction.response.send_message("✅ Ticket fechado e transcript enviado.", ephemeral=True)

class StaffPanelView(discord.ui.View):
    def __init__(self, channel, staff_member, bot):
        super().__init__(timeout=None)
        self.channel = channel
        self.staff_member = staff_member
        self.bot = bot

    @discord.ui.button(label="SOLUCIONADO ✅", style=discord.ButtonStyle.green, custom_id="solucionado_button")
    async def solucionado(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StaffFeedbackModal(self.channel, self.staff_member, self.bot, "SOLUCIONADO"))

    @discord.ui.button(label="+EQUIPE ⚠️", style=discord.ButtonStyle.blurple, custom_id="mais_equipe_button")
    async def mais_equipe(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "⚠️ Suporte adicional será acionado. Um moderador irá contatar para auxiliar.", ephemeral=True
        )

    @discord.ui.button(label="ABANDONO 🚫", style=discord.ButtonStyle.red, custom_id="abandono_button")
    async def abandono(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StaffFeedbackModal(self.channel, self.staff_member, self.bot, "ABANDONO"))

class StaffFeedbackModal(discord.ui.Modal):
    feedback = discord.ui.TextInput(label="Digite seu feedback", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, channel, staff_member, bot, status):
        super().__init__(title=f"Feedback - {status}")
        self.channel = channel
        self.staff_member = staff_member
        self.bot = bot
        self.status = status

    async def on_submit(self, interaction: discord.Interaction):
        file = await TicketsCog(self.bot).create_transcript(self.channel)
        archive_channel = self.bot.get_channel(TICKET_ARCHIVE_CHANNEL_ID)
        feedback_text = self.feedback.value
        await archive_channel.send(
            f"📁 Ticket {self.status} por {self.staff_member.mention}\nFeedback: {feedback_text}", file=file
        )
        await TicketsCog(self.bot).send_log(self=self.bot.get_cog("TicketsCog"), action=f"Ticket {self.status}", channel=self.channel, user=self.staff_member, feedback=feedback_text)
        await self.channel.delete()
        await interaction.response.send_message(f"✅ Ticket {self.status} e transcript enviado.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketsCog(bot))

# ============================================================
# Atualizado em: 2025-11-23 23:51:12 (Horário de Brasília)
# ============================================================
