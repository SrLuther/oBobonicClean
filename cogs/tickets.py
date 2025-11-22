# cogs/tickets.py
"""
Sistema de tickets (Versão Final: ID Numérico Sequencial)

Funcionalidades:
1. ID de ticket numérico sequencial (ID:1, ID:2...).
2. Nome de canal formatado: ticket-ID-NomeUsuario
3. O fluxo principal e as funções de ACEITAR/ENCERRAR/Arquivamento permanecem as mesmas.
"""

import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput
from discord import PermissionOverwrite
import random
import string
import datetime
import os
import json
import asyncio
import tempfile
from typing import Optional

# ==============================================================================
# 🧩 SEÇÃO 1: CONFIGURAÇÃO E CONSTANTES (Importa tudo do config.py)
# ==============================================================================
try:
    from config import (
        CANAL_PAINEL_ID, CANAL_ARQUIVO_ID, TICKET_CATEGORY_ID, CANAL_STATUS_ID,
        MOD_ROLE_IDS, STAFF_ROLE_ID, EXPIRACAO_TICKET_HORAS, TICKET_ID_LENGTH
    )
    # TICKET_ID_LENGTH não será mais usado, mas o mantemos por compatibilidade
except ImportError:
    print("⚠️ config.py não encontrado ou incompleto. Usando valores padrão.")
    CANAL_PAINEL_ID = 0
    CANAL_ARQUIVO_ID = 0 
    TICKET_CATEGORY_ID = 0
    CANAL_STATUS_ID = 0
    MOD_ROLE_IDS = []
    STAFF_ROLE_ID = []
    EXPIRACAO_TICKET_HORAS = 48
    TICKET_ID_LENGTH = 5

# Paths de Arquivo
DATA_DIR = "data"
TICKETS_JSON = os.path.join(DATA_DIR, "tickets.json")
TRANSCRIPTS_DIR = "transcripts"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

# Variável global para armazenar o ID do próximo ticket
_next_ticket_id = 1

# ==============================================================================
# 🛠️ SEÇÃO 2: HELPERS E UTILIDADES
# ==============================================================================

_json_lock = asyncio.Lock()

def normalize_to_list_int(x):
    """Converte valores de configuração para uma lista de IDs inteiros."""
    if isinstance(x, (int, str)) and str(x).isdigit():
        return [int(x)]
    if isinstance(x, (list, tuple)):
        return [int(item) for item in x if str(item).isdigit()]
    return []

# Combina cargos de Staff
STAFF_ROLES = list(set(normalize_to_list_int(STAFF_ROLE_ID) + normalize_to_list_int(MOD_ROLE_IDS)))

def utcnow():
    """Retorna o datetime UTC atual (sem timezone info)."""
    return datetime.datetime.utcnow()

async def _read_json_safe(path):
    """Lê um arquivo JSON de forma segura."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

async def _write_json_safe(path, data):
    """Escreve dados em JSON de forma segura."""
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tf:
            json.dump(data, tf, ensure_ascii=False, indent=2, default=str)
        os.replace(tf.name, path)
    except Exception as e:
        print(f"[tickets] erro ao escrever json: {e}")
        if os.path.exists(tf.name):
            os.remove(tf.name)

async def load_all_tickets():
    """Carrega todos os dados de tickets E o contador de ID."""
    global _next_ticket_id
    async with _json_lock:
        data = await _read_json_safe(TICKETS_JSON)
        # Carrega o próximo ID do contador, se existir
        _next_ticket_id = data.get("next_ticket_id", 1)
        return data.get("tickets", {})

async def save_all_tickets(tickets):
    """Salva todos os dados de tickets E o contador de ID."""
    global _next_ticket_id
    async with _json_lock:
        data = {
            "next_ticket_id": _next_ticket_id,
            "tickets": tickets
        }
        await _write_json_safe(TICKETS_JSON, data)

def get_next_ticket_id():
    """Retorna o próximo ID de ticket e incrementa o contador global."""
    global _next_ticket_id
    current_id = _next_ticket_id
    _next_ticket_id += 1
    return current_id


async def gerar_transcript_file(channel: discord.TextChannel):
    """Gera um arquivo de transcrição (transcript) do canal."""
    lines = [f"--- Transcript do Ticket: {channel.name} (ID: {channel.id}) ---"]
    try:
        async for m in channel.history(limit=None, oldest_first=True):
            ts = m.created_at.isoformat(timespec='seconds')
            author = f"{m.author.display_name} ({m.author.id})"
            content = m.content or ""
            if m.attachments:
                atts = " | attachments: " + ", ".join(a.url for a in m.attachments)
                content += atts
            if m.embeds and not content:
                content += " [EMBED: " + (m.embeds[0].title or "Sem título") + "]"
            
            lines.append("[{}] {}: {}".format(ts, author, content.replace('\n', ' ')))

    except Exception as e:
        lines.append(f"[ERROR] Falha ao ler histórico: {e}")

    text = "\n".join(lines)
    fd, path = tempfile.mkstemp(prefix=f"transcript-{channel.name}-", suffix=".txt", dir=TRANSCRIPTS_DIR)
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

def is_staff_member(member: discord.Member):
    """Verifica se o membro pertence à equipe de staff/moderação."""
    if member.guild_permissions.manage_messages:
        return True
    for rid in STAFF_ROLES:
        if rid in [r.id for r in member.roles]:
            return True
    return False

# ==============================================================================
# 🖥️ SEÇÃO 3: UI COMPONENTS (VIEWS E MODALS)
# ==============================================================================

class ConfirmArchiveView(View):
    """View para confirmação antes de deletar o canal."""
    def __init__(self, user, channel):
        super().__init__(timeout=60)
        self.user_id = user.id
        self.channel = channel
        
    @discord.ui.button(label="CONFIRMAR ARQUIVAMENTO", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if not (interaction.user.id == self.user_id or is_staff_member(interaction.user)):
             await interaction.response.send_message("❌ Apenas quem iniciou o comando ou a equipe pode confirmar.", ephemeral=True)
             return

        await interaction.response.edit_message(content="✅ Confirmação recebida. Arquivando ticket... O canal será deletado em instantes.", view=None)
        
        ok, err = await arquivar_ticket_por_canal(self.channel, by_user=interaction.user)
        
        if not ok and err != "Ticket não registrado. O canal foi deletado.":
            log = self.channel.guild.get_channel(CANAL_STATUS_ID)
            if log:
                await log.send(f"❌ Erro crítico ao arquivar: {err}")
            await self.channel.send(f"❌ Erro final ao arquivar: {err}")
            
    @discord.ui.button(label="CANCELAR", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="Arquivamento cancelado.", view=None)

class TicketControlView(View):
    """View com botões de ACEITAR e ENCERRAR enviada dentro do canal do ticket."""
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="ACEITAR", style=discord.ButtonStyle.blurple, custom_id="ticket_aceitar")
    async def aceitar_ticket(self, interaction: discord.Interaction, button: Button):
        if not is_staff_member(interaction.user):
            await interaction.response.send_message("❌ Apenas membros da equipe podem aceitar tickets.", ephemeral=True)
            return
        
        await interaction.response.defer()

        tickets = await load_all_tickets()
        channel_id_str = str(interaction.channel.id)
        info = tickets.get(channel_id_str)
        
        if not info or info.get("closed"):
            await interaction.followup.send("❌ Este ticket está fechado ou não registrado.", ephemeral=True)
            return

        if info.get("claimed_by"):
            await interaction.followup.send(f"⚠️ Este ticket já foi aceito por <@{info['claimed_by']}>.", ephemeral=True)
            return

        # Update JSON
        info["claimed_by"] = interaction.user.id
        info["claimed_at"] = utcnow().isoformat()
        await save_all_tickets(tickets)

        # Send Confirmation (Brasilia Time)
        brasilia_tz = datetime.timezone(datetime.timedelta(hours=-3))
        now_brasilia = datetime.datetime.now(brasilia_tz).strftime("%d/%m/%Y às %H:%M:%S")
        
        await interaction.followup.send(
            f"✅ Ticket **aceito** por {interaction.user.mention}."
            f"\n*Atendimento iniciado em: {now_brasilia} (Horário de Brasília).*"
        )
        
    @discord.ui.button(label="ENCERRAR", style=discord.ButtonStyle.red, custom_id="ticket_encerrar")
    async def encerrar_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        tickets = await load_all_tickets()
        info = tickets.get(str(interaction.channel.id))
        
        if not info:
             await interaction.followup.send("❌ Este canal não está registrado como um ticket ativo.", ephemeral=True)
             return
             
        # Envia View de confirmação
        await interaction.followup.send(
            "⚠️ Você tem certeza que deseja **ENCERRAR** e arquivar este ticket? Isso irá gerar o histórico e deletar o canal.",
            view=ConfirmArchiveView(interaction.user, interaction.channel),
            ephemeral=True
        )

class ReasonModal(Modal):
    """Modal para coletar o motivo e descrição do ticket."""
    def __init__(self):
        super().__init__(title="Abrir Ticket de Suporte")
        self.reason = TextInput(
            label="Motivo principal do suporte",
            style=discord.TextStyle.short,
            required=True,
            max_length=256,
            placeholder="Ex: Problema com o pagamento / Dúvida técnica"
        )
        self.description = TextInput(
            label="Descrição detalhada (opcional)", 
            style=discord.TextStyle.long, 
            required=False, 
            max_length=1000,
            placeholder="Descreva seu problema para a equipe."
        )
        self.add_item(self.reason)
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        # Deferir imediatamente (Corrige o "Algo deu errado" / Timeout)
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Chama a função principal de criação de ticket
        await criar_ticket(interaction, self.reason.value, self.description.value or "")

class PainelView(View):
    """View persistente com UM ÚNICO BOTÃO de ABRIR TICKET."""
    def __init__(self, bot):
        super().__init__(timeout=None) 
        self.bot = bot

    @discord.ui.button(label="🎫 ABRIR TICKET", style=discord.ButtonStyle.green, custom_id="abrir_ticket_unico")
    async def abrir_ticket(self, interaction: discord.Interaction, button: Button):
        await abrir_etapas(interaction) 

async def abrir_etapas(interaction: discord.Interaction):
    """Checa anti-spam e mostra o Modal de Motivo."""
    author = interaction.user
    tickets = await load_all_tickets()
    
    # Checagem anti-spam
    for v in tickets.values():
        if v.get("owner") == author.id and not v.get("closed", False):
            await interaction.response.send_message("⚠️ Você já tem um ticket aberto registrado. Feche-o antes de abrir outro.", ephemeral=True)
            return

    # Checa canais ativos na Categoria
    guild = interaction.guild
    category = guild.get_channel(TICKET_CATEGORY_ID)
    if category and isinstance(category, discord.CategoryChannel):
        for ch in category.channels:
            if ch.topic and "owner:{}".format(author.id) in (ch.topic or "") and not ch.name.startswith("archived-"):
                await interaction.response.send_message("⚠️ Você já tem um ticket aberto no canal {}. Por favor, use este canal para continuar.".format(ch.mention), ephemeral=True)
                return

    # Envia Modal
    modal = ReasonModal()
    await interaction.response.send_modal(modal)

async def criar_ticket(interaction: discord.Interaction, reason: str, descricao: str = ""):
    """Cria o canal de ticket, registra e envia o painel de controle."""
    guild = interaction.guild
    author = interaction.user
    tickets = await load_all_tickets()

    category = guild.get_channel(TICKET_CATEGORY_ID)
    if not isinstance(category, discord.CategoryChannel):
        await interaction.followup.send("❌ Categoria de tickets não encontrada ou inválida. Contate a moderação.", ephemeral=True)
        log_c = guild.get_channel(CANAL_STATUS_ID)
        if log_c:
             await log_c.send(f"⚠️ **ATENÇÃO STAFF:** O ID de Categoria configurado (`{TICKET_CATEGORY_ID}`) para tickets é inválido ou não existe.", allowed_mentions=discord.AllowedMentions.none())
        return

    # === NOVO: Geração do ID Numérico ===
    ticket_id = get_next_ticket_id()
    
    # === NOVO: Formatação do Nome do Canal (ticket-ID-nome) ===
    clean_name = ''.join(c for c in author.name if c.isalnum() or c in ('-')) 
    # Max de 80 caracteres para nome, com buffer de 20 para o prefixo/sufixo
    max_name_len = 80 - len(str(ticket_id)) - 8 # 8 é o 'ticket--'
    name_suffix = clean_name[:max_name_len].lower()
    name = f"ticket-{ticket_id}-{name_suffix}"
    
    # Configuração de Permissões
    overwrites = {
        guild.default_role: PermissionOverwrite(view_channel=False),
        author: PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True, embed_links=True, attach_files=True),
        guild.me: PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    for rid in STAFF_ROLES:
        role = guild.get_role(rid)
        if role:
            overwrites[role] = PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)

    try:
        safe_reason = reason.replace('\n', ' ').replace('\\', '').replace('"', '').replace("'", '')
        channel_topic = "ticket_id:{} owner:{} reason:{}".format(
            ticket_id, 
            author.id, 
            safe_reason
        )

        channel = await guild.create_text_channel(
            name=name,
            category=category,
            overwrites=overwrites,
            topic=channel_topic
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ Erro: O bot não tem permissão para criar canais.", ephemeral=True)
        return
    except Exception as e:
        error_msg = "❌ Erro desconhecido ao criar canal do ticket: {}".format(e)
        await interaction.followup.send(error_msg, ephemeral=True)
        return

    # Registro no JSON
    now = utcnow().isoformat()
    tickets[str(channel.id)] = {
        "owner": author.id,
        "opened_at": now,
        "claimed_by": None,
        "ticket_id": ticket_id, # ID é agora um INT
        "reason": reason,
        "description": descricao,
        "closed": False
    }
    await save_all_tickets(tickets) # Salva tickets e incrementa o _next_ticket_id

    # Mensagem de Boas-vindas com painel de controle
    # === NOVO: Título da Mensagem como solicitado ===
    embed = discord.Embed(
        title=f"Ticket ID:{ticket_id} | {author.name}", 
        description=(
            "**Motivo:** {}\n"
            "**Descrição:** {}\n\n"
            "⚠️ **Aguardando Atendimento:** A equipe irá clicar em **ACEITAR** para iniciar. Você pode usar este canal para fornecer mais detalhes."
        ).format(reason, descricao or '—'), 
        color=discord.Color.green(),
        timestamp=datetime.datetime.utcnow()
    )
    # A menção está no content, o embed pode usar o nome
    embed.set_author(name=f"Aberto por: {author.display_name}", icon_url=author.display_avatar.url)
    embed.set_footer(text="ID do Ticket: {} | Abertura: {}".format(ticket_id, now)) 
    
    control_view = TicketControlView(interaction.client) 
    await channel.send(content="{}".format(author.mention), embed=embed, view=control_view)
    
    await interaction.followup.send("✅ Seu ticket foi criado: {}".format(channel.mention), ephemeral=True)

    # Log de status
    log_c = guild.get_channel(CANAL_STATUS_ID)
    if log_c and isinstance(log_c, discord.TextChannel):
        await log_c.send("🟢 Ticket criado: {} (ID {}) por {}".format(channel.name, ticket_id, author.mention))


# ==============================================================================
# 🚀 SEÇÃO 4: LÓGICA DE GERENCIAMENTO (AÇÕES)
# ==============================================================================

async def fechar_ticket_por_canal(channel: discord.TextChannel, by_user: discord.Member = None):
    # ... (lógica inalterada)
    tickets = await load_all_tickets()
    channel_id_str = str(channel.id)
    info = tickets.get(channel_id_str)
    
    if not info or info.get("closed"):
        return False, "Ticket não registrado ou já está fechado."

    info["closed"] = True
    info["closed_at"] = utcnow().isoformat()
    await save_all_tickets(tickets)
    
    owner = channel.guild.get_member(info.get('owner'))
    overwrites = channel.overwrites
    
    if owner:
        overwrites[owner] = PermissionOverwrite(view_channel=True, send_messages=False, read_messages=True)
    
    try:
        await channel.edit(overwrites=overwrites)
        await channel.send("🔒 Ticket **fechado**. Use `!reabrir` para continuar ou `!transcript`.")
    except discord.Forbidden:
        await channel.send("⚠️ Não consegui remover as permissões de envio de mensagens. Permissões insuficientes.")
    
    log = channel.guild.get_channel(CANAL_STATUS_ID)
    if log and isinstance(log, discord.TextChannel):
        who = by_user.mention if by_user else "Sistema"
        await log.send("🔒 Ticket {} fechado por {}".format(channel.name, who))
    
    return True, None

async def arquivar_ticket_por_canal(channel: discord.TextChannel, by_user: discord.Member = None):
    # ... (lógica inalterada - Tratamento de Falha do Arquivo)
    tickets = await load_all_tickets()
    channel_id_str = str(channel.id)
    info = tickets.pop(channel_id_str, None)

    if not info:
        try:
             await channel.delete(reason="Arquivado por {} (Registro não encontrado).".format(by_user.name if by_user else 'Sistema'))
        except:
             pass
        return False, "Ticket não registrado. O canal foi deletado."

    # 1. Generate Transcript File
    path = await gerar_transcript_file(channel)
    
    # 2. Setup Archive Destination
    archive_id = CANAL_ARQUIVO_ID 
    arquivo = channel.guild.get_channel(archive_id)
    
    archive_failed = False
    
    # 3. Build Filename 
    ticket_id = info.get("ticket_id", "UNKNOWN")
    owner_member = channel.guild.get_member(info.get('owner'))
    owner_name_safe = owner_member.name if owner_member else "UnknownUser"
    owner_name_safe = ''.join(c for c in owner_name_safe if c.isalnum() or c in ('-'))[:20]
    filename = f"{ticket_id}-{owner_name_safe}-transcript.txt" 

    # 4. Send Transcript (Somente se o canal for válido)
    if arquivo and isinstance(arquivo, discord.TextChannel):
        owner_mention = owner_member.mention if owner_member else f"<@{info.get('owner')}>"

        embed = discord.Embed(
            title=f"📁 Ticket Arquivado: ID {ticket_id}", 
            description=f"Canal: **{channel.name}**\n**Aberto por:** {owner_mention}", 
            color=discord.Color.greyple(), 
            timestamp=utcnow()
        )
        if by_user:
            embed.add_field(name="Arquivado por", value=by_user.mention, inline=False)
        embed.add_field(name="Motivo", value=info.get("reason", "—"), inline=True)
        
        try:
            await arquivo.send(embed=embed)
            await arquivo.send(file=discord.File(path, filename=filename))
        except Exception as e:
            archive_failed = True
            log = channel.guild.get_channel(CANAL_STATUS_ID)
            if log:
                await log.send(f"❌ Erro ao enviar transcript para o canal de arquivamento (ID `{archive_id}`). Falha: {e}")
            await channel.send("⚠️ Erro ao enviar transcript para o canal de arquivamento. Deletando canal.", delete_after=10)
    else:
        archive_failed = True
        log = channel.guild.get_channel(CANAL_STATUS_ID)
        if log and isinstance(log, discord.TextChannel):
            await log.send(
                f"🚨 **ALERTA DE CONFIGURAÇÃO:** Falha ao arquivar ticket `{info.get('ticket_id')}`! "
                f"O canal de arquivamento configurado (ID `{archive_id}`) não foi encontrado. "
                f"O transcript NÃO foi salvo. Por favor, use `!set_archive_id <NOVO_ID>` para corrigir."
            )
            
    await save_all_tickets(tickets) 

    # 5. Deleta o canal (Continua o processo de exclusão)
    try:
        await channel.delete(reason="Arquivado por {}".format(by_user.name if by_user else 'Sistema'))
    except Exception:
        log = channel.guild.get_channel(CANAL_STATUS_ID)
        if log:
             await log.send("❌ ATENÇÃO: Bot falhou ao deletar o canal {} por falta de permissão. Registro removido do JSON.".format(channel.name))
        return False, "O bot não tem permissão para deletar o canal."
        
    # 6. Log e Limpeza
    log = channel.guild.get_channel(CANAL_STATUS_ID)
    if log and isinstance(log, discord.TextChannel):
        who = by_user.mention if by_user else "Sistema"
        await log.send("📁 Ticket {} arquivado por {}".format(channel.name, who))
    
    try:
        os.remove(path)
    except Exception:
        pass
        
    if archive_failed:
        return False, "Ticket arquivado (deletado), mas falha ao salvar o transcript no canal de arquivo."
    return True, None

async def reabrir_por_canal(channel: discord.TextChannel, by_user: discord.Member = None):
    # ... (lógica inalterada)
    tickets = await load_all_tickets()
    channel_id_str = str(channel.id)
    info = tickets.get(channel_id_str)
    
    if not info or not info.get("closed"):
        return False, "Ticket não registrado ou já está aberto."
        
    info["closed"] = False
    info.pop("closed_at", None)
    tickets[channel_id_str] = info
    await save_all_tickets(tickets)
    
    owner = channel.guild.get_member(info.get('owner'))
    overwrites = channel.overwrites
    
    if owner:
        overwrites[owner] = PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)

    try:
        await channel.edit(overwrites=overwrites)
        await channel.send("🔓 Ticket **reaberto**. O canal está novamente ativo para mensagens.")
    except discord.Forbidden:
        await channel.send("⚠️ Não consegui restaurar as permissões de envio de mensagens. Permissões insuficientes.")
        
    log = channel.guild.get_channel(CANAL_STATUS_ID)
    if log and isinstance(log, discord.TextChannel):
        who = by_user.mention if by_user else "Sistema"
        await log.send("🔓 Ticket {} reaberto por {}".format(channel.name, who))
        
    return True, None

# ==============================================================================
# 🤖 SEÇÃO 5: COG PRINCIPAL E COMANDOS DE PREFIXO
# ==============================================================================

class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_inatividade.start()
        
    # --- Comando de Setup do Painel ---
    @commands.command(name="ticketpanel")
    @commands.has_permissions(manage_messages=True)
    async def cmd_ticket_panel(self, ctx):
        # ... (lógica de setup do painel - inalterada)
        TARGET_PANEL_ID = CANAL_PAINEL_ID
        
        if not TARGET_PANEL_ID:
             await ctx.send("❌ ID do canal de painel (CANAL_PAINEL_ID) não configurado.", delete_after=8)
             return
             
        canal = ctx.guild.get_channel(TARGET_PANEL_ID)
        if not isinstance(canal, discord.TextChannel):
            await ctx.send("❌ Canal de painel não encontrado ou não é um canal de texto. Verifique o config.", delete_after=8)
            return
            
        EXPIRACAO = EXPIRACAO_TICKET_HORAS
        
        embed = discord.Embed(
            title="🎫 Sistema de Tickets de Suporte", 
            description="Use o botão abaixo para iniciar uma conversa **privada** com a nossa equipe de suporte.", 
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="1️⃣ Como Abrir um Ticket?",
            value=(
                "**1.** Clique no botão **`🎫 ABRIR TICKET`**.\n"
                "**2.** Preencha o formulário com o **motivo** e a **descrição**.\n"
                "**3.** Um canal de texto privado será criado para você e a equipe."
            ),
            inline=False
        )

        embed.add_field(
            name="2️⃣ Fluxo de Atendimento",
            value=(
                "* **Abertura:** O canal é criado. Um moderador irá clicar em **ACEITAR**.\n"
                "* **Resolução:** Use o botão **ENCERRAR** (ou a equipe fechará) para finalizar e arquivar a conversa."
            ),
            inline=False
        )
        
        embed.add_field(
            name="⏳ Fechamento Automático",
            value=(
                f"* **Inatividade:** Se o ticket ficar inativo por **{EXPIRACAO} horas**, ele será fechado automaticamente (sem arquivar).\n"
                "* **Comandos:** Use comandos de emergência como `!reabrir` e `!transcript`."
            ),
            inline=False
        )
        
        embed.set_footer(text="Aguarde o atendimento. O tempo de resposta pode variar.")

        await canal.send(embed=embed, view=PainelView(self.bot)) 
        
        await ctx.send("✅ Painel de tickets enviado.", delete_after=7)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    # --- Helper para comandos ---
    def _is_ticket_channel(self, channel: discord.TextChannel, tickets):
        """Verifica se o canal atual é um ticket registrado."""
        if channel and channel.topic and "ticket_id:" in channel.topic:
            info = tickets.get(str(channel.id))
            if info:
                return True, info
        return False, None

    # --- Comandos de Gerenciamento (inalterados) ---
    @commands.command(name="fechar")
    async def cmd_fechar(self, ctx):
        """Fecha o ticket no canal atual (Apenas remove permissão de envio)."""
        tickets = await load_all_tickets()
        is_ticket, info = self._is_ticket_channel(ctx.channel, tickets)

        if not is_ticket:
            await ctx.send("❌ Este comando deve ser usado em um canal de ticket.", delete_after=5)
            return

        owner = info.get("owner")
        if not (ctx.author.id == owner or is_staff_member(ctx.author)):
            await ctx.send("❌ Apenas o autor do ticket ou um moderador pode fechar este ticket.", delete_after=5)
            return

        try:
            await ctx.message.delete()
        except Exception:
            pass
            
        ok, err = await fechar_ticket_por_canal(ctx.channel, by_user=ctx.author)
        if not ok:
            await ctx.channel.send("❌ Erro ao fechar: {}".format(err))

    @commands.command(name="arquivar")
    @commands.has_permissions(manage_messages=True)
    async def cmd_arquivar(self, ctx):
        """Arquiva (deleta) o ticket no canal atual após gerar transcript."""
        tickets = await load_all_tickets()
        is_ticket, _ = self._is_ticket_channel(ctx.channel, tickets)

        if not is_ticket:
            await ctx.send("❌ Este comando deve ser usado em um canal de ticket.", delete_after=5)
            return
        
        try:
            await ctx.message.delete()
        except Exception:
            pass
            
        await ctx.send(
            "⚠️ Você tem certeza que deseja **ENCERRAR** e arquivar este ticket? O canal será deletado.",
            view=ConfirmArchiveView(ctx.author, ctx.channel)
        )


    @commands.command(name="transcript")
    async def cmd_transcript(self, ctx):
        """Gera o transcript do ticket e envia como arquivo temporário."""
        tickets = await load_all_tickets()
        is_ticket, info = self._is_ticket_channel(ctx.channel, tickets)
        
        if not is_ticket:
            await ctx.send("❌ Este comando deve ser usado em um canal de ticket.", delete_after=5)
            return
            
        owner = info.get("owner")
        if not (ctx.author.id == owner or is_staff_member(ctx.author)):
            await ctx.send("❌ Apenas o autor do ticket ou um moderador pode gerar o transcript.", delete_after=5)
            return
            
        await ctx.send("📝 Gerando transcript...", delete_after=5)
        path = await gerar_transcript_file(ctx.channel)
        
        try:
            ticket_id = info.get("ticket_id", "UNKNOWN")
            owner_member = ctx.guild.get_member(info.get('owner'))
            owner_name_safe = ''.join(c for c in owner_member.name if c.isalnum() or c in ('-'))[:20] if owner_member else "UnknownUser"
            filename = f"{ticket_id}-{owner_name_safe}-transcript.txt"

            await ctx.channel.send("📝 Transcript gerado:", file=discord.File(path, filename=filename))
            try:
                await ctx.message.delete()
            except:
                pass
        except Exception:
            await ctx.author.send("❌ Erro ao enviar transcript. Verifique as permissões de anexo do bot.")
        finally:
            try:
                os.remove(path)
            except Exception:
                pass


    @commands.command(name="reabrir")
    async def cmd_reabrir(self, ctx):
        """Reabre um ticket fechado."""
        tickets = await load_all_tickets()
        is_ticket, info = self._is_ticket_channel(ctx.channel, tickets)

        if not is_ticket:
            await ctx.send("❌ Este comando deve ser usado em um canal de ticket.", delete_after=5)
            return

        owner = info.get("owner")
        if not (ctx.author.id == owner or is_staff_member(ctx.author)):
            await ctx.send("❌ Apenas o autor do ticket ou um moderador pode reabrir este ticket.", delete_after=5)
            return

        try:
            await ctx.message.delete()
        except Exception:
            pass
            
        ok, err = await reabrir_por_canal(ctx.channel, by_user=ctx.author)
        if not ok:
            await ctx.channel.send("❌ Erro ao reabrir: {}".format(err))
            
    @commands.command(name="set_archive_id")
    @commands.has_permissions(administrator=True) 
    async def cmd_set_archive_id(self, ctx, new_id: Optional[int]):
        """Define o novo ID do canal de arquivamento em tempo de execução."""
        global CANAL_ARQUIVO_ID
        
        if not new_id:
            await ctx.send(f"❌ Uso: `!set_archive_id <ID_DO_CANAL>`. O ID atual é `{CANAL_ARQUIVO_ID}`.", delete_after=10)
            return

        channel = ctx.guild.get_channel(new_id)
        if not isinstance(channel, discord.TextChannel):
            await ctx.send("❌ O ID fornecido não é um canal de texto válido no servidor.", delete_after=10)
            return
            
        CANAL_ARQUIVO_ID = new_id

        await ctx.send(f"✅ O ID do canal de arquivamento foi atualizado com sucesso para **{channel.mention}** (`{new_id}`).", delete_after=15)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    # --- Listener de Interações ---
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        # ... (lógica inalterada)
        if interaction.type != discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get("custom_id")
        
        if custom_id in ("abrir_ticket_unico", "ticket_aceitar", "ticket_encerrar"):
             pass 
        else:
             return

    # --- Tarefa de Verificação de Inatividade ---
    @tasks.loop(hours=1)
    async def check_inatividade(self):
        # ... (lógica de inatividade - inalterada)
        if not self.bot.is_ready() or not self.bot.guilds:
            return
        
        guild = self.bot.guilds[0]
        category = guild.get_channel(TICKET_CATEGORY_ID)
        
        if not isinstance(category, discord.CategoryChannel) or EXPIRACAO_TICKET_HORAS <= 0:
            return
            
        limite = utcnow() - datetime.timedelta(hours=EXPIRACAO_TICKET_HORAS)
        tickets = await load_all_tickets()
        
        for ch in list(category.channels):
            if not isinstance(ch, discord.TextChannel):
                continue
            
            info = tickets.get(str(ch.id))
            if not info or info.get("closed"):
                continue
                
            try:
                last = None
                async for m in ch.history(limit=1, oldest_first=False):
                    last = m
                    break
                    
                last_time = last.created_at.replace(tzinfo=None) if last else ch.created_at.replace(tzinfo=None)
                
                if last_time < limite:
                    await ch.send("⏰ Ticket fechado automaticamente por inatividade (última mensagem há mais de {} horas).".format(EXPIRACAO_TICKET_HORAS))
                    await fechar_ticket_por_canal(ch, by_user=None) 
                    
            except discord.NotFound:
                if str(ch.id) in tickets:
                    tickets.pop(str(ch.id))
                    await save_all_tickets(tickets)
            except Exception as e:
                print("[tickets] Erro ao checar inatividade no canal {}: {}".format(ch.name, e))
                continue

    @check_inatividade.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()
        
    def cog_unload(self):
        try:
            self.check_inatividade.cancel()
        except Exception:
            pass

# ==============================================================================
# 📝 SEÇÃO 6: SETUP
# ==============================================================================
async def setup(bot):
    """Função de registro do cog e da view persistente."""
    # Garante que o contador de tickets seja carregado na inicialização
    await load_all_tickets() 
    
    cog = TicketsCog(bot)
    await bot.add_cog(cog)
    
    bot.add_view(PainelView(bot))
    bot.add_view(TicketControlView(bot))