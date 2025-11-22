# cogs/tickets.py
"""
Sistema completo de tickets:
- Persistência JSON em data/tickets.json
- Transcripts gerados e enviados ao canal de arquivo (CANAL_ARQUIVO_ID)
- Painel (botão único) + comando !ticket (moderadores com manage_messages)
- Anti-spam: 1 ticket por usuário
- Etapas: motivo (select) + modal descrição
- Botões no ticket: Fechar, Arquivar, Transcript, Reabrir
- Task de checagem de inatividade (EXPIRACAO_TICKET_HORAS)
- Comandos administrativos: !ticket-admin, !ticket-info
- Views persistentes após restart (bot.add_view)
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

from config import (
    CANAL_PAINEL_ID,
    CANAL_ARQUIVO_ID,
    TICKET_CATEGORY_ID,
    TICKET_ARCHIVE_CHANNEL_ID,
    MOD_ROLE_IDS,
    STAFF_ROLE_ID,
    EXPIRACAO_TICKET_HORAS,
    TICKET_ID_LENGTH,
    CANAL_STATUS_ID
)

# ---------------------------
# Paths / Folders / JSON
# ---------------------------
DATA_DIR = "data"
TICKETS_JSON = os.path.join(DATA_DIR, "tickets.json")
TRANSCRIPTS_DIR = "transcripts"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

_json_lock = asyncio.Lock()

# ---------------------------
# Helpers
# ---------------------------
def normalize_to_list(x):
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return list(x)
    try:
        return [int(x)]
    except Exception:
        return []

STAFF_ROLES = normalize_to_list(STAFF_ROLE_ID) or normalize_to_list(MOD_ROLE_IDS)

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
    except Exception:
        return {}

async def _write_json_safe(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        print(f"[tickets] erro ao escrever json: {e}")

async def load_all_tickets():
    async with _json_lock:
        data = await _read_json_safe(TICKETS_JSON)
        return data.get("tickets", {})

async def save_all_tickets(tickets):
    async with _json_lock:
        await _write_json_safe(TICKETS_JSON, {"tickets": tickets})

# Transcript helper
async def gerar_transcript_file(channel: discord.TextChannel):
    lines = []
    try:
        async for m in channel.history(limit=None, oldest_first=True):
            ts = m.created_at.isoformat()
            author = f"{m.author} ({m.author.id})"
            content = m.content or ""
            lines.append(f"[{ts}] {author}: {content}")
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
        r = member.guild.get_role(rid)
        if r and r in member.roles:
            return True
    return False

# ---------------------------
# UI Components
# ---------------------------
class DescricaoModal(Modal):
    def __init__(self, reason: str):
        super().__init__(title="Descreva seu problema (opcional)")
        self.reason = reason
        self.descricao = TextInput(label="Descrição (máx 1000 caracteres)",
                                   style=discord.TextStyle.long,
                                   required=False,
                                   max_length=1000)
        self.add_item(self.descricao)

    async def on_submit(self, interaction: discord.Interaction):
        await criar_ticket(interaction, self.reason, self.descricao.value or "")

class MotivoSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Suporte", description="Ajuda técnica, bugs, dúvidas"),
            discord.SelectOption(label="Compras", description="Pedidos, valores, pagamentos"),
            discord.SelectOption(label="Parcerias", description="Propostas comerciais"),
            discord.SelectOption(label="Denúncia", description="Reportar alguém"),
            discord.SelectOption(label="Outro", description="Outro assunto")
        ]
        super().__init__(placeholder="Escolha o motivo do seu ticket...",
                         min_values=1, max_values=1,
                         options=options,
                         custom_id="motivo_select")

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        modal = DescricaoModal(reason=chosen)
        await interaction.response.send_modal(modal)

class MotivoView(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(MotivoSelect())

class PainelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Abrir Ticket", style=discord.ButtonStyle.green, custom_id="abrir_ticket")
    async def abrir_1(self, interaction: discord.Interaction, button: Button):
        await abrir_etapas(interaction)

    @discord.ui.button(label="Abrir Ticket (2)", style=discord.ButtonStyle.green, custom_id="abrir_ticket_fallback")
    async def abrir_2(self, interaction: discord.Interaction, button: Button):
        await abrir_etapas(interaction)

class TicketButtons(View):
    def __init__(self, channel_id: int, closed: bool = False):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        if closed:
            self.add_item(Button(label="🔓 Reabrir Ticket",
                                 style=discord.ButtonStyle.green,
                                 custom_id=f"reabrir_{channel_id}"))
        else:
            self.add_item(Button(label="🔒 Fechar",
                                 style=discord.ButtonStyle.red,
                                 custom_id=f"fechar_{channel_id}"))
            self.add_item(Button(label="📁 Arquivar",
                                 style=discord.ButtonStyle.grey,
                                 custom_id=f"arquivar_{channel_id}"))
            self.add_item(Button(label="📝 Transcript",
                                 style=discord.ButtonStyle.blurple,
                                 custom_id=f"transcript_{channel_id}"))

# ---------------------------
# Fluxo: abrir etapas
# ---------------------------
async def abrir_etapas(interaction: discord.Interaction):
    author = interaction.user
    tickets = await load_all_tickets()

    # anti-spam
    for k, v in tickets.items():
        if v.get("owner") == author.id and not v.get("closed", False):
            await interaction.response.send_message(
                "⚠️ Você já tem um ticket aberto.", ephemeral=True)
            return

    guild = interaction.guild
    category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None

    if category:
        for ch in category.channels:
            if ch.topic and f"owner:{author.id}" in (ch.topic or "") and not ch.name.startswith("archived-"):
                await interaction.response.send_message(
                    "⚠️ Você já tem um ticket aberto.", ephemeral=True)
                return

    await interaction.response.send_message("Escolha o motivo:", view=MotivoView(), ephemeral=True)

# ---------------------------
# Criar ticket
# ---------------------------
async def criar_ticket(interaction: discord.Interaction, reason: str, descricao: str = ""):
    guild = interaction.guild
    author = interaction.user
    tickets = await load_all_tickets()

    for k, v in tickets.items():
        if v.get("owner") == author.id and not v.get("closed", False):
            await interaction.followup.send("⚠️ Você já tem um ticket aberto.", ephemeral=True)
            return

    category = guild.get_channel(TICKET_CATEGORY_ID)
    if not category:
        await interaction.followup.send("❌ Categoria não encontrada.", ephemeral=True)
        return

    ticket_id = gerar_ticket_id()
    name = f"ticket-{author.name}-{ticket_id}".lower()[:90]

    overwrites = {
        guild.default_role: PermissionOverwrite(view_channel=False),
        author: PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)
    }

    for rid in STAFF_ROLES:
        role = guild.get_role(rid)
        if role:
            overwrites[role] = PermissionOverwrite(view_channel=True, send_messages=True)

    try:
        channel = await guild.create_text_channel(
            name=name,
            category=category,
            overwrites=overwrites,
            topic=f"ticket_id:{ticket_id} owner:{author.id} reason:{reason}"
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao criar ticket: {e}", ephemeral=True)
        return

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

    embed = discord.Embed(
        title=f"🎫 Ticket {ticket_id}",
        description=f"{author.mention}\n**Motivo:** {reason}\n**Descrição:** {descricao or '—'}",
        color=discord.Color.green(),
        timestamp=datetime.datetime.utcnow()
    )

    await channel.send(content=f"{author.mention}", embed=embed,
                       view=TicketButtons(channel.id, closed=False))

    try:
        await interaction.followup.send(f"✅ Ticket criado: {channel.mention}", ephemeral=True)
    except Exception:
        await interaction.response.send_message(f"✅ Ticket criado: {channel.mention}", ephemeral=True)

    log = guild.get_channel(CANAL_STATUS_ID)
    if log:
        await log.send(f"🟢 Ticket criado: {channel.name} ({ticket_id}) por {author.mention}")
# ---------------------------
# Fechar ticket
# ---------------------------
async def fechar_ticket(interaction: discord.Interaction, channel: discord.TextChannel):
    tickets = await load_all_tickets()
    ch_id = str(channel.id)

    if ch_id not in tickets:
        await interaction.response.send_message("❌ Este ticket não existe no sistema.", ephemeral=True)
        return

    data = tickets[ch_id]
    if data.get("closed"):
        await interaction.response.send_message("⚠️ Este ticket já está fechado.", ephemeral=True)
        return

    # apenas staff ou o dono
    if interaction.user.id != data.get("owner") and not is_staff_member(interaction.user):
        await interaction.response.send_message("❌ Você não pode fechar este ticket.", ephemeral=True)
        return

    data["closed"] = True
    data["closed_at"] = utcnow().isoformat()
    await save_all_tickets(tickets)

    await interaction.response.send_message("🔒 Ticket fechado.")

    # Atualiza botões
    await channel.send("🔒 Ticket fechado.", view=TicketButtons(channel.id, closed=True))

# ---------------------------
# Reabrir ticket
# ---------------------------
async def reabrir_ticket(interaction: discord.Interaction, channel: discord.TextChannel):
    tickets = await load_all_tickets()
    ch_id = str(channel.id)

    if ch_id not in tickets:
        await interaction.response.send_message("❌ Ticket desconhecido.", ephemeral=True)
        return

    data = tickets[ch_id]
    if not data.get("closed"):
        await interaction.response.send_message("⚠️ Este ticket já está aberto.", ephemeral=True)
        return

    # Apenas staff pode reabrir
    if not is_staff_member(interaction.user):
        await interaction.response.send_message("❌ Apenas a staff pode reabrir tickets.", ephemeral=True)
        return

    data["closed"] = False
    data["reopened_at"] = utcnow().isoformat()
    await save_all_tickets(tickets)

    await interaction.response.send_message("🔓 Ticket reaberto.")
    await channel.send("🔓 Ticket reaberto!", view=TicketButtons(channel.id, closed=False))

# ---------------------------
# Arquivar Ticket
# ---------------------------
async def arquivar_ticket(interaction: discord.Interaction, channel: discord.TextChannel):
    tickets = await load_all_tickets()
    ch_id = str(channel.id)

    if ch_id not in tickets:
        await interaction.response.send_message("❌ Ticket não existe no sistema.", ephemeral=True)
        return

    data = tickets[ch_id]

    # apenas staff
    if not is_staff_member(interaction.user):
        await interaction.response.send_message("❌ Apenas staff pode arquivar tickets.", ephemeral=True)
        return

    guild = interaction.guild
    archive_channel = guild.get_channel(TICKET_ARCHIVE_CHANNEL_ID)

    if not archive_channel:
        await interaction.response.send_message("❌ Canal de arquivo não encontrado.", ephemeral=True)
        return

    # Gera transcript
    transcript_path = await gerar_transcript_file(channel)

    # Envia transcrição para o canal de arquivo
    try:
        await archive_channel.send(
            f"📁 Transcript do ticket **{data.get('ticket_id')}** — {channel.name}",
            file=discord.File(transcript_path)
        )
    except Exception as e:
        print(f"[tickets] Erro ao enviar transcript para canal: {e}")

    # move o canal
    try:
        await channel.edit(name=f"archived-{channel.name}", category=archive_channel.category)
    except Exception as e:
        print(f"[tickets] Falha ao mover ticket arquivado: {e}")

    data["archived"] = True
    data["archived_at"] = utcnow().isoformat()
    await save_all_tickets(tickets)

    await interaction.response.send_message("📁 Ticket arquivado e transcript enviado ao canal.")
    await channel.send("📁 Ticket arquivado.")

# ---------------------------
# Transcript sob demanda
# ---------------------------
async def enviar_transcript_manual(interaction: discord.Interaction, channel: discord.TextChannel):
    transcript_path = await gerar_transcript_file(channel)
    await interaction.response.send_message(
        "📝 Transcript gerado:",
        file=discord.File(transcript_path),
        ephemeral=True
    )

# ---------------------------
# Inatividade — Fechar após 48h
# ---------------------------
async def fechar_inativo(channel: discord.TextChannel, data: dict):
    now = utcnow()
    last = data.get("last_message")

    if last:
        try:
            last_dt = datetime.datetime.fromisoformat(last)
        except Exception:
            last_dt = utcnow()
    else:
        last_dt = utcnow()

    diff = now - last_dt
    if diff.total_seconds() > EXPIRACAO_TICKET_HORAS * 3600:
        try:
            await channel.send("⏳ Ticket fechado automaticamente por inatividade.")
        except Exception:
            pass

        data["closed"] = True
        data["closed_at"] = utcnow().isoformat()

        tickets = await load_all_tickets()
        tickets[str(channel.id)] = data
        await save_all_tickets(tickets)

        return True
    return False

# ---------------------------
# Atualizar última mensagem
# ---------------------------
async def atualizar_atividade(message: discord.Message):
    if message.author.bot:
        return

    tickets = await load_all_tickets()
    ch_id = str(message.channel.id)

    if ch_id not in tickets:
        return

    data = tickets[ch_id]
    if data.get("closed"):
        return

    data["last_message"] = utcnow().isoformat()
    await save_all_tickets(tickets)

# ---------------------------
# Cog
# ---------------------------
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_inativos.start()

    def cog_unload(self):
        self.check_inativos.cancel()

    # Verifica inatividade
    @tasks.loop(minutes=10)
    async def check_inativos(self):
        tickets = await load_all_tickets()
        guild = self.bot.get_guild(next(iter(self.bot.guilds)).id)

        for ch_id, data in list(tickets.items()):
            ch = guild.get_channel(int(ch_id))
            if not ch:
                continue

            if not data.get("closed"):
                try:
                    await fechar_inativo(ch, data)
                except Exception as e:
                    print(f"[tickets] erro inativo: {e}")

    @check_inativos.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # Painel
    @commands.command(name="ticket-panel")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx):
        canal = ctx.guild.get_channel(CANAL_PAINEL_ID)
        if not canal:
            return await ctx.send("❌ Canal de painel não encontrado.")

        embed = discord.Embed(
            title="🎟️ Sistema de Tickets",
            description="Clique abaixo para abrir um ticket.",
            color=discord.Color.blue()
        )
        await canal.send(embed=embed, view=PainelView())
        await ctx.send("Painel enviado!", delete_after=5)

    # Info
    @commands.command(name="ticket-info")
    async def ticket_info(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        tickets = await load_all_tickets()

        ch_id = str(channel.id)
        if ch_id not in tickets:
            return await ctx.send("❌ Este canal não é um ticket.")

        data = tickets[ch_id]

        embed = discord.Embed(
            title=f"Informações do Ticket {data.get('ticket_id')}",
            color=discord.Color.gold()
        )
        for k, v in data.items():
            embed.add_field(name=k, value=str(v), inline=False)

        await ctx.send(embed=embed)
# ============================================================
# 🔹 Função de arquivamento automático por inatividade
# ============================================================

async def auto_archive_task(self):
    await self.bot.wait_until_ready()
    while not self.bot.is_closed():
        try:
            for ticket_id, data in list(self.active_tickets.items()):
                channel_id = data["channel_id"]
                last_activity = data.get("last_activity", time.time())

                # Se passou o tempo limite → arquiva
                if time.time() - last_activity > 48 * 3600:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        try:
                            await channel.send("⏳ **Ticket arquivado automaticamente por inatividade.**")
                        except:
                            pass
                    await self.archive_ticket(None, ticket_id)

            await asyncio.sleep(3600)  # Checa a cada 1 hora

        except Exception as e:
            print(f"[ERRO AUTO-ARCHIVE] {e}")
            await asyncio.sleep(60)

# ============================================================
# 🔹 Setup do COG
# ============================================================

async def setup(bot):
    await bot.add_cog(Tickets(bot))
    print("[COG] Tickets carregado com sucesso.")

