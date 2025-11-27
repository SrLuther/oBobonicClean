import discord
from .tickets_views import gerar_embed_ticket, gerar_view_ticket
from .tickets_utils import gerar_id_ticket_formato
from config import TICKET_CATEGORY_ID, TICKET_ARCHIVE_CHANNEL_ID

class TicketsService:
    def __init__(self, bot):
        self.bot = bot

    async def criar_ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        usuario = interaction.user

        # Gerar ID do ticket
        ticket_id = await gerar_id_ticket_formato()

        # Criar canal do ticket
        category = discord.utils.get(guild.categories, id=TICKET_CATEGORY_ID)
        canal = await guild.create_text_channel(
            name=f"ticket-{ticket_id}",
            category=category,
            topic=f"Ticket de {usuario} ({usuario.id})",
            reason="Novo ticket criado via /ticket"
        )

        # Enviar mensagem inicial com embed + botões
        embed = gerar_embed_ticket(usuario, ticket_id)
        view = gerar_view_ticket()
        await canal.send(embed=embed, view=view)

        return canal

    async def encerrar_ticket(self, interaction: discord.Interaction):
        canal = interaction.channel
        usuario = interaction.user
        # Mensagem de confirmação
        await canal.send(f"{usuario.mention} solicitou encerrar este ticket. Clique no botão para confirmar.",
                         view=gerar_view_ticket())

    async def confirmar_fechamento(self, interaction: discord.Interaction):
        canal = interaction.channel
        # Mover para canal de arquivamento
        archive_channel = discord.utils.get(interaction.guild.channels, id=TICKET_ARCHIVE_CHANNEL_ID)
        await canal.delete(reason="Ticket encerrado e arquivado")
        # Pode adicionar aqui log no canal de notificação
