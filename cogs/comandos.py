# cogs/comandos.py
import discord
from discord.ext import commands
from typing import Any


class ComandosCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="bobo", aliases=["comandos", "ajuda"])
    async def help_command(self, ctx: commands.Context[Any]):
        """Exibe todos os comandos do bot organizados por categoria."""

        try:
            resolved = await self.bot.get_prefix(ctx.message)
            p = resolved if isinstance(resolved, str) else (resolved[0] if resolved else "!")
        except Exception:
            p = "!"

        # ── embed 1: geral + calculadora + apelidos ────────────────────
        e1 = discord.Embed(
            title="📚 Comandos do Bobonic — Parte 1/3",
            color=discord.Color.blue()
        )

        e1.add_field(
            name="📖 Geral",
            value=(
                f"`{p}bobo` / `{p}comandos` / `{p}ajuda` — Exibe este menu de ajuda\n"
                f"`{p}echo <msg>` — Faz o bot repetir uma mensagem\n"
                f"`{p}regras` / `{p}rules` — Exibe as regras do servidor\n"
                f"`{p}xp` / `{p}level` / `{p}lvl` — Mostra seu nível e XP atual\n"
                f"`{p}promo [steam]` — Busca e publica promoções de jogos gratuitos"
            ),
            inline=False
        )

        e1.add_field(
            name="🦕 Calculadora de Dinossauros",
            value=(
                f"`{p}criarcalc` / `{p}criarpainel` — Cria os 3 painéis (Vanilla, Primal Fear, Omega)\n"
                f"`{p}tipos` — Lista as categorias de dinos e seus multiplicadores\n"
                f"`{p}dinos [nome]` — Lista os dinos disponíveis por modo/busca\n"
                f"`{p}historico` — Exibe o histórico de avaliações realizadas\n"
                f"`{p}ajudacalc` — Guia detalhado de como usar a calculadora"
            ),
            inline=False
        )

        e1.add_field(
            name="🏷️ Apelidos",
            value=(
                f"`{p}sincapelidos` — Sincroniza apelidos de todos os membros com seus cargos *(admin)*\n"
                f"`{p}cargosape` — Lista os cargos que afetam o apelido e sua prioridade\n"
                f"`{p}meuapelido` — Mostra seu apelido atual e qual cargo o determina"
            ),
            inline=False
        )

        e1.add_field(
            name="🎫 VIP",
            value=(
                f"`{p}painelvip` — Cria o painel VIP no canal configurado *(admin)*"
            ),
            inline=False
        )

        e1.set_footer(text=f"Prefixo: {p}  •  Página 1 de 3")

        # ── embed 2: lojas + tickets + moderação + autoloop ────────────
        e2 = discord.Embed(
            title="📚 Comandos do Bobonic — Parte 2/3",
            color=discord.Color.green()
        )

        e2.add_field(
            name="🏪 Lojas",
            value=(
                f"`{p}lojastart` — Cria o painel de lojas no canal *(admin)*\n"
                f"`{p}fecharloja` — Fecha e arquiva sua loja pessoal"
            ),
            inline=False
        )

        e2.add_field(
            name="🎫 Tickets",
            value=(
                f"`{p}ticketstart` — Cria o painel de abertura de tickets no canal *(admin)*"
            ),
            inline=False
        )

        e2.add_field(
            name="🧹 Moderação",
            value=(
                f"`{p}faxina` / `{p}purgeall` — Apaga **todas** as mensagens do canal *(manage_messages)*\n"
                f"`{p}limpar <n>` / `{p}clear <n>` — Apaga mensagens até atingir N caracteres *(manage_messages)*\n"
                f"`{p}limpezageral @user [limite]` — Purge global + quarentena de um usuário *(admin)*"
            ),
            inline=False
        )

        e2.add_field(
            name="🔁 AutoLoop *(admin)*",
            value=(
                f"`{p}cadloop <msg>` — Adiciona mensagem ao loop automático (envia a cada 6h)\n"
                f"`{p}listarloop` — Lista todas as mensagens cadastradas no loop\n"
                f"`{p}removerloop <nº>` — Remove uma mensagem do loop pelo índice\n"
                f"`{p}limparloop` — Remove **todas** as mensagens do loop (pede confirmação)\n"
                f"`{p}enviarloop` — Força o envio imediato de uma mensagem do loop"
            ),
            inline=False
        )

        e2.set_footer(text=f"Prefixo: {p}  •  Página 2 de 3")

        # ── embed 3: admin + testes ─────────────────────────────────────
        e3 = discord.Embed(
            title="📚 Comandos do Bobonic — Parte 3/3",
            color=discord.Color.orange()
        )

        e3.add_field(
            name="🦕 ARK: Survival Evolved *(admin)*",
            value=(
                f"`{p}arkmapas` — Lista os mapas e portas RCON configurados\n"
                f"`{p}arkstatus [mapa]` — Status dos servidores (online/offline e jogadores)\n"
                f"`{p}arkplayers <mapa>` — Lista jogadores conectados em um mapa\n"
                f"`{p}rcon <mapa> <comando>` — Envia qualquer comando RCON diretamente\n"
                f"`{p}arkligar <mapa>` — Inicia o servidor via systemctl\n"
                f"`{p}arkdesligar <mapa>` — Salva mundo e para o servidor *(pede confirmação)*\n"
                f"`{p}arkreinicia <mapa>` — Avisa, salva e reinicia *(pede confirmação)*\n"
                f"Mapas: `Ragnarok Omega` · `The Island` · `Genesis 2` · `Fjordur`"
            ),
            inline=False
        )

        e3.add_field(
            name="🔧 Administração do Bot *(admin)*",
            value=(
                f"`{p}reload <cog>` / `{p}recarregar <cog>` — Recarrega uma extensão sem reiniciar o bot\n"
                f"`{p}load <cog>` / `{p}carregar <cog>` — Carrega uma extensão desativada\n"
                f"`{p}unload <cog>` / `{p}descarregar <cog>` — Descarrega uma extensão ativa\n"
                f"`{p}restart` / `{p}reboot` / `{p}reiniciar` — Reinicia o bot\n"
                f"`{p}shutdown` / `{p}desligar` — Desliga o bot completamente"
            ),
            inline=False
        )

        e3.add_field(
            name="📋 Changelog *(admin)*",
            value=(
                f"`{p}chang <texto>` / `{p}changelog <texto>` — Publica changelog versionado (v0.1, v0.2…) no canal oficial\n"
                f"`{p}versao` / `{p}version` — Exibe a versão atual e o histórico de changelogs"
            ),
            inline=False
        )

        e3.add_field(
            name="🧪 Testes *(admin)*",
            value=(
                f"`{p}testar_boas_vindas` — Envia uma mensagem de boas-vindas de teste"
            ),
            inline=False
        )

        e3.add_field(
            name="💡 Legenda",
            value=(
                "*(admin)* → requer permissão de Administrador\n"
                "*(manage_messages)* → requer permissão de Gerenciar Mensagens"
            ),
            inline=False
        )

        e3.set_footer(text=f"Prefixo: {p}  •  Página 3 de 3")

        await ctx.send(embeds=[e1, e2, e3])

    @commands.command(name="echo")
    @commands.has_permissions(administrator=True)
    async def echo_command(self, ctx: commands.Context[Any], *, message: str):
        """Repete a mensagem enviada."""
        await ctx.send(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(ComandosCog(bot))
