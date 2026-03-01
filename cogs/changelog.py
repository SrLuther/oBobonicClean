# cogs/changelog.py
import discord
from discord.ext import commands
from typing import Any
from datetime import datetime
import json
import os

from config import CANAL_CHANGELOG_ID

CHANGELOG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "changelog.json")


def _load_data() -> dict:
    """Carrega os dados do changelog (versão + histórico)."""
    if not os.path.exists(CHANGELOG_FILE):
        return {"major": 0, "minor": 1, "history": []}
    with open(CHANGELOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_data(data: dict) -> None:
    """Salva os dados do changelog."""
    os.makedirs(os.path.dirname(CHANGELOG_FILE), exist_ok=True)
    with open(CHANGELOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _format_version(major: int, minor: int) -> str:
    return f"v{major}.{minor}"


def _next_version(data: dict) -> tuple[int, int]:
    """Retorna o próximo (major, minor) sem alterar o dict."""
    major = data.get("major", 0)
    minor = data.get("minor", 1)
    return major, minor


def _increment_version(data: dict) -> None:
    """Incrementa a versão no dict in-place."""
    minor = data.get("minor", 1) + 1
    if minor >= 10:
        data["major"] = data.get("major", 0) + 1
        data["minor"] = 0
    else:
        data["minor"] = minor


class ChangelogCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="chang", aliases=["changelog"])
    @commands.has_permissions(administrator=True)
    async def changelog_command(self, ctx: commands.Context[Any], *, conteudo: str):
        """Publica um changelog versionado no canal oficial.

        Uso: !chang <descrição das mudanças>
        """
        data = _load_data()
        major, minor = _next_version(data)
        versao = _format_version(major, minor)

        canal: discord.TextChannel | None = self.bot.get_channel(CANAL_CHANGELOG_ID)  # type: ignore[assignment]
        if canal is None:
            await ctx.send(
                f"⚠️ Canal de changelog (`{CANAL_CHANGELOG_ID}`) não encontrado. "
                "Verifique se o bot tem acesso ao canal.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📋 Changelog {versao}",
            description=conteudo,
            color=discord.Color.blurple(),
            timestamp=datetime.now()
        )
        embed.set_footer(
            text=f"Publicado por {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )

        await canal.send(embed=embed)

        # Salva histórico e incrementa versão para a próxima publicação
        data.setdefault("history", []).append({
            "version": versao,
            "content": conteudo,
            "author": str(ctx.author),
            "timestamp": datetime.now().isoformat()
        })
        _increment_version(data)
        _save_data(data)

        # Confirmação discreta no canal do autor
        if ctx.channel.id != CANAL_CHANGELOG_ID:
            await ctx.message.add_reaction("✅")
        
        await ctx.send(
            f"✅ Changelog **{versao}** publicado em {canal.mention}! "
            f"Próxima versão será **{_format_version(data['major'], data['minor'])}**.",
            delete_after=15
        )

    @changelog_command.error
    async def changelog_error(self, ctx: commands.Context[Any], error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "⚠️ Você precisa informar o conteúdo do changelog.\n"
                "**Uso:** `!chang <descrição das mudanças>`",
                delete_after=15
            )
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 Apenas administradores podem publicar changelogs.", delete_after=10)
        else:
            raise error

    @commands.command(name="versao", aliases=["version"])
    async def versao_atual(self, ctx: commands.Context[Any]):
        """Exibe a versão atual do servidor e o histórico de changelogs."""
        data = _load_data()
        versao_atual = _format_version(data.get("major", 0), data.get("minor", 1))

        historico = data.get("history", [])
        
        embed = discord.Embed(
            title="📋 Versão do Servidor",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Versão Atual", value=f"**{versao_atual}**", inline=False)

        if historico:
            ultimas = historico[-5:][::-1]  # últimas 5, mais recente primeiro
            linhas = []
            for entry in ultimas:
                ts = entry.get("timestamp", "")[:10]  # só a data
                linhas.append(f"**{entry['version']}** `{ts}` — {entry['content'][:80]}{'...' if len(entry['content']) > 80 else ''}")
            embed.add_field(name="Últimas Versões", value="\n".join(linhas), inline=False)
        else:
            embed.add_field(name="Histórico", value="Nenhum changelog publicado ainda.", inline=False)

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChangelogCog(bot))
