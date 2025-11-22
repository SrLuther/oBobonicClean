# cogs/tickets.py
"""
Sistema de tickets completo: 
- 1 Botão de Abrir Ticket no painel.
- Gerenciamento feito por comandos de prefixo (!fechar, !arquivar, etc.).
- Painel informativo detalhado.
- Estabilidade aprimorada nas interações.
- CORREÇÃO FINAL V2: Garantia de que strings multi-linhas não causem SyntaxError de backslash no carregamento.
"""

import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select, Modal, TextInput
from discord import PermissionOverwrite
import random
import string
import datetime
import os
import json
import asyncio
import tempfile
import time 

# ---------------------------
# Configuração (Importação e Fallback)
# ---------------------------
try:
    from config import (
        CANAL_PAINEL_ID,
        CANAL_ARQUIVO_ID,
        TICKET_CATEGORY_ID,
        MOD_ROLE_IDS,
        STAFF_ROLE_ID,
        EXPIRACAO_TICKET_HORAS,
        TICKET_ID_LENGTH,
        CANAL_STATUS_ID
    )
except ImportError:
    # Valores Padrão de Falha (IMPORTANTE: Configure seu config.py!)
    CANAL_PAINEL_ID = 0
    CANAL_ARQUIVO_ID = 0
    TICKET_CATEGORY_ID = 0
    MOD_ROLE_IDS = []
    STAFF_ROLE_ID = []
    EXPIRACAO_TICKET_HORAS = 24
    TICKET_ID_LENGTH = 5
    CANAL_STATUS_ID = 0


# ---------------------------
# Paths / Helpers (Funções de Arquivo e Utilidade)
# ---------------------------
DATA_DIR = "data"
TICKETS_JSON = os.path.join(DATA_DIR, "tickets.json")
TRANSCRIPTS_DIR = "transcripts"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

_json_lock = asyncio.Lock()

def normalize_to_list_int(x):
    if x is None:
        return []
    if isinstance(x, (int, str)):
        try:
            return [int(x)]
        except ValueError:
            return []
    if isinstance(x, (list, tuple)):
        return [int(item) for item in x if isinstance(item, (int, str)) and str(item).isdigit()]
    return []

# Compila as listas de IDs de cargos de Staff
STAFF_ROLES = normalize_to_list_int(STAFF_ROLE_ID) + normalize_to_list_int(MOD_ROLE_IDS)
STAFF_ROLES = list(set(STAFF_ROLES))

def gerar_ticket_id():
    length = TICKET_ID_LENGTH if isinstance(TICKET_ID_LENGTH, int) and TICKET_ID_LENGTH > 0 else 5
    return "T-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def utcnow():
    return datetime.datetime.utcnow()

async def _read_json_safe(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

async def _write_json_safe(path, data):
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tf:
            json.dump(data, tf, ensure_ascii=False, indent=2, default=str)
        os.replace(tf.name, path)
    except Exception as e:
        print(f"[tickets] erro ao escrever json: {e}")
        if os.path.exists(tf.name):
            os.remove(tf.name)

async def load_all_tickets():
    async with _json_lock:
        data = await _read_json_safe(TICKETS_JSON)
        return data.get("tickets", {})

async def save_all_tickets(tickets):
    async with _json_lock:
        await _write_json_safe(TICKETS_JSON, {"tickets": tickets})

async def gerar_transcript_file(channel: discord.TextChannel):
    lines = [f"--- Transcript do Ticket: {channel.name} (ID: {channel.id}) ---"]
    try:
        async for m in channel.history(limit=None, oldest_first=True):
            ts = m.created_at.isoformat(timespec='seconds')
            author = f"{m.author.display_name} ({m.author.id})"
            content = m.content or ""
            if m.attachments:
                atts = " | attachments: " + ", ".join(a.url for a in m.attachments)
                content = content + atts
            if m.embeds and not content:
                content = content + " [EMBED: " + (m.embeds[0].title or "Sem título") + "]"
            lines.append(f"[{ts}] {author}: {content.replace('\n', ' ')}")
    except Exception as e:
        lines.append(f"[ERROR] Falha ao ler histórico: {e}")

    text = "\n".join(lines)
    fd, path = tempfile.mkstemp(prefix=f"transcript-{channel.name}-", suffix=".txt", dir=TRANSCRIPTS_DIR)
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

def is_staff_member(member: discord.Member):
    if member.guild_permissions.manage_messages:
        return True
    for rid in STAFF_ROLES:
        if rid in [r.id for r in member.roles]:
            return True
    return False

# ---------------------------
# UI Components: Modal / Select / Views (Fluxo de Abertura)
# ---------------------------
class DescricaoModal(Modal):
    def __init__(self, reason: str):
        super().__init__(title="Descreva seu problema (opcional)")
        self.reason = reason
        self.descricao = TextInput(
            label="Descrição (máx 1000 caracteres)", 
            style=discord.TextStyle.long, 
            required=False, 
            max_length=1000,
            placeholder="Forneça detalhes que ajudem nossa equipe a te auxiliar."
        )
        self.add_item(self.descricao)

    async def on_submit(self, interaction: discord.Interaction):
        await criar_ticket(interaction, self.reason, self.descricao.value or "")

class MotivoSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Suporte Técnico", description="Ajuda técnica, bugs, dúvidas gerais", emoji="🛠️"),
            discord.SelectOption(label="Compras/Pagamentos", description="Pedidos, valores, status de pagamento", emoji="💰"),
            discord.SelectOption(label="Parcerias/Comercial", description="Propostas ou assuntos de negócios", emoji="🤝"),
            discord.SelectOption(label="Denúncia/Report", description="Reportar infrações de regras ou usuários", emoji="🚨"),
            discord.SelectOption(label="Outro Assunto", description="Assunto não listado acima", emoji="❓")
        ]
        super().__init__(placeholder="Escolha o motivo do seu ticket...", min_values=1, max_values=1, options=options, custom_id="motivo_select_id")

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        modal = DescricaoModal(reason=chosen)
        await interaction.response.send_modal(modal)

class MotivoView(View):
    def __init__(self):
        super().__init__(timeout=300) 
        self.add_item(MotivoSelect())
        
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class PainelView(View):
    """View persistente com UM ÚNICO BOTÃO de ABRIR TICKET."""
    def __init__(self, bot):
        super().__init__(timeout=None) # timeout=None torna a View persistente
        self.bot = bot

    @discord.ui.button(label="🎫 ABRIR TICKET", style=discord.ButtonStyle.green, custom_id="abrir_ticket_unico")
    async def abrir_ticket(self, interaction: discord.Interaction, button: Button):
        await abrir_etapas(interaction) 

# ---------------------------
# Fluxo: abrir etapas / criar ticket
# ---------------------------
async def abrir_etapas(interaction: discord.Interaction):
    """Primeira etapa: checa anti-spam e mostra o select de motivo."""
    author = interaction.user
    tickets = await load_all_tickets()
    
    # 1. Checa se o usuário já tem um ticket ativo no JSON
    for v in tickets.values():
        if v.get("owner") == author.id and not v.get("closed", False):
            await interaction.response.send_message("⚠️ Você já tem um ticket aberto registrado. Feche-o antes de abrir outro.", ephemeral=True)
            return

    # 2. Checa se o usuário já tem um canal de ticket aberto na Categoria
    guild = interaction.guild
    category = guild.get_channel(TICKET_CATEGORY_ID)
    if category and isinstance(category, discord.CategoryChannel):
        for ch in category.channels:
            if ch.topic and f"owner:{author.id}" in (ch.topic or "") and not ch.name.startswith("archived-"):
                await interaction.response.send_message(f"⚠️ Você já tem um ticket aberto no canal {ch.mention}. Por favor, use este canal para continuar.", ephemeral=True)
                return

    # 3. Mostra o Select de Motivo
    await interaction.response.send_message("Escolha o motivo do ticket:", view=MotivoView(), ephemeral=True)

async def criar_ticket(interaction: discord.Interaction, reason: str, descricao: str = ""):
    """Cria o canal de ticket e registra no JSON."""
    guild = interaction.guild
    author = interaction.user
    tickets = await load_all_tickets()

    # Segunda checagem para evitar race condition
    for v in tickets.values():
        if v.get("owner") == author.id and not v.get("closed", False):
            await interaction.followup.send("⚠️ Você já tem um ticket aberto.", ephemeral=True)
            return

    category = guild.get_channel(TICKET_CATEGORY_ID)
    if not isinstance(category, discord.CategoryChannel):
        await interaction.followup.send("❌ Categoria de tickets não encontrada ou inválida. Contate a moderação.", ephemeral=True)
        return

    ticket_id = gerar_ticket_id()
    clean_name = ''.join(c for c in author.name if c.isalnum() or c in ('-')) 
    name = f"ticket-{clean_name[:15]}-{ticket_id}".lower()[:90]

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
        # CORREÇÃO: Usando .format() e limpando o 'reason' e removendo backslashes
        # que poderiam causar o SyntaxError.
        safe_reason = reason.replace('\n', ' ').replace('\\', '') 
        
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
        # CORREÇÃO: Usando str.format() para a mensagem de erro para evitar o SyntaxError
        error_msg = "❌ Erro desconhecido ao criar canal do ticket: {}".format(e)
        await interaction.followup.send(error_msg, ephemeral=True)
        return

    # Registro no JSON
    now = utcnow().isoformat()
    tickets[str(channel.id)] = {
        "owner": author.id,
        "opened_at": now,
        "claimed_by": None,
        "ticket_id": ticket_id,
        "reason": reason,
        "description": descricao,
        "closed": False
    }
    await save_all_tickets(tickets)

    # Mensagem de Boas-vindas no Ticket
    embed = discord.Embed(
        title=f"🎫 Ticket {ticket_id}: {reason}",
        description=(
            f"**Usuário:** {author.mention}\n"
            f"**Descrição:** {descricao or '—'}\n\n"
            f"Aguarde. Um membro da equipe irá atender em breve. "
        ),
        color=discord.Color.green(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_footer(text=f"ID do Ticket: {ticket_id} | Abertura: {now}")

    await channel.send(content=f"{author.mention}", embed=embed)
    
    # Confirmação para o usuário
    await interaction.followup.send(f"✅ Seu ticket foi criado: {channel.mention}", ephemeral=True)

    # Log de status
    log_c = guild.get_channel(CANAL_STATUS_ID)
    if log_c and isinstance(log_c, discord.TextChannel):
        await log_c.send(f"🟢 Ticket criado: {channel.name} (ID {ticket_id}) por {author.mention}")

# ---------------------------
# Actions (Lógica de Gerenciamento)
# ---------------------------
async def fechar_ticket_por_canal(channel: discord.TextChannel, by_user: discord.Member = None):
    tickets = await load_all_tickets()
    channel_id_str = str(channel.id)
    info = tickets.get(channel_id_str)
    
    if not info or info.get("closed"):
        return False, "Ticket não registrado ou já está fechado."

    info["closed"] = True
    info["closed_at"] = utcnow().isoformat()
    tickets[channel_id_str] = info
    await save_all_tickets(tickets)

    owner = channel.guild.get_member(info.get('owner'))
    overwrites = channel.overwrites
    
    # Revoga permissão de enviar mensagens ao owner
    if owner:
        overwrites[owner] = PermissionOverwrite(view_channel=True, send_messages=False, read_messages=True)
    
    # Mantém permissão de ver/ler para Staff
    for rid in STAFF_ROLES:
        role = channel.guild.get_role(rid)
        if role:
             overwrites[role] = PermissionOverwrite(view_channel=True, send_messages=False, manage_messages=True)

    try:
        await channel.edit(overwrites=overwrites)
        await channel.send("🔒 Ticket **fechado**. Use `!reabrir` para continuar ou `!transcript`.")
    except discord.Forbidden:
        await channel.send("⚠️ Não consegui remover as permissões de envio de mensagens. Permissões insuficientes.")
    except Exception:
        pass
        
    log = channel.guild.get_channel(CANAL_STATUS_ID)
    if log and isinstance(log, discord.TextChannel):
        who = by_user.mention if by_user else "Sistema"
        await log.send(f"🔒 Ticket {channel.name} fechado por {who}")
    
    return True, None

async def arquivar_ticket_por_canal(channel: discord.TextChannel, by_user: discord.Member = None):
    tickets = await load_all_tickets()
    channel_id_str = str(channel.id)
    info = tickets.pop(channel_id_str, None)

    if not info:
        # Se o registro não existe, tenta deletar o canal para limpar
        try:
             await channel.delete(reason=f"Arquivado por {by_user.name if by_user else 'Sistema'} (Registro não encontrado).")
        except:
             pass
        return False, "Ticket não registrado. O canal foi deletado."

    path = await gerar_transcript_file(channel)
    arquivo = channel.guild.get_channel(CANAL_ARQUIVO_ID)
    
    # Envia o transcript para o canal de arquivos
    if arquivo and isinstance(arquivo, discord.TextChannel):
        owner_member = channel.guild.get_member(info.get('owner'))
        owner_mention = owner_member.mention if owner_member else f"<@{info.get('owner')}>"

        embed = discord.Embed(
            title="📁 Ticket Arquivado", 
            description=f"Ticket: **{channel.name}**\n**Aberto por:** {owner_mention}", 
            color=discord.Color.greyple(), 
            timestamp=utcnow()
        )
        if by_user:
            embed.add_field(name="Arquivado por", value=by_user.mention, inline=False)
        embed.add_field(name="ID", value=info.get("ticket_id", "—"), inline=True)
        embed.add_field(name="Motivo", value=info.get("reason", "—"), inline=True)
        
        try:
            await arquivo.send(embed=embed)
            await arquivo.send(file=discord.File(path, filename=f"{channel.name}-transcript.txt"))
        except discord.Forbidden:
            await channel.send("❌ Não consegui enviar o transcript para o canal de arquivamento (Permissão Negada). Deletando canal.", delete_after=10)
        except Exception:
            await channel.send("⚠️ Erro ao enviar transcript para o canal de arquivamento. Deletando canal.", delete_after=10)
    
    await save_all_tickets(tickets) # Salva o JSON sem o ticket

    # Deleta o canal
    try:
        await channel.delete(reason=f"Arquivado por {by_user.name if by_user else 'Sistema'}")
    except discord.Forbidden:
        log = channel.guild.get_channel(CANAL_STATUS_ID)
        if log:
             await log.send(f"❌ ATENÇÃO: Bot falhou ao deletar o canal {channel.name} por falta de permissão. Registro removido do JSON.")
        return False, "O bot não tem permissão para deletar o canal."
    except Exception:
        pass
        
    log = channel.guild.get_channel(CANAL_STATUS_ID)
    if log and isinstance(log, discord.TextChannel):
        who = by_user.mention if by_user else "Sistema"
        await log.send(f"📁 Ticket {channel.name} arquivado por {who}")
    
    try:
        os.remove(path)
    except Exception:
        pass
        
    return True, None

async def reabrir_por_canal(channel: discord.TextChannel, by_user: discord.Member = None):
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
    
    # Restaura permissão de enviar mensagens ao owner
    if owner:
        overwrites[owner] = PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)
    
    # Restaura permissão de enviar mensagens para Staff
    for rid in STAFF_ROLES:
        role = channel.guild.get_role(rid)
        if role:
            overwrites[role] = PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)

    try:
        await channel.edit(overwrites=overwrites)
        await channel.send("🔓 Ticket **reaberto**. O canal está novamente ativo para mensagens.")
    except discord.Forbidden:
        await channel.send("⚠️ Não consegui restaurar as permissões de envio de mensagens. Permissões insuficientes.")
    except Exception:
        pass
        
    log = channel.guild.get_channel(CANAL_STATUS_ID)
    if log and isinstance(log, discord.TextChannel):
        who = by_user.mention if by_user else "Sistema"
        await log.send(f"🔓 Ticket {channel.name} reaberto por {who}")
        
    return True, None

# ---------------------------
# COG (Comandos de Prefixos e Tarefas em Background)
# ---------------------------
class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_inatividade.start()

    # --- Comando de Setup do Painel (Informativo) ---
    @commands.command(name="ticketpanel")
    @commands.has_permissions(manage_messages=True)
    async def cmd_ticket_panel(self, ctx):
        """Envia o painel de abertura de tickets no canal configurado com instruções."""
        TARGET_PANEL_ID = CANAL_PAINEL_ID
        
        if not TARGET_PANEL_ID:
             await ctx.send("❌ ID do canal de painel (CANAL_PAINEL_ID) não configurado.", delete_after=8)
             return
             
        canal = ctx.guild.get_channel(TARGET_PANEL_ID)
        if not isinstance(canal, discord.TextChannel):
            await ctx.send("❌ Canal de painel não encontrado ou não é um canal de texto. Verifique o config.", delete_after=8)
            return
            
        EXPIRACAO = EXPIRACAO_TICKET_HORAS
        
        # NOTE: Não use f-string aqui (f"...") para evitar o SyntaxError com \n no carregamento.
        embed = discord.Embed(
            title="🎫 Sistema de Tickets de Suporte", 
            description="Use o botão abaixo para iniciar uma conversa **privada** com a nossa equipe de suporte.", 
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="1️⃣ Como Abrir um Ticket?",
            # Usando strings concatenadas (sem f"...")
            value=(
                "**1.** Clique no botão **`🎫 ABRIR TICKET`**.\n"
                "**2.** Escolha o **motivo** do seu suporte.\n"
                "**3.** Descreva seu problema (opcional).\n"
                "**4.** Um canal de texto privado será criado para você e a equipe."
            ),
            inline=False
        )

        embed.add_field(
            name="2️⃣ Do Clique à Solução (O Fluxo)",
            # Usando strings concatenadas (sem f"...")
            value=(
                "* **Abertura:** O canal é criado. Mencione novamente o problema.\n"
                "* **Atendimento:** Um membro da equipe irá se identificar e começar a te ajudar.\n"
                "* **Resolução:** Assim que o problema for resolvido, use **`!fechar`** (ou a equipe fechará) para finalizar a conversa."
            ),
            inline=False
        )
        
        embed.add_field(
            name="⏳ Fechamento Automático e Comandos",
            # A única f-string necessária aqui é simples e no fim do campo
            value=(
                f"* **Inatividade:** Se o ticket ficar inativo (sem mensagens) por **{EXPIRACAO} horas**, ele será fechado automaticamente.\n"
                "* **Reabertura:** Use o comando `!reabrir` dentro do canal para continuar após o fechamento.\n"
                "* **Transcrição:** Use `!transcript` para gerar o histórico da conversa."
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Aguarde o atendimento. O tempo de resposta pode variar.")

        # Envia o novo embed informativo com a view
        await canal.send(embed=embed, view=PainelView(self.bot)) 
        
        await ctx.send("✅ Painel de tickets enviado.", delete_after=7)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    # --- Helper para comandos ---
    def _is_ticket_channel(self, channel: discord.TextChannel, tickets):
        """Verifica se o canal atual é um ticket registrado."""
        if not channel or not channel.topic:
            return False, None
        if "ticket_id:" in channel.topic:
            info = tickets.get(str(channel.id))
            if info:
                return True, info
        return False, None

    # --- Comandos de Gerenciamento ---
    @commands.command(name="fechar")
    async def cmd_fechar(self, ctx):
        """Fecha o ticket no canal atual."""
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
            await ctx.channel.send(f"❌ Erro ao fechar: {err}")

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
            
        await ctx.send("📁 Arquivando ticket e gerando transcript... O canal será deletado em 5 segundos.")
        await asyncio.sleep(5)
        
        ok, err = await arquivar_ticket_por_canal(ctx.channel, by_user=ctx.author)
        if not ok:
            await ctx.channel.send(f"❌ Erro ao arquivar: {err}")


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
            await ctx.channel.send("📝 Transcript gerado:", file=discord.File(path, filename=f"{ctx.channel.name}-transcript.txt"))
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
            await ctx.channel.send(f"❌ Erro ao reabrir: {err}")
        

    @commands.command(name="ticket-admin")
    @commands.has_permissions(manage_messages=True)
    async def cmd_ticket_admin(self, ctx):
        """Lista todos os tickets abertos por DM."""
        tickets = await load_all_tickets()
        lines = []
        for ch_id, info in tickets.items():
            lines.append(f"- {info.get('ticket_id')} — Canal: <#{ch_id}> — Owner: <@{info.get('owner')}> — Motivo: {info.get('reason')}")
        
        text = "\n".join(lines) or "Nenhum ticket aberto."
        
        if len(text) > 1800:
             text = text[:1700] + "\n... (Lista muito longa. Verifique o JSON.)"
             
        try:
            await ctx.author.send(f"📋 **Tickets Abertos ({len(tickets)}):**\n{text}")
            await ctx.send("✅ Listei os tickets por DM.", delete_after=8)
        except discord.Forbidden:
            await ctx.send("❌ Não consegui enviar DM. Verifique se o seu DM está aberto.", delete_after=8)
        except Exception:
             await ctx.send("❌ Erro ao enviar a lista por DM.", delete_after=8)


    @commands.command(name="ticket-info")
    @commands.has_permissions(manage_messages=True)
    async def cmd_ticket_info(self, ctx, channel: discord.TextChannel = None):
        """Mostra informações detalhadas do ticket no canal atual ou especificado."""
        if channel is None:
            if ctx.channel.topic and "ticket_id:" in ctx.channel.topic:
                channel = ctx.channel
            else:
                await ctx.send("❌ Informe o canal do ticket, ex: `!ticket-info #ticket-user-TXXXX` (ou use o comando dentro do canal).", delete_after=10)
                return

        tickets = await load_all_tickets()
        info = tickets.get(str(channel.id))
        
        if not info:
            await ctx.send("❌ Canal informado não é um ticket registrado.", delete_after=8)
            return

        owner = info.get("owner")
        claimed = info.get("claimed_by")
        opened = info.get("opened_at")
        
        opened_dt = datetime.datetime.fromisoformat(opened) if opened else None
        diff = utcnow() - opened_dt if opened_dt else datetime.timedelta(0)
        hours = int(diff.total_seconds() // 3600)
        
        embed = discord.Embed(title=f"ℹ️ Info — {channel.name}", color=discord.Color.blurple())
        embed.add_field(name="ID", value=info.get("ticket_id", "—"), inline=True)
        embed.add_field(name="Aberto por", value=f"<@{owner}>", inline=True)
        embed.add_field(name="Fechado", value=("Sim" if info.get("closed") else "Não"), inline=True)
        embed.add_field(name="Motivo", value=info.get("reason", "—"), inline=False)
        embed.add_field(name="Descrição", value=info.get("description", "—")[:100] + "..." if len(info.get("description", "")) > 100 else info.get("description", "—"), inline=False)
        embed.add_field(name="Horas abertas", value=f"{hours}h", inline=True)
        embed.add_field(name="Atendido por", value=(f"<@{claimed}>" if claimed else "—"), inline=True)
        
        await ctx.send(embed=embed)

    # --- Listener de Interações (Apenas Abertura) ---
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Trata apenas a interação de abertura de ticket e o select de motivo."""
        if interaction.type != discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get("custom_id")
        
        # O fluxo é: PainelView (abrir_ticket_unico) -> MotivoView (motivo_select_id) -> Modal -> criar_ticket
        if custom_id in ("abrir_ticket_unico", "motivo_select_id"):
             pass # Deixa as classes View/Select/Modal lidarem com o callback
        else:
             # Ignora qualquer outra interação de botão (que deve ser substituída por comando)
             return

    # --- Tarefa de Verificação de Inatividade ---
    @tasks.loop(hours=1)
    async def check_inatividade(self):
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
                # Obtém a última mensagem
                last = None
                async for m in ch.history(limit=1, oldest_first=False):
                    last = m
                    break
                    
                last_time = last.created_at.replace(tzinfo=None) if last else ch.created_at.replace(tzinfo=None)
                
                # Verifica inatividade
                if last_time < limite:
                    await ch.send(f"⏰ Ticket fechado automaticamente por inatividade (última mensagem há mais de {EXPIRACAO_TICKET_HORAS} horas).")
                    await fechar_ticket_por_canal(ch, by_user=None)
                    
            except discord.NotFound:
                # Canal foi deletado manualmente, limpa o registro
                if str(ch.id) in tickets:
                    tickets.pop(str(ch.id))
                    await save_all_tickets(tickets)
            except Exception as e:
                print(f"[tickets] Erro ao checar inatividade no canal {ch.name}: {e}")
                continue

    @check_inatividade.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()
        
    def cog_unload(self):
        try:
            self.check_inatividade.cancel()
        except Exception:
            pass

# ---------------------------
# setup (Registro da Cog e da View Persistente)
# ---------------------------
async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
    # É fundamental registrar a View persistente para que o botão funcione após restarts.
    bot.add_view(PainelView(bot))