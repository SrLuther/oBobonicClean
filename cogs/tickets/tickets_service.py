# ============================================================
# cogs/tickets/tickets_service.py
# Lógica de criação/fechamento/assumir tickets
# ============================================================

import discord
import datetime
import asyncio
import config
from .tickets_utils import gerar_ticket_id, salvar_log_ticket, is_mod, format_timestamp
from .tickets_views import gerar_view_ticket_ativo

EXPIRACAO_TICKET_HORAS = config.EXPIRACAO_TICKET_HORAS

class TicketsService:
    def __init__(self, bot):
        self.bot = bot
        self.tickets = {}  # {ticket_id: {channel, owner, assunto, criado_em, assumido_por}}

    async def criar_ticket(self, interaction, assunto):
        ticket_id = gerar_ticket_id()
        guild = interaction.guild
        categoria = guild.get_channel(config.TICKET_CATEGORY_ID)
        usuario_nome = interaction.user.name
        canal_nome = f"TICKET {ticket_id} - {usuario_nome}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=canal_nome, category=categoria, overwrites=overwrites)

        self.tickets[ticket_id] = {
            "channel": channel.id,
            "owner": interaction.user,
            "assunto": assunto,
            "created": datetime.datetime.now(),
            "assumido_por": None
        }

        await channel.send(f"🎫 Ticket `{ticket_id}` criado por {interaction.user.mention}", view=gerar_view_ticket_ativo())

        # iniciar timer de expiração
        asyncio.create_task(self._verificar_expiracao(ticket_id))

        return channel, ticket_id

    async def fechar_ticket(self, interaction, ticket_id):
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            await interaction.response.send_message("❌ Ticket não encontrado.", ephemeral=True)
            return

        # solicitar feedback
        if interaction.user.id == ticket["owner"].id:
            await interaction.response.send_modal(
                self.FeedbackModal(ticket_id, self)
            )
        else:
            await self._finalizar_ticket(ticket_id, interaction.user)

    async def _finalizar_ticket(self, ticket_id, fechado_por):
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return

        channel = self.bot.get_channel(ticket["channel"])
        owner = ticket["owner"]
        conteudo = (
            f"Ticket #{ticket_id}\n"
            f"Criador: {owner}\n"
            f"Fechado por: {fechado_por}\n"
            f"Data: {format_timestamp()}\n"
            f"Assunto: {ticket['assunto']}\n"
            f"Assumido por: {ticket['assumido_por']}\n"
        )

        arquivo = salvar_log_ticket(ticket_id, conteudo)
        canal_arquivo = self.bot.get_channel(config.CANAL_ARQUIVO_ID)
        if canal_arquivo:
            await canal_arquivo.send(file=discord.File(arquivo))

        await channel.delete()
        del self.tickets[ticket_id]

    async def assumir_ticket(self, interaction, ticket_id):
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            await interaction.response.send_message("❌ Ticket não encontrado.", ephemeral=True)
            return

        if not is_mod(interaction.user):
            await interaction.response.send_message("❌ Apenas moderadores podem assumir tickets. Por favor, aguarde atendimento.", ephemeral=True)
            return

        ticket["assumido_por"] = interaction.user
        channel = self.bot.get_channel(ticket["channel"])
        await channel.send(f"🟢 Ticket assumido por {interaction.user.mention} em {format_timestamp()}")

    async def _verificar_expiracao(self, ticket_id):
        await asyncio.sleep(EXPIRACAO_TICKET_HORAS * 3600)
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return

        channel = self.bot.get_channel(ticket["channel"])
        await channel.send(f"⏳ Ticket inativo por {EXPIRACAO_TICKET_HORAS} horas. Será arquivado automaticamente.")
        await self._finalizar_ticket(ticket_id, fechado_por="Sistema (inatividade)")

    # ===================== MODAL =====================
    class FeedbackModal(discord.ui.Modal):
        def __init__(self, ticket_id, service):
            super().__init__(title="Feedback do Ticket")
            self.ticket_id = ticket_id
            self.service = service
            self.feedback = discord.ui.TextInput(
                label="Feedback (opcional)",
                style=discord.TextStyle.paragraph,
                placeholder="Digite seu feedback...",
                required=False,
                max_length=500
            )
            self.add_item(self.feedback)

        async def on_submit(self, interaction: discord.Interaction):
            await self.service._finalizar_ticket(self.ticket_id, fechado_por=interaction.user)
