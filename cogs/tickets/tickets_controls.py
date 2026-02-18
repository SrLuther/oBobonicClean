import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import config
from typing import Optional, Union, Mapping, Any
try:
    from utils.cache import channel_cache, role_cache
except ImportError:
    channel_cache = None
    role_cache = None

from .tickets_utils import salvar_transcript, gerar_ticket_id
from .tickets_views import gerar_view_ticket

class TicketsController(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.inatividade_check.start()

    # ------------------------
    # COMANDO SLASH PARA CRIAR PAINEL (opcional)
    # ------------------------
    @commands.Cog.listener()
    async def on_ready(self):
        # Registra a view persistente
        try:
            self.bot.add_view(gerar_view_ticket(self))
            print("✅ View de tickets registrada como persistente")
        except Exception as e:
            print(f"⚠️ Erro ao registrar view de tickets: {e}")

    async def criar_painel_ticket(self) -> None:
        """Cria painel de tickets com cache otimizado."""
        if channel_cache:
            canal = channel_cache.get(self.bot, config.CANAL_PAINEL_ID)
        else:
            canal = self.bot.get_channel(config.CANAL_PAINEL_ID)
        
        if not isinstance(canal, discord.TextChannel):
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
            "🎫 **Abra seu ticket abaixo!**\n\n"
            "Para abrir seu ticket:\n"
            "• Clique no botão **Abrir Ticket**.\n"
            "• Informe um **resumo objetivo** do problema (assunto + detalhes).\n"
            "• Inclua **dados úteis** (IDs, links, imagens).\n"
            "• Não compartilhe **senhas** ou dados sensíveis.\n\n"
            "Após abrir, um canal exclusivo será criado para o seu atendimento.",
            view=view
        )
        await painel_msg.pin()
        print(f"✅ Painel persistente criado em {canal.name} ({canal.id})")

    @commands.command(name="ticketpanel", aliases=["paineltickets", "painel"])
    @commands.has_permissions(administrator=True)
    async def ticketpanel(self, ctx: commands.Context[Any]) -> None:
        await self.criar_painel_ticket()
        try:
            await ctx.send("✅ Painel de tickets enviado e fixado.", delete_after=10)
        except Exception:
            pass

    # ------------------------
    # CRIAR TICKET
    # ------------------------
    async def criar_ticket(self, interaction: discord.Interaction, descricao: str) -> None:
        guild: Optional[discord.Guild] = interaction.guild
        if guild is None:
            try:
                await interaction.followup.send("❌ Esta ação só pode ser usada dentro de um servidor.", ephemeral=True)
            except Exception:
                pass
            return
        
        try:
            ticket_id = gerar_ticket_id()
            usuario = interaction.user
            membro: Optional[discord.Member]
            if isinstance(usuario, discord.Member):
                membro = usuario
            else:
                membro = guild.get_member(usuario.id)
            
            if membro is None:
                try:
                    await interaction.followup.send("❌ Não foi possível identificar o membro do servidor.", ephemeral=True)
                except Exception:
                    pass
                return
            
            nome_canal = f"TICKET {ticket_id} - {membro.name}"
            categoria = guild.get_channel(config.TICKET_CATEGORY_ID)
            if not isinstance(categoria, discord.CategoryChannel):
                print(f"❌ Categoria de tickets inválida ({config.TICKET_CATEGORY_ID}).")
                try:
                    await interaction.followup.send("❌ Categoria de tickets não encontrada. Avise a equipe.", ephemeral=True)
                except Exception:
                    pass
                return

            overwrites: Mapping[Union[discord.Role, discord.Member, discord.Object], discord.PermissionOverwrite] = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                membro: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }

            # Permissões para moderadores (com cache)
            for role_id in config.MOD_ROLE_IDS:
                if role_cache:
                    role = role_cache.get(guild, role_id)
                else:
                    role = guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            canal_ticket = await guild.create_text_channel(
                nome_canal, category=categoria, overwrites=overwrites
            )

            # Mensagem inicial
            from .tickets_views import gerar_ticket_view
            await canal_ticket.send(
                (
                    f"📝 **Descrição:** {descricao}\n\n"
                    "Painel do ticket:\n"
                    "• **Assumir** (Equipe): Registra o responsável pelo atendimento e inicia a triagem.\n"
                    "• **Fechar**: Solicita um breve feedback e encerra o canal; um transcript é arquivado.\n\n"
                    "Antes de fechar:\n"
                    "• Confirme que o problema foi resolvido.\n"
                    "• Envie um **feedback curto** (obrigatório).\n\n"
                    "Reabertura:\n"
                    "• Caso precise reabrir, avise a equipe após o encerramento."
                ),
                view=gerar_ticket_view(self, canal_ticket, membro, ticket_id)
            )

            await interaction.followup.send(f"✅ Ticket criado: {canal_ticket.mention}", ephemeral=True)
            print(f"✅ Ticket #{ticket_id} criado por {membro.name}")
        
        except Exception as e:
            print(f"❌ Erro ao criar ticket: {type(e).__name__}: {e}")
            try:
                await interaction.followup.send(f"❌ Erro ao criar ticket: {type(e).__name__}", ephemeral=True)
            except Exception:
                pass

    # ------------------------
    # FECHAR TICKET
    # ------------------------
    async def fechar_ticket(self, canal: discord.TextChannel, usuario: discord.Member, ticket_id: int | str) -> None:
        try:
            def check(m: discord.Message) -> bool:
                return bool(m.author == usuario and isinstance(m.channel, discord.TextChannel))

            await canal.send("💬 Por favor, envie um breve feedback sobre este ticket antes de fechá-lo:")

            try:
                msg_feedback = await self.bot.wait_for('message', check=check, timeout=300)
                feedback = msg_feedback.content
            except asyncio.TimeoutError:
                feedback = "Sem feedback fornecido."

            await canal.send("✅ Ticket será encerrado...")
            await salvar_transcript(canal, usuario, ticket_id, feedback)
            await canal.delete()
            print(f"✅ Ticket #{ticket_id} fechado por {usuario.name}")
        except Exception as e:
            print(f"❌ Erro ao fechar ticket #{ticket_id}: {type(e).__name__}: {e}")
            try:
                await canal.send(f"❌ Erro ao fechar ticket: {type(e).__name__}")
            except Exception:
                pass

    # ------------------------
    # ASSUMIR TICKET
    # ------------------------
    async def assumir_ticket(self, canal: discord.TextChannel, usuario: discord.Member, ticket_id: int | str) -> None:
        """Verifica e registra quem assumiu o ticket."""
        try:
            # Verifica se é moderador (otimizado com set)
            mod_ids_set = set(config.MOD_ROLE_IDS)
            usuario_role_ids = {role.id for role in usuario.roles}
            if not mod_ids_set.intersection(usuario_role_ids):
                await canal.send("⚠️ Apenas moderadores podem assumir tickets. Por favor, seja paciente.")
                return

            agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            await canal.send(f"🛡️ Ticket assumido por {usuario.mention} em {agora}")
            print(f"✅ Ticket #{ticket_id} assumido por {usuario.name}")
        except Exception as e:
            print(f"❌ Erro ao assumir ticket #{ticket_id}: {type(e).__name__}: {e}")

    # ------------------------
    # TASK PARA VERIFICAR INATIVIDADE
    # ------------------------
    @tasks.loop(minutes=60)
    async def inatividade_check(self):
        """Verifica tickets inativos e os arquiva."""
        from discord.utils import utcnow
        expiration_seconds = config.EXPIRACAO_TICKET_HORAS * 3600
        
        for guild in self.bot.guilds:
            if channel_cache:
                categoria = channel_cache.get(self.bot, config.TICKET_CATEGORY_ID)
            else:
                categoria = self.bot.get_channel(config.TICKET_CATEGORY_ID)
            
            if not isinstance(categoria, discord.CategoryChannel):
                continue
            
            # Processa apenas canais que começam com "TICKET"
            ticket_channels = [c for c in categoria.text_channels if c.name.startswith("TICKET")]
            
            for canal in ticket_channels:
                delta = utcnow() - canal.created_at
                if delta.total_seconds() >= expiration_seconds:
                    await canal.send(f"⏰ Ticket inativo por mais de {config.EXPIRACAO_TICKET_HORAS} horas, será arquivado.")
                    owner_candidate: Optional[discord.Member] = canal.guild.owner or canal.guild.me
                    if owner_candidate:
                        ticket_id = canal.name.split()[1] if len(canal.name.split()) > 1 else "unknown"
                        await salvar_transcript(canal, owner_candidate, ticket_id, "Ticket inativo automaticamente")
                    await canal.delete()
