# cogs/ranking.py
"""Ranking Global Unificado
Lê xp.json, referrals.json e treasure_hunt.json e posta/edita
uma única mensagem no RANKING_CHANNEL_ID.

Outros cogs não postam no canal de ranking — apenas chamam:
    cog = bot.get_cog("RankingCog")
    if cog:
        await cog.update(guild)
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

import discord
from discord.ext import commands, tasks

import config

RANKING_CHANNEL_ID: int = config.RANKING_CHANNEL_ID
RANKING_EXCLUDED_IDS: set[int] = set(config.RANKING_EXCLUDED_IDS)

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XP_FILE    = os.path.join(_BASE, ".bancos", "xp.json")
REF_FILE   = os.path.join(_BASE, ".bancos", "referrals.json")
TH_FILE    = os.path.join(_BASE, ".bancos", "treasure_hunt.json")
STATE_FILE = os.path.join(_BASE, ".bancos", "ranking_state.json")


def _load_state() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(data: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def compute_scores(guild: discord.Guild) -> list:
    """Retorna lista de (uid_int, level, msg_xp, voice_xp, refs, th_pts, score) ordenada por score."""
    xp_data  = _load_json(XP_FILE)
    ref_data = _load_json(REF_FILE)
    th_data  = _load_json(TH_FILE)

    # Indicações aprovadas por referrer_id (all-time)
    ref_counts: dict = {}
    for r in ref_data.get("referrals", []):
        if r.get("status") == "approved":
            rid = str(r.get("referrer_id", ""))
            if rid:
                ref_counts[rid] = ref_counts.get(rid, 0) + 1

    # TH pontos por discord_id
    th_map: dict = {
        str(uid): (data.get("pontos", 0) if isinstance(data, dict) else 0)
        for uid, data in th_data.get("players", {}).items()
    }

    all_ids = set(xp_data.keys()) | set(ref_counts.keys()) | set(th_map.keys())

    scores = []
    for uid_str in all_ids:
        try:
            uid_int = int(uid_str)
        except ValueError:
            continue
        raw = xp_data.get(uid_str, {})
        if not isinstance(raw, dict):
            raw = {}
        level   = int(raw.get("level", 0))
        msg_xp  = int(raw.get("message_xp_total", 0))
        voice_xp = int(raw.get("voice_xp_total", 0))
        refs    = ref_counts.get(uid_str, 0)
        th_pts  = th_map.get(uid_str, 0)
        # Fórmula: nível base + XP msg (peso 1) + XP voz (peso 0.3) + Refs + Eventos (dominantes)
        score = (level * 100_000) + msg_xp + int(voice_xp * 0.3) + refs * 5_000 + th_pts * 500
        scores.append((uid_int, level, msg_xp, voice_xp, refs, th_pts, score))

    scores.sort(key=lambda e: e[6], reverse=True)
    return scores


def build_embed(guild: discord.Guild) -> discord.Embed:
    all_scores = compute_scores(guild)

    # Separa excluídos (staff) da competição
    scores  = [s for s in all_scores if s[0] not in RANKING_EXCLUDED_IDS]
    staff   = [s for s in all_scores if s[0] in RANKING_EXCLUDED_IDS]

    embed = discord.Embed(
        title="🌐 Ranking Global — Comunidade",
        description="⭐ XP/Nível  ·  🔗 Indicações  ·  🏆 Treasure Hunt",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc),
    )

    formula_text = (
        "**Nível** → cada nível completo vale **+100.000 pts**\n"
        "**💬 Mensagens** → cada XP de mensagem vale **+1 pt**\n"
        "**🎙️ Voz** → cada XP de call vale **+0,3 pt** *(menos que mensagens)*\n"
        "**🔗 Indicações** → cada indicação aprovada vale **+5.000 pts**\n"
        "**🎪 Evento Rotativo** → cada ponto de evento vale **+500 pts**\n\n"
        "*Exemplo: 375 pts no evento = +187.500 pts no ranking.*"
    )
    embed.add_field(name="📊 Como é calculado:", value=formula_text, inline=False)

    premio_text = (
        "🥇 **1º lugar** → 1.000 pontos\n"
        "🥈 **2º lugar** → 750 pontos\n"
        "🥉 **3º lugar** → 500 pontos\n"
        "🏅 **4º, 5º e 6º** → 300 pontos cada\n"
        "🎖️ **7º, 8º e 9º** → 200 pontos cada\n"
        "🎗️ **10º lugar** → 100 pontos\n\n"
        "*Pontos creditados diretamente na loja do jogo. Premiação entregue entre os dias **1 e 3** de cada mês.*"
    )
    embed.add_field(name="🎁 Premiação mensal — Top 10:", value=premio_text, inline=False)

    medalhas = ["🥇", "🥈", "🥉"]
    linhas = []
    for i, (uid_int, level, msg_xp, voice_xp, refs, th_pts, score) in enumerate(scores[:10]):
        prefixo = medalhas[i] if i < 3 else f"`#{i + 1}`"
        member = guild.get_member(uid_int)
        nome = member.display_name if member else f"<@{uid_int}>"
        parts = [f"**{score:,} pts**".replace(",", ".")]
        if refs:
            parts.append(f"🔗 {refs} ref{'s' if refs != 1 else ''}")
        if th_pts:
                parts.append(f"🎪 {th_pts} Evento")
        detalhes = f" — {' · '.join(parts)}" if parts else ""
        linhas.append(f"{prefixo} **{nome}** *(Nv.{level})*{detalhes}")

    embed.add_field(
        name="Top 10:",
        value="\n".join(linhas) if linhas else "*Nenhum dado registrado ainda.*",
        inline=False,
    )

    if staff:
        staff_linhas = []
        for uid_int, level, msg_xp, voice_xp, refs, th_pts, score in staff:
            member = guild.get_member(uid_int)
            nome = member.display_name if member else f"<@{uid_int}>"
            parts = [f"**{score:,} pts**".replace(",", ".")]
            if refs:
                parts.append(f"🔗 {refs} ref{'s' if refs != 1 else ''}")
            if th_pts:
                parts.append(f"� {th_pts} Evento")
            detalhes = f" — {' · '.join(parts)}" if parts else ""
            staff_linhas.append(f"⚙️ **{nome}** *(Nv.{level})*{detalhes}")
        embed.add_field(
            name="⚙️ Staff (fora da competição):",
            value="\n".join(staff_linhas),
            inline=False,
        )

    embed.set_footer(text="Atualizado automaticamente · a cada 5 minutos")
    embed.add_field(
        name="ℹ️ Dica:",
        value="Use o comando `!xphelp` para receber, só para você, uma explicação detalhada de como funciona o XP, ranking e premiação.",
        inline=False,
    )
    return embed


# ─────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────

class RankingCog(commands.Cog, name="RankingCog"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._message: Optional[discord.Message] = None
        state = _load_state()
        self._message_id: Optional[int] = state.get("message_id")

    async def cog_load(self) -> None:
        if not self.auto_update.is_running():
            self.auto_update.start()

    async def cog_unload(self) -> None:
        if self.auto_update.is_running():
            self.auto_update.cancel()

    # ─── Atualização automática horária ──────────────────────

    @tasks.loop(minutes=5)
    async def auto_update(self) -> None:
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self.update(guild)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            await self.update(guild)

    # ─── Método público ──────────────────────────────────────

    async def update(self, guild: Optional[discord.Guild] = None) -> None:
        """Posta ou edita o ranking no canal. Chamado por outros cogs quando necessário."""
        if guild is None:
            for g in self.bot.guilds:
                await self.update(g)
            return

        channel = self.bot.get_channel(RANKING_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            try:
                channel = await self.bot.fetch_channel(RANKING_CHANNEL_ID)
            except Exception:
                print(f"[Ranking] ❌ Canal {RANKING_CHANNEL_ID} não encontrado.")
                return
        if not isinstance(channel, discord.TextChannel):
            return

        embed = build_embed(guild)

        # 1. Tenta editar mensagem em memória
        if self._message:
            try:
                await self._message.edit(embed=embed)
                return
            except discord.NotFound:
                self._message = None

        # 2. Tenta recuperar pelo ID persistido no disco
        if self._message_id:
            try:
                msg = await channel.fetch_message(self._message_id)
                self._message = msg
                await msg.edit(embed=embed)
                print("[Ranking] 🔁 Mensagem de ranking editada (via state).")
                return
            except discord.NotFound:
                self._message_id = None
                _save_state({})

        # 3. Procura mensagem existente do bot no histórico
        async for msg in channel.history(limit=20):
            if msg.author == self.bot.user and msg.embeds:
                self._message = msg
                self._message_id = msg.id
                _save_state({"message_id": msg.id})
                await msg.edit(embed=embed)
                print("[Ranking] 🔁 Mensagem de ranking editada (via histórico).")
                return

        # 4. Nenhuma encontrada: limpa canal e posta do zero
        try:
            await channel.purge(limit=None)
        except Exception:
            pass
        self._message = await channel.send(embed=embed)
        self._message_id = self._message.id
        _save_state({"message_id": self._message.id})
        print("[Ranking] ✅ Ranking global postado.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RankingCog(bot))
