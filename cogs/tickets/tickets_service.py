import discord
from discord.ext import commands
import datetime
import config

from .tickets_views import gerar_embed_ticket, gerar_view_ticket
from .tickets_utils import gerar_id_ticket_formato

class TicketsService:
    def __init__(self, bot):
        self.bot = bot

    # ============================================================
    # CRIAÇÃO DO TICKET
    # ============================================================
    async def criar_ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        usuario = interaction.user

        categoria = guild.get_channel(config.TICKET_CATEGORY_ID)

        # Gera ID: exemplo T-00001
        ticket_id = await gerar_id_ticket_formato()

        nome_canal = f"ticket-{ticket_id}-{usuario.name}".replace(" ", "-").lower()

        canal = await guild.create_text_channel(
            name=nome_canal,
            category=categoria,
            topic=f"Ticket de {usuario} | ID: {ticket_id}"
        )

        # Permissões
        await canal.set_permissions(guild.default_role, read_messages=False)
        await canal.set_permissions(usuario, read_messages=True, send_messages=True)

        # Staff
        staff_role = guild.get_role(config.STAFF_ROLE_ID)
        if staff_role:
            await canal.set_permissions(staff_role, read_messages=True, send_messages=True)

        # Envia mensagem inicial
        embed = gerar_embed_ticket(usuario, ticket_id)
        view = gerar_view_ticket()

        await canal.send(embed=embed, view=view)

        # Notificação opcional
        notify = guild.get_channel(config.TICKET_NOTIFY_CHANNEL_ID)
        if notify:
            await notify.send(f"📩 Novo Ticket criado: {canal.mention}")

        return canal

    # ============================================================
    # ENCERRAR TICKET
    # ============================================================
    async def encerrar_ticket(self, interaction: discord.Interaction):
        view = discord.ui.View(timeout=None)
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label="Confirmar encerramento",
                custom_id="confirmar_encerramento"
            )
        )

        await interaction.response.send_message(
            "Tem certeza que deseja encerrar o ticket?",
            view=view,
            ephemeral=True
        )

    # ============================================================
    # CONFIRMAR FECHAMENTO
    # ============================================================
    async def confirmar_fechamento(self, interaction: discord.Interaction):
        canal = interaction.channel

        embed = discord.Embed(
            title="Ticket Encerrado",
            description=f"O ticket foi encerrado por **{interaction.user}**.",
            color=0xff5555,
            timestamp=datetime.datetime.utcnow()
        )

        await canal.send(embed=embed)

        await canal.edit(name=f"{canal.name}-fechado")

        await interaction.response.send_message(
            "Ticket encerrado com sucesso!",
            ephemeral=True
        )
