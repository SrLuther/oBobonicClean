# cogs/treasure_hunt.py
# The Legendary Treasure Hunt Sundays — Sistema completo
# Setup de categoria, cadastro, provas, desafios, ranking e logs.

import discord
from discord.ext import commands
from discord.ext import tasks
import json
import os

import uuid
import io
import aiohttp
from datetime import datetime, timezone, date
from typing import Optional, cast

# Importa XPSystem para tipagem
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from cogs.xp import XPSystem

BANCO_FILE = ".bancos/treasure_hunt.json"

# IDs dos canais lidos do .env — fallback caso o banco esteja zerado (ex: container sem volume)
_CHANNEL_IDS_FALLBACK = {
    "banco":    int(os.getenv("TH_CHANNEL_BANCO",    "0") or "0"),
    "cadastro": int(os.getenv("TH_CHANNEL_CADASTRO", "0") or "0"),
    "provas":   int(os.getenv("TH_CHANNEL_PROVAS",   "0") or "0"),
    "logs":     int(os.getenv("TH_CHANNEL_LOGS",     "0") or "0"),
}

MAPAS_ARK = [
    "The Island", "The Center", "Scorched Earth", "Ragnarok",
    "Aberration", "Extinction", "Valguero", "Genesis: Part 1",
    "Crystal Isles", "Genesis: Part 2", "Lost Island", "Fjordur",
]

REGULAMENTO_TEXTO = """
## 📜 Regulamento — The Legendary Treasure Hunt Sundays

**Sequência oficial de mapas ARK (ordem de lançamento):**
> 1. The Island — Junho de 2015
> 2. The Center — Maio de 2016
> 3. Scorched Earth — Setembro de 2016
> 4. Ragnarok — Junho de 2017
> 5. Aberration — Dezembro de 2017
> 6. Extinction — Novembro de 2018
> 7. Valguero — Junho de 2019
> 8. Genesis: Part 1 — Fevereiro de 2020
> 9. Crystal Isles — Junho de 2020
> 10. Genesis: Part 2 — Junho de 2021
> 11. Lost Island — Dezembro de 2021
> 12. Fjordur — Junho de 2022

**Como se cadastrar:**
1. Clique em **📝 Cadastrar** abaixo.
2. Preencha: **nome no jogo**, **link ou código Steam** e **suas tribos em cada mapa** (indicando qual é a tribo principal).
3. Seu cadastro fica salvo automaticamente e você já pode participar.

**Como enviar provas:**
1. Acesse o canal de provas.
2. Envie a **imagem da prova** diretamente no canal (sem texto).
3. O bot irá postar a imagem numerada — reaja com o número do desafio correspondente.
4. A administração irá aprovar ou rejeitar com justificativa.

**Pontuação:** cada desafio tem pontuação própria definida pela administração.
**Ranking:** atualizado sempre que a administração aprovar ou ajustar pontos.
"""

# ─────────────────────────────────────────────────────────────
# BANCO DE DADOS (JSON)
# ─────────────────────────────────────────────────────────────

def _banco_padrao() -> dict:
    return {
        "channels": {
            "banco": None,
            "cadastro": None,
            "ranking": None,
            "provas": None,
            "logs": None,
        },
        "challenges": {},
        "players": {},
        "provas": {},
        "pending_provas": {},
        "pending_conversoes": {},
        "ranking_message_id": None,
        "cadastro_message_id": None,
        "banco_message_id": None,
        "provas_message_id": None,
        "evento_atual": {
            "mapa": None,
            "semana": None,
            "data_inicio": None,
            "data_fim": None,
            "observacao": None,
        },
    }


def load_banco() -> dict:
    if not os.path.exists(BANCO_FILE):
        banco = _banco_padrao()
    else:
        try:
            with open(BANCO_FILE, "r", encoding="utf-8") as f:
                banco = json.load(f)
        except (json.JSONDecodeError, IOError):
            banco = _banco_padrao()

    # Garante que canais conhecidos nunca fiquem None
    channels = banco.setdefault("channels", {})
    preencheu = False
    for chave, cid in _CHANNEL_IDS_FALLBACK.items():
        if not channels.get(chave):
            channels[chave] = cid
            preencheu = True
    if preencheu:
        save_banco(banco)
        print("[TREASURE] ⚠️ Banco sem IDs de canais — fallback aplicado e salvo.")

    return banco


def save_banco(data: dict) -> None:
    os.makedirs(os.path.dirname(BANCO_FILE), exist_ok=True)
    with open(BANCO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# Emojis numerados usados como reações de seleção de criatura (máx 10)
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

# Mapa de message_id → uid: para lookup rápido em on_raw_reaction_add
_pending_reactions: dict = {}  # { bot_message_id: uid }
_pending_image_data: dict = {}  # { uid: (bytes, filename) }

# ─────────────────────────────────────────────────────────────
# HELPERS DE PERMISSÃO
# ─────────────────────────────────────────────────────────────

def is_admin(member: "discord.Member | discord.User") -> bool:
    if not isinstance(member, discord.Member):
        return False
    return member.guild_permissions.administrator


# ─────────────────────────────────────────────────────────────
# VIEWS — CADASTRO
# ─────────────────────────────────────────────────────────────

class CadastroView(discord.ui.View):
    def __init__(self, cog: "TreasureHuntCog"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="📝 Cadastrar",
        style=discord.ButtonStyle.primary,
        custom_id="th_cadastro_btn",
    )
    async def cadastrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        banco = load_banco()
        uid = str(interaction.user.id)
        dados = banco["players"].get(uid)
        if dados:
            embed = discord.Embed(
                title="📋 Você já está cadastrado",
                color=discord.Color.orange(),
            )
            embed.add_field(name="Nome no jogo", value=dados.get("nome_jogo", "*—*"), inline=False)
            embed.add_field(name="Steam", value=dados.get("steam", "*—*"), inline=False)
            embed.add_field(name="Tribos", value=f"```{dados.get('tribos_raw', '*—*')}```", inline=False)
            embed.set_footer(text="Deseja atualizar seus dados?")
            await interaction.response.send_message(
                embed=embed,
                view=_AtualizarCadastroView(self.cog),
                ephemeral=True,
            )
        else:
            await interaction.response.send_modal(CadastroModal(self.cog))


class _AtualizarCadastroView(discord.ui.View):
    def __init__(self, cog: "TreasureHuntCog"):
        super().__init__(timeout=60)
        self.cog = cog

    @discord.ui.button(label="✏️ Atualizar dados", style=discord.ButtonStyle.primary)
    async def atualizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CadastroModal(self.cog))

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Cadastro mantido sem alterações.", embed=None, view=None)


class CadastroModal(discord.ui.Modal, title="Cadastro — Treasure Hunt"):
    nome_jogo = discord.ui.TextInput(
        label="Nome no Jogo",
        placeholder="Seu nome exatamente como aparece no ARK",
        required=True,
        max_length=64,
    )
    steam = discord.ui.TextInput(
        label="Link ou Código Steam",
        placeholder="https://steamcommunity.com/id/... ou código de 17 dígitos",
        required=True,
        max_length=128,
    )
    tribos = discord.ui.TextInput(
        label="Suas Tribos por Mapa",
        placeholder=(
            "The Island: NomeDaTribo (principal)\n"
            "Ragnarok: OutraTribo\n"
            "(liste todos os mapas onde você joga)"
        ),
        style=discord.TextStyle.long,
        required=True,
        max_length=1000,
    )

    def __init__(self, cog: "TreasureHuntCog"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        banco = load_banco()
        uid = str(interaction.user.id)

        banco["players"][uid] = {
            "discord_tag": str(interaction.user),
            "nome_jogo": self.nome_jogo.value.strip(),
            "steam": self.steam.value.strip(),
            "tribos_raw": self.tribos.value.strip(),
            "pontos": banco["players"].get(uid, {}).get("pontos", 0),
            "cadastro_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        save_banco(banco)

        await self.cog._log(
            interaction.guild,
            f"📋 **Cadastro** — {interaction.user.mention} (`{interaction.user}`)\n"
            f"• Nome: `{self.nome_jogo.value.strip()}`\n"
            f"• Steam: `{self.steam.value.strip()}`\n"
            f"• Tribos:\n```\n{self.tribos.value.strip()}\n```",
        )

        await interaction.response.send_message(
            "✅ Cadastro salvo! Você já está participando do evento.", ephemeral=True
        )


# ─────────────────────────────────────────────────────────────
# VIEWS — APROVAÇÃO DE PROVAS (persistente após restart)
# ─────────────────────────────────────────────────────────────

class ProvaAprovacaoView(discord.ui.View):
    """View persistente — custom_ids fixos, prova_id lido do footer do embed."""
    def __init__(self, cog: "TreasureHuntCog"):
        super().__init__(timeout=None)
        self.cog = cog

    def _prova_id(self, interaction: discord.Interaction) -> Optional[str]:
        if not interaction.message or not interaction.message.embeds:
            return None
        footer = interaction.message.embeds[0].footer
        if footer and footer.text and "ID da prova: " in footer.text:
            return footer.text.split("ID da prova: ", 1)[1].strip()
        return None

    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.green, custom_id="th_aprovar_universal")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return
        prova_id = self._prova_id(interaction)
        if not prova_id:
            await interaction.response.send_message("❌ Não foi possível identificar a prova.", ephemeral=True)
            return
        await self.cog.processar_aprovacao(interaction, prova_id, aprovado=True)

    @discord.ui.button(label="❌ Rejeitar", style=discord.ButtonStyle.red, custom_id="th_rejeitar_universal")
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return
        prova_id = self._prova_id(interaction)
        if not prova_id:
            await interaction.response.send_message("❌ Não foi possível identificar a prova.", ephemeral=True)
            return
        await interaction.response.send_modal(RejeitarModal(self.cog, prova_id))


# ─────────────────────────────────────────────────────────────
# MODAL — REJEIÇÃO COM MOTIVO
# ─────────────────────────────────────────────────────────────

class RejeitarModal(discord.ui.Modal, title="Rejeitar Prova"):
    motivo = discord.ui.TextInput(
        label="Motivo da rejeição",
        placeholder="Ex: Imagem ilegível, nível incorreto, etc.",
        style=discord.TextStyle.long,
        required=True,
        max_length=500,
    )

    def __init__(self, cog: "TreasureHuntCog", prova_id: str):
        super().__init__()
        self.cog = cog
        self.prova_id = prova_id

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.processar_aprovacao(
            interaction, self.prova_id, aprovado=False, motivo=self.motivo.value.strip()
        )


# ─────────────────────────────────────────────────────────────
# VIEW — BOTÃO DE CONVERSÃO (canal ranking)
# ─────────────────────────────────────────────────────────────

class ConversaoPontosView(discord.ui.View):
    """View persistente no canal ranking — abre solicitação de conversão."""
    def __init__(self, cog: "TreasureHuntCog"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="🔄 Converter Pontos para a Loja",
        style=discord.ButtonStyle.blurple,
        custom_id="th_converter_pontos",
    )
    async def converter(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        banco = load_banco()

        player = banco.get("players", {}).get(uid)
        if not player:
            await interaction.response.send_message(
                "❌ Você não está cadastrado no evento Treasure Hunt.", ephemeral=True
            )
            return

        pontos = player.get("pontos", 0)
        if pontos <= 0:
            await interaction.response.send_message(
                "❌ Você não tem pontos para converter.", ephemeral=True
            )
            return

        if uid in banco.get("pending_conversoes", {}):
            await interaction.response.send_message(
                "⏳ Você já tem uma solicitação pendente. Aguarde a resposta da administração.",
                ephemeral=True,
            )
            return

        guild = interaction.guild
        canal_logs_id = banco["channels"].get("logs")
        canal_logs = guild.get_channel(canal_logs_id) if canal_logs_id else None
        if not isinstance(canal_logs, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Canal de logs não configurado. Contate a administração.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🔄 Solicitação de Conversão de Pontos",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Jogador (Discord)", value=interaction.user.mention, inline=True)
        embed.add_field(name="Nome no Jogo", value=player.get("nome_jogo", "—"), inline=True)
        embed.add_field(name="Steam", value=player.get("steam", "—"), inline=False)
        embed.add_field(name="Pontos a converter", value=f"**{pontos} pts**", inline=True)
        embed.set_footer(text=f"uid: {uid}")

        msg_log = await canal_logs.send(
            content=f"🔔 Solicitação de conversão — {interaction.user.mention}",
            embed=embed,
            view=ConversaoAprovacaoView(self.cog),
        )

        banco2 = load_banco()
        banco2.setdefault("pending_conversoes", {})[uid] = msg_log.id
        save_banco(banco2)

        await interaction.response.send_message(
            f"✅ Solicitação enviada! Você tem **{pontos} pts** aguardando conversão.\n"
            f"Você receberá uma DM quando a administração responder.",
            ephemeral=True,
        )
        await self.cog._log(
            guild,
            f"🔄 **Solicitação de conversão** — {interaction.user.mention}\n"
            f"• Pontos: **{pontos} pts**",
        )


# ─────────────────────────────────────────────────────────────
# VIEW — APROVAÇÃO DE CONVERSÃO (canal logs — admin)
# ─────────────────────────────────────────────────────────────

class ConversaoAprovacaoView(discord.ui.View):
    """View persistente no canal logs — admin aprova ou rejeita a conversão."""
    def __init__(self, cog: "TreasureHuntCog"):
        super().__init__(timeout=None)
        self.cog = cog

    def _uid(self, interaction: discord.Interaction) -> Optional[str]:
        if not interaction.message or not interaction.message.embeds:
            return None
        footer = interaction.message.embeds[0].footer
        if footer and footer.text and "uid: " in footer.text:
            return footer.text.split("uid: ", 1)[1].strip()
        return None

    @discord.ui.button(label="✅ Confirmar Troca", style=discord.ButtonStyle.green, custom_id="th_conv_aprovar")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return
        uid = self._uid(interaction)
        if not uid:
            await interaction.response.send_message("❌ Não foi possível identificar o jogador.", ephemeral=True)
            return
        await self.cog.processar_conversao(interaction, uid, aprovado=True)

    @discord.ui.button(label="❌ Rejeitar", style=discord.ButtonStyle.red, custom_id="th_conv_rejeitar")
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return
        uid = self._uid(interaction)
        if not uid:
            await interaction.response.send_message("❌ Não foi possível identificar o jogador.", ephemeral=True)
            return
        await interaction.response.send_modal(RejeitarConversaoModal(self.cog, uid))


# ─────────────────────────────────────────────────────────────
# MODAL — REJEIÇÃO DE CONVERSÃO COM MOTIVO
# ─────────────────────────────────────────────────────────────

class RejeitarConversaoModal(discord.ui.Modal, title="Rejeitar Conversão"):
    motivo = discord.ui.TextInput(
        label="Motivo da rejeição",
        placeholder="Ex: Evento ainda em andamento, pontos reservados, etc.",
        style=discord.TextStyle.long,
        required=True,
        max_length=500,
    )

    def __init__(self, cog: "TreasureHuntCog", uid: str):
        super().__init__()
        self.cog = cog
        self.uid = uid

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.processar_conversao(
            interaction, self.uid, aprovado=False, motivo=self.motivo.value.strip()
        )


# ─────────────────────────────────────────────────────────────
# VIEW — SELEÇÃO DE DESAFIO (após envio de imagem)
# ─────────────────────────────────────────────────────────────

class DesafioSelectView(discord.ui.View):
    """View temporária (5 min) enviada para o membro após enviar imagem."""
    def __init__(self, cog: "TreasureHuntCog", uid: str, options: list):
        super().__init__(timeout=300)
        pass  # substituído pelo fluxo de reações


# ─────────────────────────────────────────────────────────────
# COG PRINCIPAL
# ─────────────────────────────────────────────────────────────

class TreasureHuntCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._painel_inicializado = False
        self._last_reminder_date: Optional[date] = None

    async def cog_load(self):
        self.bot.add_view(CadastroView(self))
        self.bot.add_view(ProvaAprovacaoView(self))
        self.bot.add_view(PainelEventoView(self))
        self.bot.add_view(ConversaoPontosView(self))
        self.bot.add_view(ConversaoAprovacaoView(self))
        print("[TREASURE] ✅ Views persistentes registradas (Cadastro, Aprovação, PainelEvento, Conversão).")
        if not self.friday_reminder_task.is_running():
            self.friday_reminder_task.start()

    async def cog_unload(self):
        if self.friday_reminder_task.is_running():
            self.friday_reminder_task.cancel()

    # ─── Lembrete semanal de sexta-feira ─────────────────────

    @tasks.loop(hours=1)
    async def friday_reminder_task(self):
        """Toda sexta-feira às 18h, envia DM para todos os jogadores cadastrados."""
        now = datetime.now()
        # Sexta = weekday 4, hora 18
        if now.weekday() != 4 or now.hour != 18:
            return
        today = now.date()
        if self._last_reminder_date == today:
            return
        self._last_reminder_date = today

        banco = load_banco()
        players = banco.get("players", {})
        if not players:
            return

        evento = banco.get("evento_atual", {})
        mapa = evento.get("mapa", "TBA")
        semana = evento.get("semana", "?")

        sent = 0
        failed = 0
        for discord_id_str in players:
            try:
                user = await self.bot.fetch_user(int(discord_id_str))
                embed = discord.Embed(
                    title="🗺️ Treasure Hunt - Lembrete Semanal!",
                    description=(
                        f"Não esqueça! O **Treasure Hunt** acontece **amanhã** (domingo)!\n\n"
                        f"📍 **Mapa:** {mapa}\n"
                        f"📅 **Semana:** {semana}\n\n"
                        f"Certifique-se de estar pronto e online para não perder os desafios!"
                    ),
                    color=discord.Color.gold(),
                    timestamp=datetime.now()
                )
                embed.set_footer(text="The Legendary Treasure Hunt Sundays")
                await user.send(embed=embed)
                sent += 1
            except (discord.Forbidden, discord.NotFound):
                failed += 1
            except Exception:
                failed += 1
        print(f"[TREASURE] ✉️ Lembrete sexta enviado: {sent} DMs, {failed} falhos")

    @friday_reminder_task.before_loop
    async def before_friday_reminder(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        if self._painel_inicializado:
            return
        self._painel_inicializado = True
        await self._reiniciar_paineis()

    # ─────────────────────────────────────────────────────────────
    # HELPERS INTERNOS
    # ─────────────────────────────────────────────────────────────

    async def _reiniciar_paineis(self) -> None:
        """Remove mensagens de paineis antigos do Discord e recria fresh.
        Roda一 única vez no startup — garante estado limpo em qualquer máquina."""
        banco = load_banco()
        # Sempre força canais do .env ao reiniciar
        env_channels = {
            "banco":    int(os.getenv("TH_CHANNEL_BANCO",    "0") or "0"),
            "cadastro": int(os.getenv("TH_CHANNEL_CADASTRO", "0") or "0"),
            "ranking":  int(os.getenv("TH_CHANNEL_RANKING",  "0") or "0"),
            "provas":   int(os.getenv("TH_CHANNEL_PROVAS",   "0") or "0"),
            "logs":     int(os.getenv("TH_CHANNEL_LOGS",     "0") or "0"),
        }
        banco["channels"] = env_channels
        save_banco(banco)
        channels = banco["channels"]
        print(f"[TREASURE] 🔍 Canais do .env aplicados: banco={channels.get('banco')} | cadastro={channels.get('cadastro')} | ranking={channels.get('ranking')} | provas={channels.get('provas')} | logs={channels.get('logs')}")

        # Cada entrada: (canal_id, chave no banco)
        rastreiados = [
            (channels.get("banco"),    "banco_message_id"),
            (channels.get("ranking"),  "ranking_message_id"),
            (channels.get("cadastro"), "cadastro_message_id"),
            (channels.get("provas"),   "provas_message_id"),
        ]

        # Limpa TODAS as mensagens do bot nos canais (não só a por ID salvo)
        bot_id = self.bot.user.id
        for canal_id, chave in rastreiados:
            if not canal_id:
                continue
            for guild in self.bot.guilds:
                canal = guild.get_channel(canal_id)
                if not isinstance(canal, discord.TextChannel):
                    continue
                # Coleta histórico e deleta individualmente (mais confiável que bulk)
                deletadas = 0
                erros = 0
                try:
                    async for m in canal.history(limit=100):
                        if m.author.id == bot_id:
                            try:
                                await m.delete()
                                deletadas += 1
                            except Exception as e_del:
                                erros += 1
                                print(f"[TREASURE] ⚠️ Não deletou msg {m.id} em #{canal.name}: {e_del}")
                except Exception as e_hist:
                    print(f"[TREASURE] ⚠️ Erro ao ler histórico de #{canal.name}: {e_hist}")
                print(f"[TREASURE] 🗑️ #{canal.name}: {deletadas} msg(s) deletada(s), {erros} erro(s)")
                break
            banco[chave] = None

        save_banco(banco)
        print("[TREASURE] 🔄 Paineis antigos removidos — recriando fresh.")

        # Nomes esperados dos canais — aplica rename se necessário
        _nomes_canais = {
            "banco":    "📅︱evento-atual",
            "cadastro": "📋︱cadastro",
            "ranking":  "🏆︱ranking-de-eventos",
            "provas":   "📸︱provas",
            "logs":     "🔒︱logs",
        }
        for guild in self.bot.guilds:
            banco_reload = load_banco()
            for chave, nome_esperado in _nomes_canais.items():
                canal_id = banco_reload["channels"].get(chave)
                if not canal_id:
                    continue
                ch = guild.get_channel(canal_id)
                if isinstance(ch, discord.TextChannel) and ch.name != nome_esperado:
                    try:
                        await ch.edit(name=nome_esperado)
                        print(f"[TREASURE] ✏️ Canal '{chave}' renomeado para '{nome_esperado}'")
                    except Exception as e:
                        print(f"[TREASURE] ⚠️ Não foi possível renomear '{chave}': {e}")

        import traceback
        for guild in self.bot.guilds:
            print(f"[TREASURE] 🏗️ Recriando paineis para guild: {guild.name}")
            try:
                await self._recuperar_dados_perdidos(guild)
            except Exception as e:
                print(f"[TREASURE] ⚠️ Erro em _recuperar_dados_perdidos: {e}")
                traceback.print_exc()
            try:
                await self._atualizar_painel_banco(guild)
                print("[TREASURE] ✅ Painel banco atualizado")
            except Exception as e:
                print(f"[TREASURE] ⚠️ Erro em _atualizar_painel_banco: {e}")
                traceback.print_exc()
            try:
                await self._atualizar_ranking(guild)
                print("[TREASURE] ✅ Ranking atualizado")
            except Exception as e:
                print(f"[TREASURE] ⚠️ Erro em _atualizar_ranking: {e}")
                traceback.print_exc()
            try:
                await self._repostar_painel_cadastro(guild)
                print("[TREASURE] ✅ Painel cadastro repostado")
            except Exception as e:
                print(f"[TREASURE] ⚠️ Erro em _repostar_painel_cadastro: {e}")
                traceback.print_exc()
            try:
                await self._repostar_painel_provas(guild)
                print("[TREASURE] ✅ Painel provas repostado")
            except Exception as e:
                print(f"[TREASURE] ⚠️ Erro em _repostar_painel_provas: {e}")
                traceback.print_exc()

    async def _recuperar_dados_perdidos(self, guild: discord.Guild) -> None:
        """Reconstrói _pending_reactions em memória e processa imagens enviadas offline."""
        banco = load_banco()
        canal_id = banco["channels"].get("provas")
        if not canal_id:
            return
        canal = guild.get_channel(canal_id)
        if not isinstance(canal, discord.TextChannel):
            return

        # ── 1. Reconectar pending_provas já persistidos no banco ──
        pending_provas = banco.get("pending_provas", {})
        perdidos: list[str] = []
        recuperados = 0
        for uid, dados in list(pending_provas.items()):
            msg_id = dados.get("bot_message_id")
            if not msg_id:
                perdidos.append(uid)
                continue
            try:
                await canal.fetch_message(msg_id)
            except (discord.NotFound, discord.HTTPException):
                perdidos.append(uid)
                continue
            # Reações ainda existem no Discord — só reconecta o lookup em memória
            _pending_reactions[msg_id] = uid
            recuperados += 1

        for uid in perdidos:
            pending_provas.pop(uid, None)
        banco["pending_provas"] = pending_provas
        save_banco(banco)

        if recuperados:
            print(f"[TREASURE] ♻️ {recuperados} prova(s) pendente(s) reconectada(s) após restart.")

        # ── 2. Processar imagens enviadas enquanto o bot estava offline ──
        banco_atual = load_banco()
        processadas = 0
        async for msg in canal.history(limit=200):
            if msg.author.bot:
                continue
            imagem = next(
                (a for a in msg.attachments if a.content_type and a.content_type.startswith("image/")),
                None,
            )
            if not imagem:
                continue
            uid = str(msg.author.id)
            if uid in banco_atual.get("pending_provas", {}):
                continue  # já tem seleção pendente ativa
            if uid not in banco_atual.get("players", {}):
                try:
                    await msg.delete()
                except discord.Forbidden:
                    pass
                try:
                    await canal.send(
                        f"⚠️ {msg.author.mention} — imagem enviada durante o restart ignorada: você não está cadastrado.",
                        delete_after=30,
                    )
                except discord.Forbidden:
                    pass
                continue
            challenges = banco_atual.get("challenges", {})
            if not challenges:
                continue
            # Não reprocessa se o membro já tem prova pendente para qualquer criatura
            tem_pendente = any(
                p["user_id"] == uid and p["status"] == "pendente"
                for p in banco_atual.get("provas", {}).values()
            )
            if tem_pendente:
                continue
            await self._processar_imagem_prova(msg, imagem, uid, canal, banco_atual, offline=True)
            processadas += 1
            banco_atual = load_banco()  # recarrega para evitar sobrescritas

        if processadas:
            print(f"[TREASURE] 📸 {processadas} imagem(ns) de prova recuperada(s) do histórico do canal.")

    async def _repostar_painel_provas(self, guild: discord.Guild) -> None:
        """Posta (ou reposta) o embed de instruções do canal de provas."""
        banco = load_banco()
        canal_id = banco["channels"].get("provas")
        if not canal_id:
            return
        canal = guild.get_channel(canal_id)
        if not isinstance(canal, discord.TextChannel):
            return
        embed = discord.Embed(
            title="📸 Envio de Provas — Treasure Hunt",
            description=(
                "Envie uma **imagem** neste canal do dinossauro morto mostrando o **nome** e o **nível** dele para registrar sua prova. \n"
                "O bot irá reconhecer a imagem e perguntar qual criatura do evento ela comprova.\n\n"
                "⚠️ Você não pode enviar duas provas da mesma criatura (pendente ou aprovada)."
            ),
            color=discord.Color.green(),
        )
        msg = await canal.send(embed=embed)
        banco["provas_message_id"] = msg.id
        save_banco(banco)

    async def _repostar_painel_cadastro(self, guild: discord.Guild) -> None:
        """Posta (ou reposta) o embed de cadastro com CadastroView no canal correto."""
        banco = load_banco()
        canal_id = banco["channels"].get("cadastro")
        if not canal_id:
            return
        canal = guild.get_channel(canal_id)
        if not isinstance(canal, discord.TextChannel):
            return
        embed = discord.Embed(
            title="📋 The Legendary Treasure Hunt Sundays — Cadastro",
            description=REGULAMENTO_TEXTO,
            color=discord.Color.blue(),
        )
        msg = await canal.send(embed=embed, view=CadastroView(self))
        banco["cadastro_message_id"] = msg.id
        save_banco(banco)

    async def _log(self, guild: Optional[discord.Guild], mensagem: str) -> None:
        if not guild:
            return
        banco = load_banco()
        canal_id = banco["channels"].get("logs")
        if not canal_id:
            return
        canal = guild.get_channel(canal_id)
        if isinstance(canal, discord.TextChannel):
            embed = discord.Embed(
                description=mensagem,
                color=discord.Color.dark_gray(),
                timestamp=datetime.now(timezone.utc),
            )
            try:
                await canal.send(embed=embed)
            except discord.Forbidden:
                pass

    async def _atualizar_ranking(self, guild: Optional[discord.Guild]) -> None:
        """Delega ao RankingCog — ranking unificado gerenciado centralmente."""
        if not guild:
            return
        ranking_cog = self.bot.get_cog("RankingCog")
        if ranking_cog:
            try:
                await ranking_cog.update(guild)  # type: ignore
            except Exception as e:
                print(f"[TREASURE] ⚠️ Erro ao atualizar ranking via RankingCog: {e}")

    async def processar_aprovacao(
        self,
        interaction: discord.Interaction,
        prova_id: str,
        aprovado: bool,
        motivo: Optional[str] = None,
    ) -> None:
        banco = load_banco()
        prova = banco["provas"].get(prova_id)
        if not prova:
            await interaction.response.send_message("❌ Prova não encontrada.", ephemeral=True)
            return
        if prova["status"] != "pendente":
            await interaction.response.send_message("⚠️ Esta prova já foi avaliada.", ephemeral=True)
            return

        guild = interaction.guild
        membro = guild.get_member(int(prova["user_id"])) if guild else None


        if aprovado:
            desafio = banco["challenges"].get(prova["challenge_id"], {})
            pontos = desafio.get("pontos", 0)
            uid = prova["user_id"]
            if uid in banco["players"]:
                banco["players"][uid]["pontos"] = banco["players"][uid].get("pontos", 0) + pontos

            # Concede XP proporcional ao evento (pontos × 500)
            try:
                from typing import cast
                from cogs.xp import XPSystem  # Import direto dentro do método
                xp_cog = self.bot.get_cog("XPSystem")
                if xp_cog and membro:
                    xp_cog_typed = cast(XPSystem, xp_cog)
                    xp_total = pontos * 500
                    await xp_cog_typed.add_xp_and_check_level(membro, xp_total, source="evento")
            except Exception as e:
                print(f"[TREASURE] ⚠️ Erro ao conceder XP de evento: {e}")

            prova["status"] = "aprovada"
            prova["aprovado_por"] = str(interaction.user)
            save_banco(banco)

            await self._log(
                guild,
                f"✅ **Prova aprovada** por {interaction.user.mention}\n"
                f"• Prova ID: `{prova_id}`\n"
                f"• Jogador: {membro.mention if membro else prova['discord_tag']}\n"
                f"• Desafio: `{prova['challenge_id']}` (+{pontos} pts)",
            )
            if membro:
                try:
                    await membro.send(
                        f"✅ Sua prova `#{prova_id}` foi **aprovada**! +{pontos} pontos adicionados ao seu ranking e **{pontos * 500} XP** concedidos."
                    )
                except discord.Forbidden:
                    pass

            if guild:
                await self._atualizar_ranking(guild)
                await self._atualizar_painel_banco(guild)
            await interaction.response.send_message(f"✅ Prova `#{prova_id}` aprovada.", ephemeral=True)

        else:
            prova["status"] = "rejeitada"
            prova["justificativa"] = motivo
            prova["aprovado_por"] = str(interaction.user)
            # Remove pending_provas caso o membro ainda tenha algum preso
            uid_rej = prova["user_id"]
            banco.get("pending_provas", {}).pop(uid_rej, None)
            _pending_image_data.pop(uid_rej, None)
            save_banco(banco)

            await self._log(
                guild,
                f"❌ **Prova rejeitada** por {interaction.user.mention}\n"
                f"• Prova ID: `{prova_id}`\n"
                f"• Jogador: {membro.mention if membro else prova['discord_tag']}\n"
                f"• Motivo: {motivo}",
            )
            if membro:
                try:
                    await membro.send(
                        f"❌ Sua prova `#{prova_id}` foi **rejeitada**.\n📝 Motivo: {motivo}"
                    )
                except discord.Forbidden:
                    pass

            await interaction.response.send_message(f"❌ Prova `#{prova_id}` rejeitada.", ephemeral=True)

        # Desabilita botões na mensagem original (no canal de logs)
        try:
            canal_id = banco["channels"].get("logs")
            if canal_id and interaction.guild:
                canal = interaction.guild.get_channel(canal_id)
                if isinstance(canal, discord.TextChannel) and prova.get("message_id"):
                    msg = await canal.fetch_message(prova["message_id"])
                    view = discord.ui.View()
                    status_label = "✅ Aprovada" if aprovado else "❌ Rejeitada"
                    btn = discord.ui.Button(
                        label=status_label,
                        disabled=True,
                        style=discord.ButtonStyle.green if aprovado else discord.ButtonStyle.red,
                    )
                    view.add_item(btn)
                    await msg.edit(view=view)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────
    # CONVERSÃO DE PONTOS → LOJA
    # ─────────────────────────────────────────────────────────────

    async def processar_conversao(
        self,
        interaction: discord.Interaction,
        uid: str,
        aprovado: bool,
        motivo: Optional[str] = None,
    ) -> None:
        banco = load_banco()
        player = banco.get("players", {}).get(uid)
        if not player:
            await interaction.response.send_message("❌ Jogador não encontrado.", ephemeral=True)
            return

        pontos = player.get("pontos", 0)
        guild = interaction.guild
        membro = guild.get_member(int(uid)) if guild else None
        mention = membro.mention if membro else f"<@{uid}>"

        banco.setdefault("pending_conversoes", {}).pop(uid, None)

        if aprovado:
            banco["players"][uid]["pontos"] = 0
            save_banco(banco)

            await interaction.response.send_message(
                f"✅ Conversão de **{pontos} pts** de {mention} confirmada. Pontos zerados no ranking.",
                ephemeral=True,
            )
            if membro:
                try:
                    await membro.send(
                        f"✅ Sua solicitação de conversão de **{pontos} pontos** do Treasure Hunt foi **aceita**!\n"
                        f"Os pontos foram transferidos para a loja pelo administrador."
                    )
                except discord.Forbidden:
                    pass

            await self._log(
                guild,
                f"🔄 **Conversão aprovada** por {interaction.user.mention}\n"
                f"• Jogador: {mention}\n"
                f"• Pontos convertidos: **{pontos} pts** (zerados no ranking)",
            )
            await self._atualizar_ranking(guild)

        else:
            save_banco(banco)

            await interaction.response.send_message(
                f"❌ Conversão de {mention} rejeitada. O jogador será notificado por DM.",
                ephemeral=True,
            )
            if membro:
                try:
                    await membro.send(
                        f"❌ Sua solicitação de conversão de **{pontos} pontos** do Treasure Hunt foi **rejeitada**.\n"
                        f"📝 Motivo: {motivo}"
                    )
                except discord.Forbidden:
                    pass

            await self._log(
                guild,
                f"🔄 **Conversão rejeitada** por {interaction.user.mention}\n"
                f"• Jogador: {mention}\n"
                f"• Motivo: {motivo}",
            )

        # Desabilita botões na mensagem de logs
        try:
            status_label = "✅ Troca Confirmada" if aprovado else "❌ Rejeitada"
            view = discord.ui.View()
            btn = discord.ui.Button(
                label=status_label,
                disabled=True,
                style=discord.ButtonStyle.green if aprovado else discord.ButtonStyle.red,
            )
            view.add_item(btn)
            await interaction.message.edit(view=view)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────
    # LISTENER — IMAGEM NO CANAL DE PROVAS
    # ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        banco = load_banco()
        canal_provas_id = banco["channels"].get("provas")
        if not canal_provas_id or message.channel.id != canal_provas_id:
            return

        # Sem anexo: delete e orienta
        if not message.attachments:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            await message.channel.send(
                f"{message.author.mention} Envie uma **imagem** neste canal do dinossauro morto mostrando o **nome** e o **nível** dele para registrar sua prova.",
                delete_after=10,
            )
            return

        # Busca imagem no anexo
        imagem = next(
            (a for a in message.attachments if a.content_type and a.content_type.startswith("image/")),
            None,
        )
        if not imagem:
            return

        uid = str(message.author.id)

        # Jogador não cadastrado
        if uid not in banco.get("players", {}):
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            await message.channel.send(
                f"⚠️ {message.author.mention} Você não está cadastrado no evento. "
                f"Cadastre-se no canal de cadastro antes de enviar provas.",
                delete_after=15,
            )
            return

        # Desafios disponíveis
        challenges = banco.get("challenges", {})
        if not challenges:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            await message.channel.send(
                f"⚠️ {message.author.mention} Nenhum desafio cadastrado ainda. Aguarde a administração.",
                delete_after=15,
            )
            return

        # Já tem prova pendente aguardando seleção
        if uid in banco.get("pending_provas", {}):
            pending_data = banco["pending_provas"][uid]
            msg_id = pending_data.get("bot_message_id")
            embed_existe = False
            if msg_id and isinstance(message.channel, discord.TextChannel):
                try:
                    await message.channel.fetch_message(msg_id)
                    embed_existe = True
                except (discord.NotFound, discord.HTTPException):
                    pass

            if embed_existe:
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
                await message.channel.send(
                    f"⏳ {message.author.mention} Você ainda tem uma prova pendente de confirmação. "
                    f"Selecione a criatura na mensagem anterior antes de enviar outra imagem.",
                    delete_after=15,
                )
                return
            else:
                # Embed de seleção não existe mais — limpa o pending preso e continua
                banco["pending_provas"].pop(uid, None)
                if msg_id:
                    _pending_reactions.pop(msg_id, None)
                save_banco(banco)

        if not isinstance(message.channel, discord.TextChannel):
            return

        # Bloqueia se já tem alguma prova pendente aguardando avaliação
        tem_pendente = any(
            p["user_id"] == uid and p["status"] == "pendente"
            for p in banco.get("provas", {}).values()
        )
        if tem_pendente:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            await message.channel.send(
                f"⏳ {message.author.mention} Você já tem uma prova aguardando avaliação. "
                f"Aguarde a resposta da administração antes de enviar outra.",
                delete_after=15,
            )
            return

        await self._processar_imagem_prova(message, imagem, uid, message.channel, banco)

    async def _processar_imagem_prova(
        self,
        source_msg: discord.Message,
        imagem: discord.Attachment,
        uid: str,
        canal: discord.TextChannel,
        banco: dict,
        offline: bool = False,
    ) -> None:
        """Baixa imagem, posta embed numerado com reações para o membro selecionar a criatura."""
        challenges = banco.get("challenges", {})
        challenge_list = list(challenges.items())[:10]  # Máx 10 — limite de reações numeradas

        # Baixa imagem e guarda bytes em memória para uso posterior no log
        img_file: Optional[discord.File] = None
        image_url = imagem.proxy_url
        img_bytes: Optional[bytes] = None
        img_filename: str = imagem.filename
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(imagem.url) as resp:
                    img_bytes = await resp.read()
            img_file = discord.File(io.BytesIO(img_bytes), filename=img_filename)
        except Exception:
            pass

        try:
            await source_msg.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        # Constrói lista numerada de criaturas
        linhas = []
        for i, (cid, dados) in enumerate(challenge_list):
            mapa = dados.get("mapa", "—")
            pontos = dados.get("pontos", 0)
            linhas.append(f"{NUMBER_EMOJIS[i]} **{dados['nome']}** — {mapa} ({pontos} pts)")

        titulo = "📸 Imagem recuperada — qual é a criatura?" if offline else "📸 Imagem recebida — qual é a criatura?"
        embed = discord.Embed(
            title=titulo,
            description=(
                f"{source_msg.author.mention}, selecione a criatura desta prova clicando na reação:\n\n"
                + "\n".join(linhas)
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )

        if img_file:
            embed.set_image(url=f"attachment://{imagem.filename}")
            sent = await canal.send(embed=embed, file=img_file)
            image_url = sent.attachments[0].url if sent.attachments else image_url
        else:
            embed.set_image(url=image_url)
            sent = await canal.send(embed=embed)

        # Adiciona as reações numeradas
        for i in range(len(challenge_list)):
            try:
                await sent.add_reaction(NUMBER_EMOJIS[i])
            except discord.HTTPException:
                pass

        # Persiste pending
        _pending_reactions[sent.id] = uid
        if img_bytes:
            _pending_image_data[uid] = (img_bytes, img_filename)
        banco_p = load_banco()
        banco_p.setdefault("pending_provas", {})[uid] = {
            "image_url": image_url,
            "bot_message_id": sent.id,
            "challenges": [[cid, d["nome"]] for cid, d in challenge_list],
        }
        save_banco(banco_p)

    # ─────────────────────────────────────────────────────────────
    # LISTENER — REAÇÃO DO MEMBRO (seleção de criatura)
    # ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.user_id == self.bot.user.id:
            return
        if payload.message_id not in _pending_reactions:
            return

        uid = _pending_reactions[payload.message_id]
        canal = self.bot.get_channel(payload.channel_id)
        if not isinstance(canal, discord.TextChannel):
            return

        # Ignora reação de outro usuário — remove silenciosamente
        if str(payload.user_id) != uid:
            if payload.member:
                try:
                    msg = await canal.fetch_message(payload.message_id)
                    await msg.remove_reaction(payload.emoji, payload.member)
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    pass
            return

        emoji_str = str(payload.emoji)
        if emoji_str not in NUMBER_EMOJIS:
            # Emoji inválido — remove
            if payload.member:
                try:
                    msg = await canal.fetch_message(payload.message_id)
                    await msg.remove_reaction(payload.emoji, payload.member)
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    pass
            return

        idx = NUMBER_EMOJIS.index(emoji_str)
        banco = load_banco()
        pending = banco.get("pending_provas", {}).get(uid)
        if not pending:
            _pending_reactions.pop(payload.message_id, None)
            return

        challenge_list = pending.get("challenges", [])
        if idx >= len(challenge_list):
            return

        cid, nome_criatura = challenge_list[idx]
        image_url = pending["image_url"]
        guild = canal.guild
        member = guild.get_member(payload.user_id)
        mention = member.mention if member else f"<@{uid}>"

        # ── Verificação de duplicata ──
        # Versão assíncrona: verifica se a mensagem de log da prova ainda existe.
        # Se o embed de aprovação sumiu (admin deletou, bot reiniciou, etc.), a prova
        # é auto-cancelada para não deixar o membro preso indefinidamente.
        canal_logs_id = banco["channels"].get("logs")
        canal_logs = guild.get_channel(canal_logs_id)
        prova_bloqueante: Optional[str] = None  # prova_id que bloqueia
        for _pid, _p in list(banco.get("provas", {}).items()):
            if _p["user_id"] != uid or _p["challenge_id"] != cid:
                continue
            if _p["status"] in ("rejeitada", "cancelada"):
                continue
            # Prova pendente/aprovada — verifica se a mensagem de log ainda existe
            _msg_id = _p.get("message_id")
            if _msg_id and isinstance(canal_logs, discord.TextChannel):
                try:
                    await canal_logs.fetch_message(_msg_id)
                    prova_bloqueante = _pid  # mensagem existe → bloqueia legítimo
                    break
                except (discord.NotFound, discord.HTTPException):
                    # Mensagem sumiu → auto-cancela para liberar o membro
                    print(f"[TH] Prova {_pid} auto-cancelada: embed de log não encontrado")
                    _p["status"] = "cancelada"
                    _p["justificativa"] = "Auto-cancelada: embed de aprovação não encontrado"
                    continue
            else:
                # Sem message_id ainda (recém-criada, ainda não enviou para logs)
                prova_bloqueante = _pid
                break

        # Se houve auto-cancelamentos, salva e continua
        if not prova_bloqueante:
            save_banco(banco)

        if prova_bloqueante:
            try:
                msg = await canal.fetch_message(payload.message_id)
                await msg.delete()
            except (discord.NotFound, discord.HTTPException):
                pass
            _pending_reactions.pop(payload.message_id, None)
            banco.setdefault("pending_provas", {}).pop(uid, None)
            save_banco(banco)
            await canal.send(
                f"⚠️ {mention} Você já enviou uma prova para **{nome_criatura}** que está pendente ou aprovada. "
                f"Não é possível enviar outra para a mesma criatura.",
                delete_after=20,
            )
            return

        # ── Registra prova ──
        desafio = banco["challenges"].get(cid, {})
        prova_id = str(uuid.uuid4())[:8]
        banco["provas"][prova_id] = {
            "user_id": uid,
            "discord_tag": str(member) if member else uid,
            "challenge_id": cid,
            "descricao": "Enviado via imagem no canal de provas",
            "link_imagem": image_url,
            "bot_message_id": payload.message_id,
            "status": "pendente",
            "justificativa": None,
            "aprovado_por": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message_id": None,
        }
        banco.setdefault("pending_provas", {}).pop(uid, None)
        save_banco(banco)
        _pending_reactions.pop(payload.message_id, None)

        # ── Envia para verificação no canal de logs ANTES de deletar a mensagem ──
        # (a URL do CDN expira quando a mensagem é deletada)
        player_data = banco.get("players", {}).get(uid, {})
        embed = discord.Embed(
            title=f"📸 Prova #{prova_id} — Aguardando verificação",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Jogador (Discord)", value=mention, inline=True)
        embed.add_field(name="Nome no Jogo", value=player_data.get("nome_jogo", "—"), inline=True)
        embed.add_field(name="Steam", value=player_data.get("steam", "—"), inline=False)
        embed.add_field(name="Criatura", value=f"**{nome_criatura}**", inline=True)
        embed.add_field(name="Mapa", value=desafio.get("mapa", "—"), inline=True)
        embed.add_field(name="Pontos em jogo", value=f"**{desafio.get('pontos', 0)}** pts", inline=True)
        if player_data.get("tribos_raw"):
            embed.add_field(name="Tribos cadastradas", value=player_data["tribos_raw"][:512], inline=False)
        embed.set_footer(text=f"ID da prova: {prova_id}")

        # Usa bytes salvos em memória — garante que a imagem original é enviada sem depender de URL
        cached = _pending_image_data.pop(uid, None)
        log_file: Optional[discord.File] = None
        if cached:
            raw_bytes, raw_filename = cached
            log_file = discord.File(io.BytesIO(raw_bytes), filename=raw_filename)
            embed.set_image(url=f"attachment://{raw_filename}")
        else:
            embed.set_image(url=image_url)

        canal_logs_id = banco["channels"].get("logs")
        canal_logs = guild.get_channel(canal_logs_id) if canal_logs_id else None
        if isinstance(canal_logs, discord.TextChannel):
            msg_log = await canal_logs.send(
                content=f"🔔 Nova prova — {mention}",
                embed=embed,
                file=log_file if log_file else discord.utils.MISSING,
                view=ProvaAprovacaoView(self),
            )
            banco2 = load_banco()
            banco2["provas"][prova_id]["message_id"] = msg_log.id
            save_banco(banco2)

        await self._log(
            guild,
            f"📸 **Prova registrada** — {mention}\n"
            f"• ID: `{prova_id}` | Criatura: **{nome_criatura}**",
        )

        # Deleta a mensagem de seleção do canal de provas (imagem já salva no log)
        try:
            msg = await canal.fetch_message(payload.message_id)
            await msg.delete()
        except (discord.NotFound, discord.HTTPException):
            pass

        # Confirmação breve no canal de provas
        await canal.send(
            f"✅ {mention} — prova de **{nome_criatura}** registrada! Aguardando verificação.",
            delete_after=15,
        )

    # ─────────────────────────────────────────────────────────────
    # SETUP — COMANDO PRINCIPAL
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="th_cancelar_prova")
    @commands.has_permissions(administrator=True)
    async def th_cancelar_prova(self, ctx: commands.Context, prova_id: str):
        """Admin: força o cancelamento de uma prova presa. Uso: !th_cancelar_prova <id>"""
        banco = load_banco()
        prova = banco.get("provas", {}).get(prova_id)
        if not prova:
            await ctx.send(f"❌ Prova `{prova_id}` não encontrada.", delete_after=15)
            return
        status_anterior = prova["status"]
        prova["status"] = "cancelada"
        prova["justificativa"] = f"Cancelada manualmente por {ctx.author}"
        save_banco(banco)
        await ctx.send(
            f"✅ Prova `{prova_id}` cancelada (era `{status_anterior}`). O membro já pode reenviar.",
            delete_after=20,
        )

    @commands.command(name="setup_evento")
    @commands.has_permissions(administrator=True)
    async def setup_evento(self, ctx: commands.Context, category_id: int):
        """Configura os canais do Treasure Hunt em uma categoria existente."""
        guild = ctx.guild
        categoria = guild.get_channel(category_id)
        if not isinstance(categoria, discord.CategoryChannel):
            await ctx.send(f"❌ ID `{category_id}` não é uma categoria válida neste servidor.")
            return

        await ctx.send(f"⚙️ Configurando canais em **{categoria.name}**...")

        # Permissões do canal de logs (só admins)
        overwrites_logs = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites_logs[role] = discord.PermissionOverwrite(read_messages=True)

        banco = load_banco()

        async def _obter_ou_criar(chave: str, nome: str, topic: str, **kwargs) -> discord.TextChannel:
            canal_id = banco["channels"].get(chave)
            if canal_id:
                ch = guild.get_channel(canal_id)
                if isinstance(ch, discord.TextChannel):
                    await ch.edit(name=nome, topic=topic, category=categoria, **kwargs)
                    return ch
            return await categoria.create_text_channel(nome, topic=topic, **kwargs)

        ch_banco    = await _obter_ou_criar("banco",    "📅︱evento-atual", "Painel do evento ativo — mapa, semana e estatísticas.")
        ch_cadastro = await _obter_ou_criar("cadastro", "📋︱cadastro",     "Cadastre-se no Treasure Hunt aqui.")
        ch_ranking  = await _obter_ou_criar("ranking",  "🏆︱ranking-de-eventos", "Ranking atualizado do evento.")
        ch_provas   = await _obter_ou_criar("provas",   "📸︱provas",       "Envie suas provas aqui.")
        ch_logs     = await _obter_ou_criar("logs",     "🔒︱logs",         "Logs admin — Treasure Hunt.", overwrites=overwrites_logs)

        banco["channels"]["banco"]    = ch_banco.id
        banco["channels"]["cadastro"] = ch_cadastro.id
        banco["channels"]["ranking"]  = ch_ranking.id
        banco["channels"]["provas"]   = ch_provas.id
        banco["channels"]["logs"]     = ch_logs.id
        save_banco(banco)

        # Painel de cadastro
        embed_cad = discord.Embed(
            title="📋 The Legendary Treasure Hunt Sundays — Cadastro",
            description=REGULAMENTO_TEXTO,
            color=discord.Color.blue(),
        )
        msg_cad = await ch_cadastro.send(embed=embed_cad, view=CadastroView(self))
        banco2 = load_banco()
        banco2["cadastro_message_id"] = msg_cad.id
        save_banco(banco2)

        # Painel de provas (instrução fixa)
        embed_prov = discord.Embed(
            title="📸 Envio de Provas — Treasure Hunt",
            description=(
                "Envie uma **imagem** neste canal do dinossauro morto mostrando o **nome** e o **nível** dele para registrar sua prova.\n"
                "O bot irá reconhecer a imagem e perguntar qual criatura do evento ela comprova.\n\n"
                "⚠️ Você não pode enviar duas provas da mesma criatura (pendente ou aprovada)."
            ),
            color=discord.Color.green(),
        )
        msg_prov = await ch_provas.send(embed=embed_prov)
        banco_pv = load_banco()
        banco_pv["provas_message_id"] = msg_prov.id
        save_banco(banco_pv)

        # Ranking inicial
        embed_rank = discord.Embed(
            title="🏆 Ranking — The Legendary Treasure Hunt Sundays",
            description="*Aguardando cadastros e aprovações para exibir o ranking.*",
            color=discord.Color.gold(),
        )
        msg_rank = await ch_ranking.send(embed=embed_rank)
        banco3 = load_banco()
        banco3["ranking_message_id"] = msg_rank.id
        save_banco(banco3)

        # Painel do evento atual (evento-atual)
        await self._atualizar_painel_banco(guild)

        # Log interno
        await self._log(
            guild,
            f"🛠️ **Setup realizado** por {ctx.author.mention}\n"
            f"• Categoria: **{categoria.name}** (`{categoria.id}`)\n"
            f"• Banco: {ch_banco.mention}\n"
            f"• Cadastro: {ch_cadastro.mention}\n"
            f"• Ranking: {ch_ranking.mention}\n"
            f"• Provas: {ch_provas.mention}\n"
            f"• Logs: {ch_logs.mention}",
        )

        embed_ok = discord.Embed(
            title="✅ Evento configurado com sucesso!",
            color=discord.Color.green(),
            description=(
                f"• 💾 Banco: {ch_banco.mention}\n"
                f"• 📋 Cadastro: {ch_cadastro.mention}\n"
                f"• 🏆 Ranking: {ch_ranking.mention}\n"
                f"• 📸 Provas: {ch_provas.mention}\n"
                f"• 🔒 Logs: {ch_logs.mention}"
            ),
        )
        await ctx.send(embed=embed_ok)

    # ─────────────────────────────────────────────────────────────
    # GERENCIAR DESAFIOS
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="add_desafio")
    @commands.has_permissions(administrator=True)
    async def add_desafio(self, ctx: commands.Context):
        """Abre painel para adicionar um novo desafio via botão."""
        embed = discord.Embed(
            title="➕ Adicionar Desafio",
            description="Clique no botão para cadastrar um novo desafio de pontuação.",
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed, view=AddDesafioView(self))

    @commands.command(name="listar_desafios")
    async def listar_desafios(self, ctx: commands.Context):
        """Lista todos os desafios cadastrados."""
        banco = load_banco()
        challenges = banco.get("challenges", {})
        if not challenges:
            await ctx.send("❌ Nenhum desafio cadastrado. Use `!add_desafio`.")
            return

        embed = discord.Embed(
            title="📋 Desafios Cadastrados — Treasure Hunt",
            color=discord.Color.blurple(),
        )
        for cid, dados in challenges.items():
            embed.add_field(
                name=f"`{cid}` — {dados['nome']}",
                value=(
                    f"• Mapa: **{dados.get('mapa', '—')}**\n"
                    f"• Requisito: {dados.get('requisito', '—')}\n"
                    f"• Pontos: **{dados.get('pontos', 0)}** pts"
                ),
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(name="remover_desafio")
    @commands.has_permissions(administrator=True)
    async def remover_desafio(self, ctx: commands.Context, desafio_id: str):
        """Remove um desafio pelo ID."""
        banco = load_banco()
        cid = desafio_id.lower()
        if cid not in banco["challenges"]:
            await ctx.send(f"❌ Desafio `{cid}` não encontrado.")
            return
        nome = banco["challenges"][cid]["nome"]
        del banco["challenges"][cid]
        save_banco(banco)
        await ctx.send(f"✅ Desafio `{cid}` ({nome}) removido.")
        await self._log(ctx.guild, f"🗑️ Desafio `{cid}` ({nome}) removido por {ctx.author.mention}.")

    # ─────────────────────────────────────────────────────────────
    # GERENCIAR PONTUAÇÃO MANUAL
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="add_pontos")
    @commands.has_permissions(administrator=True)
    async def add_pontos(self, ctx: commands.Context, membro: discord.Member, pontos: int):
        """Adiciona (ou remove, com valor negativo) pontos manualmente."""
        banco = load_banco()
        uid = str(membro.id)
        if uid not in banco["players"]:
            await ctx.send(f"❌ {membro.mention} não está cadastrado no evento.")
            return
        banco["players"][uid]["pontos"] = banco["players"][uid].get("pontos", 0) + pontos
        save_banco(banco)
        await self._atualizar_ranking(ctx.guild)
        sinal = "+" if pontos >= 0 else ""
        await ctx.send(f"✅ {sinal}{pontos} pts para {membro.mention}. Total: {banco['players'][uid]['pontos']} pts.")
        await self._log(ctx.guild, f"✏️ Pontos ajustados por {ctx.author.mention}: {sinal}{pontos} para {membro.mention}.")

    @commands.command(name="ver_jogador")
    async def ver_jogador(self, ctx: commands.Context, membro: Optional[discord.Member] = None):
        """Exibe informações de cadastro de um jogador."""
        alvo = membro or ctx.author
        banco = load_banco()
        uid = str(alvo.id)
        dados = banco["players"].get(uid)
        if not dados:
            await ctx.send(f"❌ {alvo.mention} não está cadastrado.")
            return
        embed = discord.Embed(title=f"👤 {dados.get('nome_jogo', '—')}", color=discord.Color.teal())
        embed.add_field(name="Steam", value=dados.get("steam", "—"), inline=False)
        embed.add_field(name="Pontos", value=f"**{dados.get('pontos', 0)}** pts", inline=True)
        embed.add_field(name="Tribos", value=dados.get("tribos_raw", "—"), inline=False)
        embed.set_footer(text=f"Cadastrado em {dados.get('cadastro_timestamp', '—')[:10]}")
        await ctx.send(embed=embed)

    @commands.command(name="listar_provas")
    @commands.has_permissions(administrator=True)
    async def listar_provas(self, ctx: commands.Context, status: str = "pendente"):
        """Lista provas por status: pendente, aprovada, rejeitada."""
        banco = load_banco()
        filtradas = {k: v for k, v in banco["provas"].items() if v["status"] == status}
        if not filtradas:
            await ctx.send(f"Nenhuma prova com status `{status}`.")
            return
        embed = discord.Embed(title=f"📋 Provas — {status.capitalize()}", color=discord.Color.blurple())
        for pid, p in list(filtradas.items())[:10]:
            embed.add_field(
                name=f"#{pid}",
                value=f"Jogador: `{p['discord_tag']}`\nDesafio: `{p['challenge_id']}`",
                inline=True,
            )
        if len(filtradas) > 10:
            embed.set_footer(text=f"+{len(filtradas)-10} provas não exibidas.")
        await ctx.send(embed=embed)

    @commands.command(name="atualizar_ranking")
    @commands.has_permissions(administrator=True)
    async def cmd_atualizar_ranking(self, ctx: commands.Context):
        """Força atualização do embed de ranking no canal."""
        await self._atualizar_ranking(ctx.guild)
        await ctx.send("✅ Ranking atualizado.")

    # ─────────────────────────────────────────────────────────────
    # PAINEL DO EVENTO ATUAL (canal evento-atual)
    # ─────────────────────────────────────────────────────────────

    async def _atualizar_painel_banco(self, guild: Optional[discord.Guild]) -> None:
        """Atualiza (ou cria) o embed fixo de status do evento no canal evento-atual."""
        if not guild:
            print("[TREASURE] [PAINEL] Guild não fornecida para atualizar painel.")
            return
        banco = load_banco()
        canal_id = banco["channels"].get("banco")
        if not canal_id:
            print("[TREASURE] [PAINEL] Nenhum canal_id configurado em banco['channels']['banco'].")
            return
        canal = guild.get_channel(canal_id)
        if not isinstance(canal, discord.TextChannel):
            print(f"[TREASURE] [PAINEL] Canal id {canal_id} não encontrado ou não é TextChannel.")
            return

        ev = banco.get("evento_atual", {})
        mapa = ev.get("mapa") or "*Não definido*"
        semana = ev.get("semana") or "*Não definido*"
        inicio = ev.get("data_inicio") or "*Não definido*"
        fim = ev.get("data_fim") or "*Não definido*"
        obs = ev.get("observacao") or "*Nenhuma*"

        jogadores = len(banco.get("players", {}))
        desafios = len(banco.get("challenges", {}))
        provas_pendentes = sum(
            1 for p in banco.get("provas", {}).values() if p.get("status") == "pendente"
        )
        provas_aprovadas = sum(
            1 for p in banco.get("provas", {}).values() if p.get("status") == "aprovada"
        )

        embed = discord.Embed(
            title="📋 Status do Evento — Treasure Hunt Sundays",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="🗺️ Mapa Atual", value=mapa, inline=True)
        embed.add_field(name="📅 Semana", value=semana, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="🟢 Início", value=inicio, inline=True)
        embed.add_field(name="🔴 Fim", value=fim, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="👥 Jogadores cadastrados", value=str(jogadores), inline=True)
        embed.add_field(name="🎯 Desafios ativos", value=str(desafios), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="⏳ Provas pendentes", value=str(provas_pendentes), inline=True)
        embed.add_field(name="✅ Provas aprovadas", value=str(provas_aprovadas), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="📝 Observação", value=obs, inline=False)
        embed.set_footer(text="Atualizado automaticamente")

        view = PainelEventoView(self)

        msg_id = banco.get("banco_message_id")
        if msg_id:
            try:
                msg = await canal.fetch_message(msg_id)
                await msg.edit(embed=embed, view=view)
                print(f"[TREASURE] [PAINEL] Painel atualizado em canal {canal.name} (msg_id={msg_id})")
                return
            except discord.NotFound:
                print(f"[TREASURE] [PAINEL] Mensagem antiga do painel não encontrada (id={msg_id}), criando nova.")
            except Exception as e:
                print(f"[TREASURE] [PAINEL] Erro ao editar painel existente: {e}")

        try:
            msg = await canal.send(embed=embed, view=view)
            banco["banco_message_id"] = msg.id
            save_banco(banco)
            print(f"[TREASURE] [PAINEL] Painel criado em canal {canal.name} (msg_id={msg.id})")
        except Exception as e:
            print(f"[TREASURE] [PAINEL] Falha ao enviar painel no canal {canal.name}: {e}")

    # ─────────────────────────────────────────────────────────────
    # TRATAMENTO DE ERROS
    # ─────────────────────────────────────────────────────────────

    @setup_evento.error
    @add_desafio.error
    @add_pontos.error
    async def cmd_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Você não tem permissão de administrador.", delete_after=8)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Argumento faltando: `{error.param.name}`.", delete_after=8)
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Argumento inválido: {error}", delete_after=8)


# ─────────────────────────────────────────────────────────────
# VIEW/MODAL — DEFINIR EVENTO ATUAL
# ─────────────────────────────────────────────────────────────

class PainelEventoView(discord.ui.View):
    """View persistente fixada no canal evento-atual."""

    def __init__(self, cog: TreasureHuntCog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="⚙️ Configurar Evento",
        style=discord.ButtonStyle.primary,
        custom_id="th_painel_configurar_evento",
    )
    async def configurar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return
        banco = load_banco()
        ev = banco.get("evento_atual", {})
        challenges = banco.get("challenges", {})

        embed = discord.Embed(title="⚙️ Configurar Evento", color=discord.Color.blurple())
        embed.add_field(name="Mapa", value=ev.get("mapa") or "—", inline=True)
        embed.add_field(name="Semana", value=ev.get("semana") or "—", inline=True)
        embed.add_field(name="Período", value=f"{ev.get('data_inicio', '—')} → {ev.get('data_fim', '—')}", inline=False)
        if ev.get("observacao"):
            embed.add_field(name="Observação", value=ev["observacao"], inline=False)

        if challenges:
            linhas = [f"• `{cid}` — **{d['nome']}** ({d.get('pontos', 0)} pts)" for cid, d in challenges.items()]
            embed.add_field(name="🦕 Criaturas cadastradas", value="\n".join(linhas), inline=False)
        else:
            embed.add_field(name="🦕 Criaturas cadastradas", value="*Nenhuma ainda.*", inline=False)

        await interaction.response.send_message(embed=embed, view=ConfigEventoHubView(self.cog), ephemeral=True)

    @discord.ui.button(
        label="🚫 Remover Jogador",
        style=discord.ButtonStyle.danger,
        custom_id="th_painel_remover_jogador",
    )
    async def remover_jogador(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return
        await interaction.response.send_modal(RemoverJogadorModal(self.cog))


class ConfigEventoHubView(discord.ui.View):
    """Hub de administração do evento — aberto pelo botão Configurar Evento."""

    def __init__(self, cog: TreasureHuntCog):
        super().__init__(timeout=180)
        self.cog = cog

    @discord.ui.button(label="📋 Editar Dados do Evento", style=discord.ButtonStyle.primary, row=0)
    async def editar_dados(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetEventoModal(self.cog))

    @discord.ui.button(label="🦕 Adicionar Criatura", style=discord.ButtonStyle.success, row=0)
    async def adicionar_criatura(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddCriaturaModal(self.cog))

    @discord.ui.button(label="🗑️ Remover Criatura", style=discord.ButtonStyle.danger, row=0)
    async def remover_criatura(self, interaction: discord.Interaction, button: discord.ui.Button):
        banco = load_banco()
        if not banco.get("challenges"):
            await interaction.response.send_message("❌ Nenhuma criatura cadastrada.", ephemeral=True)
            return
        await interaction.response.send_message(
            "🗑️ Selecione a criatura que deseja remover:",
            view=RemoverCriaturaView(self.cog),
            ephemeral=True,
        )


class SetEventoModal(discord.ui.Modal, title="Evento Atual — Treasure Hunt"):
    mapa = discord.ui.TextInput(
        label="Mapa Atual",
        placeholder="Ex: The Island",
        required=True,
        max_length=64,
    )
    semana = discord.ui.TextInput(
        label="Semana",
        placeholder="Ex: Semana 1 — The Island",
        required=True,
        max_length=64,
    )
    data_inicio = discord.ui.TextInput(
        label="Data de Início",
        placeholder="Ex: 20/04/2026",
        required=True,
        max_length=20,
    )
    data_fim = discord.ui.TextInput(
        label="Data de Fim",
        placeholder="Ex: 26/04/2026",
        required=True,
        max_length=20,
    )
    observacao = discord.ui.TextInput(
        label="Observação (opcional)",
        placeholder="Ex: Semana estendida por feriado",
        required=False,
        style=discord.TextStyle.long,
        max_length=300,
    )

    def __init__(self, cog: TreasureHuntCog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        banco = load_banco()
        banco["evento_atual"] = {
            "mapa": self.mapa.value.strip(),
            "semana": self.semana.value.strip(),
            "data_inicio": self.data_inicio.value.strip(),
            "data_fim": self.data_fim.value.strip(),
            "observacao": self.observacao.value.strip() or None,
        }
        save_banco(banco)

        await self.cog._atualizar_painel_banco(interaction.guild)
        await self.cog._log(
            interaction.guild,
            f"📋 **Evento atualizado** por {interaction.user.mention}\n"
            f"• Mapa: {self.mapa.value.strip()}\n"
            f"• Semana: {self.semana.value.strip()}\n"
            f"• Período: {self.data_inicio.value.strip()} → {self.data_fim.value.strip()}",
        )
        await interaction.response.send_message(
            f"✅ Evento atualizado! Painel `evento-atual` atualizado.",
            ephemeral=True,
        )


class RemoverJogadorModal(discord.ui.Modal, title="Remover Jogador — Treasure Hunt"):
    usuario_id = discord.ui.TextInput(
        label="ID do Discord ou @menção",
        placeholder="Cole o ID numérico do membro (ex: 123456789012345678)",
        required=True,
        max_length=32,
    )

    def __init__(self, cog: TreasureHuntCog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.usuario_id.value.strip().strip("<@!>")
        if not raw.isdigit():
            await interaction.response.send_message("❌ ID inválido. Informe apenas o número.", ephemeral=True)
            return

        banco = load_banco()
        uid = raw
        dados = banco["players"].get(uid)
        if not dados:
            await interaction.response.send_message("❌ Jogador não encontrado no cadastro.", ephemeral=True)
            return

        banco["players"].pop(uid)
        banco.get("provas", {}).pop(uid, None)
        banco.get("pending_provas", {}).pop(uid, None)
        banco.get("pending_conversoes", {}).pop(uid, None)
        save_banco(banco)

        await self.cog._atualizar_ranking(interaction.guild)
        await self.cog._log(
            interaction.guild,
            f"🚫 **Cadastro removido** — <@{uid}> (ID: `{uid}`)\n"
            f"• Nome: `{dados.get('nome_jogo', '—')}`\n"
            f"• Removido por: {interaction.user.mention}",
        )
        await interaction.response.send_message(
            f"✅ Cadastro de <@{uid}> (`{dados.get('nome_jogo', '—')}`) removido.",
            ephemeral=True,
        )


# ─────────────────────────────────────────────────────────────
# VIEW/MODAL — GERENCIAR CRIATURAS
# ─────────────────────────────────────────────────────────────

class CriaturasManageView(discord.ui.View):
    def __init__(self, cog: TreasureHuntCog):
        super().__init__(timeout=120)
        self.cog = cog

    @discord.ui.button(label="➕ Adicionar Criatura", style=discord.ButtonStyle.success, row=0)
    async def adicionar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddCriaturaModal(self.cog))

    @discord.ui.button(label="🗑️ Remover Criatura", style=discord.ButtonStyle.danger, row=0)
    async def remover(self, interaction: discord.Interaction, button: discord.ui.Button):
        banco = load_banco()
        if not banco.get("challenges"):
            await interaction.response.send_message("❌ Nenhuma criatura cadastrada.", ephemeral=True)
            return
        await interaction.response.send_message(
            "🗑️ Selecione a criatura que deseja remover:",
            view=RemoverCriaturaView(self.cog),
            ephemeral=True,
        )


class AddCriaturaModal(discord.ui.Modal, title="Adicionar Criaturas — Treasure Hunt"):
    criaturas = discord.ui.TextInput(
        label="Criaturas (uma por linha)",
        placeholder="Nome; pontos; descrição — Ex: Giganotossauro; 25; Domar um Giga acima nível 100",
        style=discord.TextStyle.long,
        required=True,
        max_length=2000,
    )

    def __init__(self, cog: TreasureHuntCog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        banco = load_banco()
        mapa_atual = banco.get("evento_atual", {}).get("mapa", "—")
        adicionadas = []
        erros = []

        for i, linha in enumerate(self.criaturas.value.strip().splitlines(), start=1):
            linha = linha.strip()
            if not linha:
                continue
            partes = [p.strip() for p in linha.split(";")]
            if len(partes) < 2:
                erros.append(f"Linha {i}: formato inválido (`{linha}`)")
                continue
            nome = partes[0]
            try:
                pts = int(partes[1])
            except ValueError:
                erros.append(f"Linha {i}: pontuação inválida em `{linha}`")
                continue
            requisito = partes[2] if len(partes) >= 3 else "—"
            cid = nome.lower().replace(" ", "_")
            # Garante ID único acrescentando sufixo numérico se necessário
            base_cid = cid
            contador = 1
            while cid in banco["challenges"]:
                cid = f"{base_cid}_{contador}"
                contador += 1
            banco["challenges"][cid] = {
                "nome": nome,
                "mapa": mapa_atual,
                "requisito": requisito,
                "pontos": pts,
                "criado_por": str(interaction.user),
                "criado_em": datetime.now(timezone.utc).isoformat(),
            }
            adicionadas.append(f"`{cid}` — {nome} ({pts} pts)")

        if not adicionadas and not erros:
            await interaction.response.send_message("❌ Nenhuma criatura encontrada no texto.", ephemeral=True)
            return

        save_banco(banco)

        linhas_resposta = []
        if adicionadas:
            linhas_resposta.append(f"✅ **{len(adicionadas)} criatura(s) cadastrada(s):**\n" + "\n".join(adicionadas))
        if erros:
            linhas_resposta.append("⚠️ **Erros:**\n" + "\n".join(erros))

        if adicionadas:
            await self.cog._log(
                interaction.guild,
                f"🦕 **{len(adicionadas)} criatura(s) adicionada(s)** por {interaction.user.mention}:\n"
                + "\n".join(adicionadas),
            )

        await interaction.response.send_message("\n\n".join(linhas_resposta), ephemeral=True)


class RemoverCriaturaView(discord.ui.View):
    """View com Select menu para remover criatura — mostra lista das cadastradas."""

    def __init__(self, cog: TreasureHuntCog):
        super().__init__(timeout=60)
        self.cog = cog
        banco = load_banco()
        challenges = banco.get("challenges", {})
        options = [
            discord.SelectOption(
                label=dados["nome"][:100],
                value=cid,
                description=f"{dados.get('mapa', '—')} — {dados.get('pontos', 0)} pts"[:100],
            )
            for cid, dados in list(challenges.items())[:25]
        ]
        select = discord.ui.Select(
            placeholder="Selecione a criatura a remover...",
            options=options,
            min_values=1,
            max_values=1,
        )
        select.callback = self._on_select
        self.select = select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        cid = self.select.values[0]
        banco = load_banco()
        dados = banco.get("challenges", {}).get(cid)
        if not dados:
            await interaction.response.send_message("❌ Criatura não encontrada.", ephemeral=True)
            return
        nome = dados["nome"]
        del banco["challenges"][cid]
        save_banco(banco)
        await self.cog._log(
            interaction.guild,
            f"🗑️ **Criatura removida** por {interaction.user.mention}\n"
            f"• ID: `{cid}`\n"
            f"• Nome: {nome}",
        )
        await interaction.response.send_message(
            f"✅ Criatura **{nome}** removida com sucesso.",
            ephemeral=True,
        )


# ─────────────────────────────────────────────────────────────
# VIEW — ADICIONAR DESAFIO (admin)
# ─────────────────────────────────────────────────────────────

class AddDesafioView(discord.ui.View):
    def __init__(self, cog: TreasureHuntCog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label="➕ Novo Desafio", style=discord.ButtonStyle.blurple, custom_id="th_add_desafio_btn")
    async def novo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return
        await interaction.response.send_modal(AddDesafioModal(self.cog))


class AddDesafioModal(discord.ui.Modal, title="Adicionar Desafio"):
    nome = discord.ui.TextInput(label="Nome do Desafio", placeholder="Ex: Giga Nível 1000", max_length=64)
    desafio_id = discord.ui.TextInput(
        label="ID curto (slug)",
        placeholder="Ex: giga_1000  (sem espaços, minúsculo)",
        max_length=32,
    )
    mapa = discord.ui.TextInput(
        label="Mapa",
        placeholder="Ex: The Island",
        max_length=32,
    )
    requisito = discord.ui.TextInput(
        label="Requisito / Descrição",
        placeholder="Ex: Derrote um Giga nível exatamente 1000",
        style=discord.TextStyle.long,
        max_length=300,
    )
    pontos = discord.ui.TextInput(
        label="Pontuação",
        placeholder="Ex: 10",
        max_length=6,
    )

    def __init__(self, cog: TreasureHuntCog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        try:
            pts = int(self.pontos.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ A pontuação deve ser um número inteiro.", ephemeral=True)
            return

        cid = self.desafio_id.value.strip().lower().replace(" ", "_")
        banco = load_banco()
        banco["challenges"][cid] = {
            "nome": self.nome.value.strip(),
            "mapa": self.mapa.value.strip(),
            "requisito": self.requisito.value.strip(),
            "pontos": pts,
            "criado_por": str(interaction.user),
            "criado_em": datetime.now(timezone.utc).isoformat(),
        }
        save_banco(banco)

        await self.cog._log(
            interaction.guild,
            f"➕ **Desafio criado** por {interaction.user.mention}\n"
            f"• ID: `{cid}`\n"
            f"• Nome: {self.nome.value.strip()}\n"
            f"• Mapa: {self.mapa.value.strip()}\n"
            f"• Pontos: {pts}",
        )
        await interaction.response.send_message(
            f"✅ Desafio `{cid}` ({self.nome.value.strip()}) — **{pts} pts** cadastrado!", ephemeral=True
        )


# ─────────────────────────────────────────────────────────────
# SETUP DO COG
# ─────────────────────────────────────────────────────────────

async def setup(bot: commands.Bot):
    await bot.add_cog(TreasureHuntCog(bot))
