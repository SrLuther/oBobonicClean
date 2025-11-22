# cogs/tickets.py
"""
Sistema de tickets (Versão Final e Estruturada)

Objetivo:
1. Eliminar o SyntaxError persistente removendo todas as f-strings ambíguas nos pontos críticos.
2. Estruturar o código em seções lógicas para fácil manutenção.
3. Manter todas as funcionalidades de abertura, fechamento, arquivamento e comandos.
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
from typing import Optional

# ==============================================================================
# 🧩 SEÇÃO 1: CONFIGURAÇÃO E CONSTANTES
# (Valores importados ou padrões de fallback)
# ==============================================================================
try:
    from config import (
        CANAL_PAINEL_ID, CANAL_ARQUIVO_ID, TICKET_CATEGORY_ID,
        MOD_ROLE_IDS, STAFF_ROLE_ID, EXPIRACAO_TICKET_HORAS,
        TICKET_ID_LENGTH, CANAL_STATUS_ID
    )
except ImportError:
    # 🚨 Valores Padrão de Falha (Altere-os no seu config.py!)
    CANAL_PAINEL_ID = 0
    CANAL_ARQUIVO_ID = 0
    TICKET_CATEGORY_ID = 0
    MOD_ROLE_IDS = []
    STAFF_ROLE_ID = []
    EXPIRACAO_TICKET_HORAS = 24
    TICKET_ID_LENGTH = 5
    CANAL_STATUS_ID = 0

# Paths de Arquivo
DATA_DIR = "data"
TICKETS_JSON = os.path.join(DATA_DIR, "tickets.json")
TRANSCRIPTS_DIR = "transcripts"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

# ==============================================================================
# 🛠️ SEÇÃO 2: HELPERS E UTILIDADES
# (Funções de Arquivo, Tempo e Checagem de Permissão)
# ==============================================================================

_json_lock = asyncio.Lock()

def normalize_to_list_int(x):
    """Converte valores de configuração para uma lista de IDs inteiros."""
    if isinstance(x, (int, str)) and str(x).isdigit():
        return [int(x)]
    if isinstance(x, (list, tuple)):
        return [int(item) for item in x if str(item).isdigit()]
    return []

# Compila IDs de cargos de Staff (sem duplicatas)
STAFF_ROLES = list(set(normalize_to_list_int(STAFF_ROLE_ID) + normalize_to_list_int(MOD_ROLE_IDS)))

def gerar_ticket_id():
    """Gera um ID de ticket único."""
    length = TICKET_ID_LENGTH if isinstance(TICKET_ID_LENGTH, int) and TICKET_ID_LENGTH > 0 else 5
    return "T-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

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
    """Carrega todos os dados de tickets."""
    async with _json_lock:
        data = await _read_json_safe(TICKETS_JSON)
        return data.get("tickets", {})

async def save_all_tickets(tickets):
    """Salva todos os dados de tickets."""
    async with _json_lock:
        await _write_json_safe(TICKETS_JSON, {"tickets": tickets})

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
            # f-string segura (sem \ na expressão)
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
# 🖥️ SEÇÃO 3: UI COMPONENTS (VIEWS, MODALS E FLUXO DE ABERTURA)
# ==============================================================================

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
        # Chama a função principal de criação de ticket
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
        super().__init__(timeout=None) 
        self.bot = bot

    @discord.ui.button(label="🎫 ABRIR TICKET", style=discord.ButtonStyle.green, custom_id="abrir_ticket_unico")
    async def abrir_ticket(self, interaction: discord.Interaction, button: Button):
        await abrir_etapas(interaction) 

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
            if ch.topic and "owner:{}".format(author.id) in (ch.topic or "") and not ch.name.startswith("archived-"):
                await interaction.response.send_message("⚠️ Você já tem um ticket aberto no canal {}. Por favor, use este canal para continuar.".format(ch.mention), ephemeral=True)
                return

    # 3. Mostra o Select de Motivo
    await interaction.response.send_message("Escolha o motivo do ticket:", view=MotivoView(), ephemeral=True)

async def criar_ticket(interaction: discord.Interaction, reason: str, descricao: str = ""):
    """
    Cria o canal de ticket e registra no JSON. 
    CORREÇÃO DE SINTAXE: Usa .format() e sanitização rigorosa de strings.
    """
    guild = interaction.guild
    author = interaction.user
    tickets = await load_all_tickets()

    # Checagem de corrida
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
    name = "ticket-{}-{}-{}".format(clean_name[:15], ticket_id, ticket_id).lower()[:90] 

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
        # PONTO CRÍTICO: Sanitização da string para o tópico do canal
        # Remove backslashes, novas linhas e aspas que causam o SyntaxError
        safe_reason = reason.replace('\n', ' ').replace('\\', '').replace('"', '').replace("'", '')
        
        # Uso de .format() para construção segura do tópico (evita SyntaxError)
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
        "ticket_id": ticket_id,
        "reason": reason,
        "description": descricao,
        "closed": False
    }
    await save_all_tickets(tickets)

    # Mensagem de Boas-vindas
    embed = discord.Embed(
        title="🎫 Ticket {}: {}".format(ticket_id, reason), 
        description=(
            "**Usuário:** {}\n"
            "**Descrição:** {}\n\n"
            "Aguarde. Um membro da equipe irá atender em breve. "
        ).format(author.mention, descricao or '—'), 
        color=discord.Color.green(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_footer(text="ID do Ticket: {} | Abertura: {}".format(ticket_id, now)) 

    await channel.send(content="{}".format(author.mention), embed=embed)
    
    await interaction.followup.send("✅ Seu ticket foi criado: {}".format(channel.mention), ephemeral=True)

    # Log de status
    log_c = guild.get_channel(CANAL_STATUS_ID)
    if log_c and isinstance(log_c, discord.TextChannel):
        await log_c.send("🟢 Ticket criado: {} (ID {}) por {}".format(channel.name, ticket_id, author.mention))


# ==============================================================================
# 🚀 SEÇÃO 4: LÓGICA DE GERENCIAMENTO (AÇÕES)
# (fechar, arquivar, reabrir)
# ==============================================================================

async def fechar_ticket_por_canal(channel: discord.TextChannel, by_user: discord.Member = None):
    """Fecha o ticket removendo a permissão de envio de mensagens do owner."""
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
    """Arquiva (deleta) o ticket, gerando transcript."""
    tickets = await load_all_tickets()
    channel_id_str = str(channel.id)
    info = tickets.pop(channel_id_str, None)

    if not info:
        try:
             await channel.delete(reason="Arquivado por {} (Registro não encontrado).".format(by_user.name if by_user else 'Sistema'))
        except:
             pass
        return False, "Ticket não registrado. O canal foi deletado."

    path = await gerar_transcript_file(channel)
    arquivo = channel.guild.get_channel(CANAL_ARQUIVO_ID)
    
    # Envia o transcript para o canal de arquivos
    if arquivo and isinstance(arquivo, discord.TextChannel):
        owner_member = channel.guild.get_member(info.get('owner'))
        owner_mention = owner_member.mention if owner_member else "<@{}>".format(info.get('owner'))

        embed = discord.Embed(
            title="📁 Ticket Arquivado", 
            description="Ticket: **{}**\n**Aberto por:** {}".format(channel.name, owner_mention), 
            color=discord.Color.greyple(), 
            timestamp=utcnow()
        )
        if by_user:
            embed.add_field(name="Arquivado por", value=by_user.mention, inline=False)
        embed.add_field(name="ID", value=info.get("ticket_id", "—"), inline=True)
        embed.add_field(name="Motivo", value=info.get("reason", "—"), inline=True)
        
        try:
            await arquivo.send(embed=embed)
            await arquivo.send(file=discord.File(path, filename="{}-transcript.txt".format(channel.name)))
        except Exception:
            await channel.send("⚠️ Erro ao enviar transcript para o canal de arquivamento. Deletando canal.", delete_after=10)
    
    await save_all_tickets(tickets) 

    # Deleta o canal
    try:
        await channel.delete(reason="Arquivado por {}".format(by_user.name if by_user else 'Sistema'))
    except Exception:
        log = channel.guild.get_channel(CANAL_STATUS_ID)
        if log:
             await log.send("❌ ATENÇÃO: Bot falhou ao deletar o canal {} por falta de permissão. Registro removido do JSON.".format(channel.name))
        return False, "O bot não tem permissão para deletar o canal."
        
    log = channel.guild.get_channel(CANAL_STATUS_ID)
    if log and isinstance(log, discord.TextChannel):
        who = by_user.mention if by_user else "Sistema"
        await log.send("📁 Ticket {} arquivado por {}".format(channel.name, who))
    
    try:
        os.remove(path)
    except Exception:
        pass
        
    return True, None

async def reabrir_por_canal(channel: discord.TextChannel, by_user: discord.Member = None):
    """Reabre o ticket, restaurando a permissão de envio de mensagens do owner."""
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
        
        embed = discord.Embed(
            title="🎫 Sistema de Tickets de Suporte", 
            description="Use o botão abaixo para iniciar uma conversa **privada** com a nossa equipe de suporte.", 
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="1️⃣ Como Abrir um Ticket?",
            # String multi-linhas segura (sem f" no início)
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
            # String multi-linhas segura (sem f" no início)
            value=(
                "* **Abertura:** O canal é criado. Mencione novamente o problema.\n"
                "* **Atendimento:** Um membro da equipe irá se identificar e começar a te ajudar.\n"
                "* **Resolução:** Assim que o problema for resolvido, use **`!fechar`** (ou a equipe fechará) para finalizar a conversa."
            ),
            inline=False
        )
        
        embed.add_field(
            name="⏳ Fechamento Automático e Comandos",
            # Uso de f-string simples no final para incluir variável
            value=(
                f"* **Inatividade:** Se o ticket ficar inativo (sem mensagens) por **{EXPIRACAO} horas**, ele será fechado automaticamente.\n"
                "* **Reabertura:** Use o comando `!reabrir` dentro do canal para continuar após o fechamento.\n"
                "* **Transcrição:** Use `!transcript` para gerar o histórico da conversa."
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
            
        await ctx.send("📁 Arquivando ticket e gerando transcript... O canal será deletado em 5 segundos.")
        await asyncio.sleep(5)
        
        ok, err = await arquivar_ticket_por_canal(ctx.channel, by_user=ctx.author)
        if not ok:
            await ctx.channel.send("❌ Erro ao arquivar: {}".format(err))


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
            await ctx.channel.send("📝 Transcript gerado:", file=discord.File(path, filename="{}-transcript.txt".format(ctx.channel.name)))
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
        

    @commands.command(name="ticket-admin")
    @commands.has_permissions(manage_messages=True)
    async def cmd_ticket_admin(self, ctx):
        """Lista todos os tickets abertos por DM."""
        tickets = await load_all_tickets()
        lines = []
        for ch_id, info in tickets.items():
            lines.append("- {} — Canal: <#{}> — Owner: <@{}> — Motivo: {}".format(
                info.get('ticket_id'), ch_id, info.get('owner'), info.get('reason')))
        
        text = "\n".join(lines) or "Nenhum ticket aberto."
        
        if len(text) > 1800:
             text = text[:1700] + "\n... (Lista muito longa. Verifique o JSON.)"
             
        try:
            await ctx.author.send("📋 **Tickets Abertos ({})**: {}".format(len(tickets), text))
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
        
        embed = discord.Embed(title="ℹ️ Info — {}".format(channel.name), color=discord.Color.blurple())
        embed.add_field(name="ID", value=info.get("ticket_id", "—"), inline=True)
        embed.add_field(name="Aberto por", value="<@{}>".format(owner), inline=True)
        embed.add_field(name="Fechado", value=("Sim" if info.get("closed") else "Não"), inline=True)
        embed.add_field(name="Motivo", value=info.get("reason", "—"), inline=False)
        
        description_value = info.get("description", "—")
        if len(description_value) > 100:
            description_value = description_value[:100] + "..."
            
        embed.add_field(name="Descrição", value=description_value, inline=False)
        embed.add_field(name="Horas abertas", value="{}h".format(hours), inline=True)
        embed.add_field(name="Atendido por", value=(f"<@{claimed}>" if claimed else "—"), inline=True)
        
        await ctx.send(embed=embed)

    # --- Listener de Interações ---
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Trata interações de botões e selects."""
        if interaction.type != discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get("custom_id")
        
        if custom_id in ("abrir_ticket_unico", "motivo_select_id"):
             pass 
        else:
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
    await bot.add_cog(TicketsCog(bot))
    # Registra a View persistente para que o botão funcione após restarts.
    bot.add_view(PainelView(bot))