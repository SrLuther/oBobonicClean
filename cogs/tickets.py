# cogs/tickets.py
"""
Sistema completo de tickets (versão corrigida e estável)
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

# Transcript helper: write to temp file and return path
async def gerar_transcript_file(channel: discord.TextChannel):
    lines = []
    try:
        async for m in channel.history(limit=None, oldest_first=True):
            ts = m.created_at.isoformat()
            author = f"{m.author} ({m.author.id})"
            content = m.content or ""
            # include attachments simple info
            if m.attachments:
                atts = " | attachments: " + ", ".join(a.url for a in m.attachments)
                content = content + atts
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
# UI Components: Modal / Select / Views
# ---------------------------
class DescricaoModal(Modal):
    def __init__(self, reason: str):
        super().__init__(title="Descreva seu problema (opcional)")
        self.reason = reason
        self.descricao = TextInput(label="Descrição (máx 1000 caracteres)", style=discord.TextStyle.long, required=False, max_length=1000)
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
        super().__init__(placeholder="Escolha o motivo do seu ticket...", min_values=1, max_values=1, options=options, custom_id="motivo_select")

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

    # Botão A
    @discord.ui.button(label="🎫 Abrir Ticket", style=discord.ButtonStyle.green, custom_id="abrir_ticket_a")
    async def abrir_a(self, interaction: discord.Interaction, button: Button):
        await abrir_etapas(interaction)

    # Botão B (mesma ação, custom_id diferente — evita conflitos)
    @discord.ui.button(label="🎫 Abrir Ticket", style=discord.ButtonStyle.green, custom_id="abrir_ticket_b")
    async def abrir_b(self, interaction: discord.Interaction, button: Button):
        await abrir_etapas(interaction)

class TicketButtons(View):
    def __init__(self, channel_id: int, closed: bool = False):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        if closed:
            # reabrir
            self.add_item(Button(label="🔓 Reabrir Ticket", style=discord.ButtonStyle.green, custom_id=f"reabrir_{channel_id}"))
        else:
            # fechar, arquivar, transcript
            self.add_item(Button(label="🔒 Fechar", style=discord.ButtonStyle.red, custom_id=f"fechar_{channel_id}"))
            self.add_item(Button(label="📁 Arquivar", style=discord.ButtonStyle.grey, custom_id=f"arquivar_{channel_id}"))
            self.add_item(Button(label="📝 Transcript", style=discord.ButtonStyle.blurple, custom_id=f"transcript_{channel_id}"))

# ---------------------------
# Fluxo: abrir etapas / criar ticket
# ---------------------------
async def abrir_etapas(interaction: discord.Interaction):
    author = interaction.user
    tickets = await load_all_tickets()
    # anti-spam: verifica registro ativo
    for k, v in tickets.items():
        if v.get("owner") == author.id and not v.get("closed", False):
            await interaction.response.send_message("⚠️ Você já tem um ticket aberto. Feche-o antes de abrir outro.", ephemeral=True)
            return

    # checa canais existentes na categoria por topic
    guild = interaction.guild
    category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None
    if category:
        for ch in category.channels:
            if ch.topic and f"owner:{author.id}" in (ch.topic or "") and not ch.name.startswith("archived-"):
                await interaction.response.send_message("⚠️ Você já tem um ticket aberto (canal existente).", ephemeral=True)
                return

    await interaction.response.send_message("Escolha o motivo do ticket:", view=MotivoView(), ephemeral=True)

async def criar_ticket(interaction: discord.Interaction, reason: str, descricao: str = ""):
    guild = interaction.guild
    author = interaction.user
    tickets = await load_all_tickets()
    # defensivo: re-checar anti-spam
    for k, v in tickets.items():
        if v.get("owner") == author.id and not v.get("closed", False):
            await interaction.followup.send("⚠️ Você já tem um ticket aberto.", ephemeral=True)
            return

    category = guild.get_channel(TICKET_CATEGORY_ID)
    if not category:
        await interaction.followup.send("❌ Categoria de tickets não encontrada. Contate a moderação.", ephemeral=True)
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
        await interaction.followup.send(f"❌ Erro ao criar canal do ticket: {e}", ephemeral=True)
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
        description=(
            f"{author.mention}\n"
            f"**Motivo:** {reason}\n"
            f"**Descrição:** {descricao or '—'}\n\n"
            "Aguarde que um moderador irá atender em breve."
        ),
        color=discord.Color.green(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_footer(text=f"Abertura: {now}")

    await channel.send(content=f"{author.mention}", embed=embed, view=TicketButtons(channel.id, closed=False))
    try:
        await interaction.followup.send(f"✅ Seu ticket foi criado: {channel.mention}", ephemeral=True)
    except Exception:
        await interaction.response.send_message(f"✅ Seu ticket foi criado: {channel.mention}", ephemeral=True)

    # log
    log_c = guild.get_channel(CANAL_STATUS_ID)
    if log_c:
        await log_c.send(f"🟢 Ticket criado: {channel.name} (ID {ticket_id}) por {author.mention}")

# ---------------------------
# Actions: fechar, arquivar, transcript, reabrir
# ---------------------------
async def fechar_ticket_por_canal(channel: discord.TextChannel, by_user: discord.Member = None):
    tickets = await load_all_tickets()
    info = tickets.get(str(channel.id))
    if not info:
        return False, "Ticket não registrado."
    info["closed"] = True
    info["closed_at"] = utcnow().isoformat()
    tickets[str(channel.id)] = info
    await save_all_tickets(tickets)

    try:
        await channel.send("🔒 Ticket fechado. Você pode gerar transcript ou reabrir.", view=TicketButtons(channel.id, closed=True))
    except Exception:
        pass
    log = channel.guild.get_channel(CANAL_STATUS_ID)
    if log:
        who = by_user.mention if by_user else "Sistema"
        await log.send(f"🔒 Ticket {channel.name} fechado por {who}")
    return True, None

async def arquivar_ticket_por_canal(channel: discord.TextChannel, by_user: discord.Member = None):
    tickets = await load_all_tickets()
    info = tickets.get(str(channel.id))
    if not info:
        return False, "Ticket não registrado."

    path = await gerar_transcript_file(channel)
    arquivo = channel.guild.get_channel(CANAL_ARQUIVO_ID) if CANAL_ARQUIVO_ID else None
    if not arquivo:
        return False, "Canal de arquivamento não configurado."

    embed = discord.Embed(title="📁 Ticket Arquivado", description=f"Ticket: {channel.name}\nAberto por: <@{info.get('owner')}>", color=discord.Color.greyple(), timestamp=datetime.datetime.utcnow())
    if by_user:
        embed.add_field(name="Arquivado por", value=by_user.mention, inline=False)
    embed.add_field(name="ID", value=info.get("ticket_id", "—"), inline=True)

    try:
        await arquivo.send(embed=embed)
        await arquivo.send(file=discord.File(path))
    except Exception:
        try:
            await arquivo.send(embed=embed)
        except Exception:
            pass

    # remove registro e deleta canal
    tickets.pop(str(channel.id), None)
    await save_all_tickets(tickets)
    try:
        await channel.delete()
    except Exception:
        pass

    log = channel.guild.get_channel(CANAL_STATUS_ID)
    if log:
        who = by_user.mention if by_user else "Sistema"
        await log.send(f"📁 Ticket {channel.name} arquivado por {who}")
    return True, None

async def gerar_transcript_e_enviar(channel: discord.TextChannel, actor: discord.Member = None):
    path = await gerar_transcript_file(channel)
    try:
        await channel.send("📝 Transcript gerado:", file=discord.File(path))
    except Exception:
        log = channel.guild.get_channel(CANAL_STATUS_ID)
        if log:
            try:
                await log.send("📝 Transcript gerado:", file=discord.File(path))
            except Exception:
                pass

async def reabrir_por_canal(channel: discord.TextChannel, by_user: discord.Member = None):
    tickets = await load_all_tickets()
    info = tickets.get(str(channel.id))
    if not info:
        return False, "Ticket não registrado."
    info["closed"] = False
    info.pop("closed_at", None)
    tickets[str(channel.id)] = info
    await save_all_tickets(tickets)
    try:
        await channel.send("🔓 Ticket reaberto.", view=TicketButtons(channel.id, closed=False))
    except Exception:
        pass
    log = channel.guild.get_channel(CANAL_STATUS_ID)
    if log:
        who = by_user.mention if by_user else "Sistema"
        await log.send(f"🔓 Ticket {channel.name} reaberto por {who}")
    return True, None

# ---------------------------
# COG
# ---------------------------
class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_inatividade.start()

    @commands.command(name="ticket")
    @commands.has_permissions(manage_messages=True)
    async def cmd_ticket_panel(self, ctx):
        # força enviar no canal pedido (se configurado), senão usa CANAL_PAINEL_ID
        TARGET_PANEL_ID = CANAL_PAINEL_ID or 1440909767974453328
        canal = ctx.guild.get_channel(TARGET_PANEL_ID)
        if not canal:
            await ctx.send("❌ Canal de painel não encontrado. Verifique o config.", delete_after=8)
            return
        embed = discord.Embed(title="🎫 Sistema de Tickets", description="Clique para abrir um ticket com a equipe.", color=discord.Color.blue())
        msg = await canal.send(embed=embed, view=PainelView())
        try:
            await msg.pin()
        except Exception:
            pass
        await ctx.send("✅ Painel enviado.", delete_after=7)

    @commands.command(name="ticket-admin")
    @commands.has_permissions(manage_messages=True)
    async def cmd_ticket_admin(self, ctx):
        tickets = await load_all_tickets()
        lines = []
        for ch_id, info in tickets.items():
            lines.append(f"- {info.get('ticket_id')} — canal:{ch_id} — owner:{info.get('owner')} — reason:{info.get('reason')}")
        text = "\n".join(lines) or "Nenhum ticket aberto."
        try:
            await ctx.author.send(f"📋 Tickets abertos:\n{text}")
            await ctx.send("✅ Listei os tickets por DM.", delete_after=8)
        except Exception:
            await ctx.send("❌ Não consegui enviar DM. Verifique se o seu DM está aberto.", delete_after=8)

    @commands.command(name="ticket-info")
    @commands.has_permissions(manage_messages=True)
    async def cmd_ticket_info(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            await ctx.send("❌ Informe o canal do ticket, ex: `!ticket-info #ticket-user-TXXXX`", delete_after=8)
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
        diff = datetime.datetime.utcnow() - opened_dt if opened_dt else None
        hours = int(diff.total_seconds() // 3600) if diff else 0
        embed = discord.Embed(title=f"ℹ️ Info — {channel.name}", color=discord.Color.blurple())
        embed.add_field(name="ID", value=info.get("ticket_id", "—"), inline=True)
        embed.add_field(name="Aberto por", value=f"<@{owner}>", inline=True)
        embed.add_field(name="Atendido por", value=(f"<@{claimed}>" if claimed else "—"), inline=True)
        embed.add_field(name="Horas abertas", value=str(hours), inline=True)
        embed.add_field(name="Motivo", value=info.get("reason", "—"), inline=True)
        embed.add_field(name="Fechado", value=str(info.get("closed", False)), inline=True)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        # only handle component interactions
        if interaction.type != discord.InteractionType.component:
            return
        data = interaction.data or {}
        custom_id = data.get("custom_id") or data.get("custom_id")  # safe access
        if not custom_id:
            return

        # expected pattern: action_channelid  (e.g. fechar_123456)
        parts = custom_id.split("_", 1)
        if len(parts) != 2:
            return
        action, rest = parts[0], parts[1]

        try:
            channel_id = int(rest)
        except Exception:
            return

        guild = interaction.guild
        channel = guild.get_channel(channel_id)
        actor = interaction.user

        tickets = await load_all_tickets()
        info = tickets.get(str(channel_id))
        owner = info.get("owner") if info else None

        def _is_staff(m):
            return is_staff_member(m)

        if action == "fechar":
            if not (actor.id == owner or _is_staff(actor)):
                await interaction.response.send_message("❌ Apenas o autor ou um moderador pode fechar este ticket.", ephemeral=True)
                return
            ok, err = await fechar_ticket_por_canal(channel, by_user=actor)
            if ok:
                await interaction.response.send_message("🔒 Ticket fechado.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {err}", ephemeral=True)
            return

        if action == "arquivar":
            if not _is_staff(actor):
                await interaction.response.send_message("❌ Apenas moderadores podem arquivar tickets.", ephemeral=True)
                return
            ok, err = await arquivar_ticket_por_canal(channel, by_user=actor)
            if ok:
                await interaction.response.send_message("📁 Ticket arquivado.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {err}", ephemeral=True)
            return

        if action == "transcript":
            if not (_is_staff(actor) or actor.id == owner):
                await interaction.response.send_message("❌ Apenas staff ou autor podem gerar transcript.", ephemeral=True)
                return
            path = await gerar_transcript_file(channel)
            try:
                await interaction.response.send_message("📝 Transcript gerado:", file=discord.File(path), ephemeral=True)
            except Exception:
                await interaction.response.send_message("❌ Erro ao enviar transcript.", ephemeral=True)
            return

        if action == "reabrir":
            if not (_is_staff(actor) or actor.id == owner):
                await interaction.response.send_message("❌ Apenas owner ou staff pode reabrir.", ephemeral=True)
                return
            ok, err = await reabrir_por_canal(channel, by_user=actor)
            if ok:
                await interaction.response.send_message("🔓 Ticket reaberto.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {err}", ephemeral=True)
            return

    @tasks.loop(hours=1)
    async def check_inatividade(self):
        if not self.bot.guilds:
            return
        guild = self.bot.guilds[0]
        category = guild.get_channel(TICKET_CATEGORY_ID)
        log = guild.get_channel(CANAL_STATUS_ID)
        if not category:
            return
        limite = datetime.datetime.utcnow() - datetime.timedelta(hours=EXPIRACAO_TICKET_HORAS)
        tickets = await load_all_tickets()
        for ch in list(category.channels):
            info = tickets.get(str(ch.id))
            if not info or info.get("closed"):
                continue
            try:
                last = None
                async for m in ch.history(limit=1, oldest_first=False):
                    last = m
                    break
                last_time = last.created_at if last else ch.created_at
                if last_time < limite:
                    await ch.send("⏰ Ticket fechado automaticamente por inatividade.")
                    await fechar_ticket_por_canal(ch, by_user=None)
                    if log:
                        await log.send(f"⏰ Ticket {ch.name} fechado por inatividade.")
            except Exception:
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
# setup
# ---------------------------
async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
    # register persistent view so buttons keep working after restart
    bot.add_view(PainelView())
