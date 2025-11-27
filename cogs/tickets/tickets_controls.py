import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
import asyncio
import os
from io import StringIO
import datetime
import config

from .tickets_utils import salvar_transcript, gerar_ticket_id, ler_ticket_ids

class TicketsController(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.inatividade_check.start()

    # ------------------------
    # COMANDO SLASH PARA CRIAR PAINEL (opcional)
    # ------------------------
    @commands.Cog.listener()
    async def on_ready(self):
        await self.criar_painel_ticket()

    async def criar_painel_ticket(self):
        canal = self.bot.get_channel(config.CANAL_PAINEL_ID)
        if not canal:
            print(f"❌ Canal do painel ({config.CANAL_PAINEL_ID}) não encontrado.")
            return

        mensagens = [msg async for msg in canal.history(limit=50)]
        for msg in mensagens:
            if msg.pinned:
                print("✅ Painel já fixado encontrado, pulando criação.")
                return

        from .tickets_views import gerar_view_ticket
        view = gerar_view_ticket(self)
        painel_msg = await canal.send(
            "🎫 **Abra seu ticket abaixo!**\nPor favor, clique no botão e forneça uma breve descrição do seu problema.",
            view=view
        )
        await painel_msg.pin()
        print(f"✅ Painel persistente criado em {canal.name} ({canal.id})")

    # ------------------------
    # CRIAR TICKET
    # ------------------------
    async def criar_ticket(self, interaction: discord.Interaction, descricao: str):
        guild = interaction.guild
        ticket_id = gerar_ticket_id()
        membro = interaction.user
        nome_canal = f"TICKET {ticket_id} - {membro.name}"
        categoria = guild.get_channel(config.TICKET_CATEGORY_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            membro: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        # Permissões para moderadores
        for role_id in config.MOD_ROLE_IDS:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        canal_ticket = await guild.create_text_channel(
            nome_canal, category=categoria, overwrites=overwrites
        )

        # Mensagem inicial
        from .tickets_views import gerar_ticket_view
        await canal_ticket.send(
            f"📝 **Descrição:** {descricao}\n\nUse os botões abaixo para **assumir** ou **fechar** o ticket.",
            view=gerar_ticket_view(self, canal_ticket, membro, ticket_id)
        )

        await interaction.response.send_message(f"✅ Ticket criado: {canal_ticket.mention}", ephemeral=True)

    # ------------------------
    # FECHAR TICKET
    # ------------------------
    async def fechar_ticket(self, canal, usuario, ticket_id):
        def check(m):
            return m.author == usuario and isinstance(m.channel, discord.TextChannel)

        await canal.send("💬 Por favor, envie um breve feedback sobre este ticket antes de fechá-lo:")

        try:
            msg_feedback = await self.bot.wait_for('message', check=check, timeout=300)
            feedback = msg_feedback.content
        except asyncio.TimeoutError:
            feedback = "Sem feedback fornecido."

        await canal.send("✅ Ticket será encerrado...")
        await salvar_transcript(canal, usuario, ticket_id, feedback)
        await canal.delete()

    # ------------------------
    # ASSUMIR TICKET
    # ------------------------
    async def assumir_ticket(self, canal, usuario, ticket_id):
        # Verifica se é moderador
        mod_ids = [role.id for role in usuario.roles]
        if not any(role in config.MOD_ROLE_IDS for role in mod_ids):
            await canal.send(f"⚠️ Apenas moderadores podem assumir tickets. Por favor, seja paciente.")
            return

        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        await canal.send(f"🛡️ Ticket assumido por {usuario.mention} em {agora}")

    # ------------------------
    # TASK PARA VERIFICAR INATIVIDADE
    # ------------------------
    @tasks.loop(minutes=60)
    async def inatividade_check(self):
        for guild in self.bot.guilds:
            categoria = guild.get_channel(config.TICKET_CATEGORY_ID)
            if not categoria:
                continue
            for canal in categoria.text_channels:
                if canal.name.startswith("TICKET"):
                    delta = datetime.datetime.utcnow() - canal.created_at.replace(tzinfo=None)
                    if delta.total_seconds() >= config.EXPIRACAO_TICKET_HORAS * 3600:
                        await canal.send(f"⏰ Ticket inativo por mais de {config.EXPIRACAO_TICKET_HORAS} horas, será arquivado.")
                        await salvar_transcript(canal, canal.guild.owner, canal.name.split()[1], "Ticket inativo automaticamente")
                        await canal.delete()
