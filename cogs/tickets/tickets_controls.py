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
        self.inatividade_check.start()  # type: ignore

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
        
        # Aguardar um pouco para o bot ficar totalmente pronto
        try:
            await asyncio.sleep(2)
        except Exception:
            pass
        
        # Recriar painel de tickets após restart para garantir que as Views funcionem
        try:
            await self.recriar_painel_tickets()
        except Exception as e:
            print(f"⚠️ Erro ao recriar painel de tickets: {e}")
            import traceback
            traceback.print_exc()

    # ------------------------
    # RECRIAR PAINEL DE TICKETS
    # ------------------------
    async def recriar_painel_tickets(self) -> None:
        """Deleta painel anterior e cria novo para garantir que Views funcionem após restart"""
        try:
            guild = self.bot.get_guild(config.GUILD_ID)
            if not guild:
                print("⚠️ [TICKETS] Guild não encontrada para recriar painel")
                return
            
            # Obter o canal do painel
            canal = guild.get_channel(config.CANAL_PAINEL_ID)
            if not isinstance(canal, discord.TextChannel):
                print(f"⚠️ [TICKETS] Canal {config.CANAL_PAINEL_ID} não é um canal de texto")
                return
            
            # Verificar e deletar mensagem anterior fixada
            try:
                mensagens_fixadas = [msg async for msg in canal.history(limit=50) if msg.pinned and msg.author.id == self.bot.user.id]
                if mensagens_fixadas:
                    for msg_antiga in mensagens_fixadas:
                        try:
                            await msg_antiga.unpin()
                            await msg_antiga.delete()
                            print(f"✅ [TICKETS] Painel anterior deletado e despinado")
                        except Exception as e:
                            print(f"⚠️ [TICKETS] Erro ao deletar painel anterior: {e}")
                            pass
            except Exception as e:
                print(f"⚠️ [TICKETS] Erro ao verificar mensagens fixadas: {e}")
                return
            
            # Aguardar um pouco para evitar rate limit
            await asyncio.sleep(1)
            
            # Criar NOVO painel com View recém-registrada
            painel_msg = await canal.send(
                "🎟️ **SISTEMA DE TICKETS DE SUPORTE**\n\n"
                "═══════════════════════════════════════\n\n"
                "**Bem-vindo ao sistema de suporte!**\n\n"
                "Clique no botão abaixo para abrir um ticket "
                "e solicitar ajuda com dúvidas, problemas ou outros assuntos.\n\n"
                "**✨ Categorias de Suporte:**\n"
                "📋 Geral • 💰 Financeiro • 📦 Problemas com Kit\n"
                "🐛 Bug • ⚠️ Denúncia • 💡 Sugestão • 😠 Reclamação • ❓ Outro\n\n"
                "**✨ Como Funciona:**\n"
                "1️⃣ Clique em \"Abrir Ticket\"\n"
                "2️⃣ Escolha a categoria de suporte\n"
                "3️⃣ Forneça um resumo do seu problema\n"
                "4️⃣ Um canal privado será criado para você\n"
                "5️⃣ Um membro da equipe irá ajudá-lo!\n\n"
                "**⚠️ MATERIAL NECESSÁRIO:**\n"
                "• **Tenha tudo em mão antes de abrir o ticket!**\n"
                "• Provas, comprovantes ou evidências relevantes\n"
                "• Fotos ou prints mostrando o problema\n"
                "• Recibos ou confirmações de pagamento (se aplicável)\n"
                "• Informações completas e precisas sobre o caso\n\n"
                "**⚙️ Gerenciamento do Ticket:**\n"
                "• Um responsável irá **Assumir** seu atendimento\n"
                "• Responda rapidamente às questões da equipe\n"
                "• Envie anexos e evidências conforme solicitado\n"
                "• Quando resolvido, o ticket será **Fechado**\n"
                "• Forneça feedback sobre o atendimento\n\n"
                "**💡 Dicas Importantes:**\n"
                "• Seja específico e detalhado na descrição\n"
                "• Não abra múltiplos tickets para o mesmo assunto\n"
                "• A equipe trabalha o mais rápido possível\n"
                "• Tickets inativos são automaticamente encerrados\n\n"
                "═══════════════════════════════════════",
                view=gerar_view_ticket(self)
            )
            
            # Fixar a mensagem
            await painel_msg.pin()
            print(f"✅ [TICKETS] Painel recriado e fixado no canal {config.CANAL_PAINEL_ID}")
            
        except Exception as e:
            print(f"❌ [TICKETS] Erro ao recriar painel: {e}")

    # ------------------------
    # COMANDO PARA ENVIAR PAINEL DE TICKETS
    # ------------------------
    @commands.command(name="ticketstart", description="Cria e envia o painel de tickets")
    async def ticketstart(self, ctx: commands.Context) -> None:
        """Envia o painel de tickets (botão para abrir ticket) no canal"""
        
        try:
            guild = ctx.guild
            if not guild:
                await ctx.send("❌ Erro: Não foi possível identificar o servidor.", delete_after=5)
                return
            
            # Verificar se já existe mensagem com painel de tickets
            try:
                mensagens_fixadas = [msg async for msg in ctx.channel.history() if msg.pinned]
                if mensagens_fixadas:
                    for msg in mensagens_fixadas:
                        # Verificar se tem botão de "Abrir Ticket"
                        if msg.components:
                            for component in msg.components:
                                if hasattr(component, 'children'):
                                    for child in component.children:
                                        if hasattr(child, 'custom_id') and child.custom_id == "abrir_ticket":
                                            await ctx.send(
                                                f"✅ **Painel já existe!**\n\n"
                                                f"O painel de tickets está disponível em {ctx.channel.mention}\n"
                                                f"Mensagem fixada encontrada.",
                                                delete_after=10
                                            )
                                            print(f"✅ [TICKETS] Painel verificado - já existe no canal {ctx.channel.id}")
                                            return
            except Exception as e:
                print(f"⚠️ [TICKETS] Erro ao verificar painel existente: {e}")
            
            # Criar o painel de tickets
            painel_msg = await ctx.send(
                "🎟️ **SISTEMA DE TICKETS DE SUPORTE**\n\n"
                "═══════════════════════════════════════\n\n"
                "**Bem-vindo ao sistema de suporte!**\n\n"
                "Clique no botão abaixo para abrir um ticket "
                "e solicitar ajuda com dúvidas, problemas ou outros assuntos.\n\n"
                "**✨ Categorias de Suporte:**\n"
                "📋 Geral • 💰 Financeiro • 📦 Problemas com Kit\n"
                "🐛 Bug • ⚠️ Denúncia • 💡 Sugestão • 😠 Reclamação • ❓ Outro\n\n"
                "**✨ Como Funciona:**\n"
                "1️⃣ Clique em \"Abrir Ticket\"\n"
                "2️⃣ Escolha a categoria de suporte\n"
                "3️⃣ Forneça um resumo do seu problema\n"
                "4️⃣ Um canal privado será criado para você\n"
                "5️⃣ Um membro da equipe irá ajudá-lo!\n\n"
                "**⚠️ MATERIAL NECESSÁRIO:**\n"
                "• **Tenha tudo em mão antes de abrir o ticket!**\n"
                "• Provas, comprovantes ou evidências relevantes\n"
                "• Fotos ou prints mostrando o problema\n"
                "• Recibos ou confirmações de pagamento (se aplicável)\n"
                "• Informações completas e precisas sobre o caso\n\n"
                "**⚙️ Gerenciamento do Ticket:**\n"
                "• Um responsável irá **Assumir** seu atendimento\n"
                "• Responda rapidamente às questões da equipe\n"
                "• Envie anexos e evidências conforme solicitado\n"
                "• Quando resolvido, o ticket será **Fechado**\n"
                "• Forneça feedback sobre o atendimento\n\n"
                "**💡 Dicas Importantes:**\n"
                "• Seja específico e detalhado na descrição\n"
                "• Não abra múltiplos tickets para o mesmo assunto\n"
                "• A equipe trabalha o mais rápido possível\n"
                "• Tickets inativos são automaticamente encerrados\n\n"
                "═══════════════════════════════════════",
                view=gerar_view_ticket(self)
            )
            
            # Fixar a mensagem
            await painel_msg.pin()
            
            await ctx.send(
                f"✅ **Painel de tickets criado e fixado com sucesso!**\n\n"
                f"O painel está disponível em {ctx.channel.mention}",
                delete_after=10
            )
            
            print(f"✅ [TICKETS] Painel criado e fixado no canal {ctx.channel.id}")
            
        except Exception as e:
            print(f"❌ [TICKETS] Erro ao criar/verificar painel: {e}")
            await ctx.send(
                f"❌ Erro ao criar painel: {str(e)}",
                delete_after=5
            )

    # ------------------------
    # CRIAR TICKET
    # ------------------------
    async def criar_ticket(self, interaction: discord.Interaction, descricao: str) -> None:
        print(f"🔍 [TICKETS] Iniciando criação de ticket...")
        guild: Optional[discord.Guild] = interaction.guild
        if guild is None:
            print(f"❌ [TICKETS] Guild é None")
            try:
                await interaction.followup.send("❌ Esta ação só pode ser usada dentro de um servidor.", ephemeral=True)
            except Exception:
                pass
            return
        
        try:
            print(f"🔍 [TICKETS] Guild encontrada: {guild.name} ({guild.id})")
            ticket_id = gerar_ticket_id()
            print(f"🔍 [TICKETS] Ticket ID gerado: {ticket_id}")
            
            usuario = interaction.user
            membro: Optional[discord.Member]
            if isinstance(usuario, discord.Member):
                membro = usuario
            else:
                membro = guild.get_member(usuario.id)
            
            print(f"🔍 [TICKETS] Membro: {membro}")
            if membro is None:
                print(f"❌ [TICKETS] Membro é None")
                try:
                    await interaction.followup.send("❌ Não foi possível identificar o membro do servidor.", ephemeral=True)
                except Exception:
                    pass
                return
            
            nome_canal = f"TICKET {ticket_id} - {membro.name}"
            print(f"🔍 [TICKETS] Nome do canal: {nome_canal}")
            
            categoria = guild.get_channel(config.TICKET_CATEGORY_ID)
            print(f"🔍 [TICKETS] Categoria encontrada: {categoria}")
            
            if not isinstance(categoria, discord.CategoryChannel):
                print(f"❌ [TICKETS] Categoria inválida ou não encontrada ({config.TICKET_CATEGORY_ID}).")
                try:
                    await interaction.followup.send(f"❌ Categoria de tickets não encontrada (ID: {config.TICKET_CATEGORY_ID}).", ephemeral=True)
                except Exception as e:
                    print(f"❌ Erro ao enviar mensagem de followup: {e}")
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

            print(f"🔍 [TICKETS] Criando canal de texto...")
            canal_ticket = await guild.create_text_channel(
                nome_canal, category=categoria, overwrites=overwrites
            )
            print(f"✅ [TICKETS] Canal criado: {canal_ticket.mention}")

            # Mensagem inicial
            from .tickets_views import gerar_ticket_view
            await canal_ticket.send(
                (
                    f"🎟️ **Olá {membro.mention}!**\n\n"
                    f"**Ticket ID:** `#{ticket_id}`\n"
                    f"**Status:** 🟡 Em Aberto\n"
                    f"**Criado em:** <t:{int(__import__('time').time())}:f>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"**📝 Sua Solicitação:**\n```\n{descricao}\n```\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"**⚠️ IMPORTANTE - TENHA TUDO EM MÃO!**\n"
                    f"Para que seu ticket seja resolvido rapidamente, certifique-se de:\n\n"
                    f"📸 **Provas e Comprovantes:**\n"
                    f"• Se for sobre uma compra: envie recibos ou confirmação de pagamento\n"
                    f"• Se for um bug: envie prints ou vídeos mostrando o problema\n"
                    f"• Se for uma reclamação: tenha evidências disponíveis\n"
                    f"• Se for denúncia: envie prints ou comprovações\n\n"
                    f"📋 **Informações Necessárias:**\n"
                    f"• Seja específico e detalhado na descrição\n"
                    f"• Inclua datas, horários e nomes envolvidos (se aplicável)\n"
                    f"• Responda a todas as perguntas da equipe\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"**⏳ O que Acontece Agora?**\n"
                    f"1. A equipe será notificada sobre seu ticket\n"
                    f"2. Um responsável irá **Assumir** o atendimento\n"
                    f"3. Você receberá respostas neste canal\n"
                    f"4. Quando resolvido, o ticket será **Fechado**\n\n"
                    f"**🛠️ Ações Disponíveis:**\n\n"
                    f"Pressione os botões abaixo:\n"
                    f"• **Assumir** (Equipe): Registra o responsável pelo atendimento\n"
                    f"• **Fechar**: Finaliza o ticket (com feedback)\n\n"
                    f"**💬 Como Proceder:**\n"
                    f"• Envie mensagens normalmente neste canal\n"
                    f"• Anexe fotos, prints ou comprovantes quando necessário\n"
                    f"• Responda rapidamente às questões da equipe\n"
                    f"• Seja educado e paciente - estamos aqui para ajudar!\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                view=gerar_ticket_view(self, canal_ticket, membro, ticket_id)
            )

            await interaction.followup.send(f"✅ Ticket criado: {canal_ticket.mention}", ephemeral=True)
            print(f"✅ Ticket #{ticket_id} criado por {membro.name}")
        
        except Exception as e:
            import traceback
            print(f"❌ Erro ao criar ticket: {type(e).__name__}: {e}")
            print(traceback.format_exc())
            try:
                await interaction.followup.send(f"❌ Erro ao criar ticket: {type(e).__name__}: {e}", ephemeral=True)
            except Exception as e2:
                print(f"❌ Erro ao enviar mensagem de erro: {e2}")

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
