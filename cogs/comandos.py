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

        # ── embed 1: geral + xp + vinculação ARK ──────────────────────
        e1 = discord.Embed(
            title="📚 Comandos do Bobonic — Parte 1/5",
            color=discord.Color.blue()
        )

        e1.add_field(
            name="📖 Geral",
            value=(
                f"`{p}bobo` / `{p}comandos` / `{p}ajuda` — Exibe este menu de ajuda\n"
                f"`{p}echo <msg>` — Faz o bot repetir uma mensagem *(admin)*\n"
                f"`{p}regras` / `{p}rules` — Exibe as regras do servidor\n"
                f"`{p}promo [steam]` — Busca e publica promoções de jogos gratuitos"
            ),
            inline=False
        )

        e1.add_field(
            name="⭐ XP & Níveis",
            value=(
                f"`{p}xp` / `{p}level` / `{p}lvl` — Mostra seu nível e XP atual\n"
                f"`{p}xp @membro` — Mostra o nível de outro membro"
            ),
            inline=False
        )

        e1.add_field(
            name="🔗 Vinculação ARK ↔ Discord",
            value=(
                f"`{p}vincular <link_steam>` — Vincula seu perfil Steam ao Discord\n"
                f"`{p}meuvínculo` — Mostra suas informações de vinculação\n"
                f"`{p}atualizarpersonagem <nome>` — Atualiza o nome do seu personagem\n"
                f"`{p}removervinculo` — Remove sua vinculação"
            ),
            inline=False
        )

        e1.add_field(
            name="🦕 Calculadora de Dinossauros",
            value=(
                f"`{p}criarcalc` / `{p}criarpainel` — Cria os 3 painéis (Vanilla, Primal Fear, Omega) *(admin)*\n"
                f"`{p}tipos` — Lista as categorias de dinos e seus multiplicadores\n"
                f"`{p}dinos [nome]` — Lista os dinos disponíveis por modo/busca\n"
                f"`{p}historico` — Exibe o histórico de avaliações realizadas\n"
                f"`{p}ajudacalc` — Guia detalhado de como usar a calculadora"
            ),
            inline=False
        )

        e1.set_footer(text=f"Prefixo: {p}  •  Página 1 de 5")

        # ── embed 2: lojas + tickets + autoloop + vip ──────────────────
        e2 = discord.Embed(
            title="📚 Comandos do Bobonic — Parte 2/5",
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
            name="🎫 VIP",
            value=(
                f"`{p}painelvip` / `{p}vippainel` / `{p}criarvip` — Cria o painel VIP no canal configurado *(admin)*"
            ),
            inline=False
        )

        e2.add_field(
            name="🔁 AutoLoop *(admin)*",
            value=(
                f"`{p}cadloop <msg>` — Adiciona mensagem ao loop automático (envia a cada 6h)\n"
                f"`{p}listarloop` — Lista todas as mensagens cadastradas no loop\n"
                f"`{p}removerloop <nº>` — Remove uma mensagem do loop pelo índice\n"
                f"`{p}limparloop` — Remove **todas** as mensagens do loop *(pede confirmação)*\n"
                f"`{p}enviarloop` — Força o envio imediato de uma mensagem do loop"
            ),
            inline=False
        )

        e2.add_field(
            name="🎵 Música",
            value=(
                f"`{p}play` / `{p}tocar` / `{p}p <query>` — Toca música do YouTube\n"
                f"`{p}join` / `{p}chamar` / `{p}entrar` — Entra no seu canal de voz\n"
                f"`{p}skip` / `{p}pular` / `{p}s` — Pula a música atual\n"
                f"`{p}pause` / `{p}pausar` — Pausa a música\n"
                f"`{p}resume` / `{p}continuar` — Retoma a música pausada\n"
                f"`{p}stop` / `{p}parar` — Para e limpa a fila\n"
                f"`{p}leave` / `{p}sair` / `{p}dc` — Sai do canal de voz\n"
                f"`{p}queue` / `{p}fila` / `{p}q` — Exibe a fila de músicas\n"
                f"`{p}nowplaying` / `{p}np` / `{p}tocando` — Música sendo tocada\n"
                f"`{p}volume` / `{p}vol <0-200>` — Ajusta o volume"
            ),
            inline=False
        )

        e2.set_footer(text=f"Prefixo: {p}  •  Página 2 de 5")

        # ── embed 3: moderação + indicações ───────────────────────────
        e3 = discord.Embed(
            title="📚 Comandos do Bobonic — Parte 3/5",
            color=discord.Color.orange()
        )

        e3.add_field(
            name="🧹 Moderação",
            value=(
                f"`{p}faxina` / `{p}purgeall` — Apaga **todas** as mensagens do canal *(manage_messages)*\n"
                f"`{p}limpar <n>` / `{p}clear <n>` — Apaga mensagens até atingir N caracteres *(manage_messages)*\n"
                f"`{p}limpezageral @user [limite]` — Purge global + quarentena de um usuário *(admin)*"
            ),
            inline=False
        )

        e3.add_field(
            name="🤝 Indicações",
            value=(
                f"`{p}meus_pontos_indicacao` — Veja seus pontos como indicador e indicado\n"
                f"`{p}gerar_id_indicacao` — Acesso rápido ao painel de geração de código\n"
                f"`{p}enviar_indicacao` — Acesso rápido ao painel de envio de indicação\n"
                f"`{p}painel_indicacoes` — Painel admin de indicações *(MOD)*\n"
                f"`{p}limpar_indicacoes_quebradas` — Remove indicações inválidas *(MOD)*\n"
                f"`{p}recriar_paineis_indicacao` — Recria os painéis de indicação *(admin/MOD)*\n"
                f"`{p}atualizar_ranking_indicacoes` — Atualiza ranking manualmente *(admin/MOD)*\n"
                f"`{p}distribuir_premios_ranking` — Distribui prêmios ao top 3 do mês *(admin/MOD)*"
            ),
            inline=False
        )

        e3.add_field(
            name="📺 Twitch",
            value=(
                f"`{p}twitch_status` — Veja os canais monitorados e status de cada um\n"
                f"`{p}twitch_rebuild_panels` — Reconstrói os painéis do zero *(MOD)*"
            ),
            inline=False
        )

        e3.set_footer(text=f"Prefixo: {p}  •  Página 3 de 5")

        # ── embed 4: ARK ───────────────────────────────────────────────
        e4 = discord.Embed(
            title="📚 Comandos do Bobonic — Parte 4/5",
            color=discord.Color.dark_green()
        )

        e4.add_field(
            name="🦕 ARK: Survival Evolved",
            value=(
                f"`{p}arkstatus [mapa]` — Status de todos ou de um servidor específico\n"
                f"`{p}arkplayers <mapa>` — Lista jogadores conectados em um mapa *(admin)*\n"
                f"`{p}arkmapas` — Lista os mapas e portas RCON configurados *(admin)*\n"
                f"`{p}rcon <mapa> <comando>` — Envia qualquer comando RCON diretamente *(admin)*\n"
                f"`{p}arkligar <mapa>` — Inicia o servidor via systemctl *(admin)*\n"
                f"`{p}arkdesligar <mapa>` — Salva mundo e para o servidor *(admin)*\n"
                f"`{p}arkreinicia <mapa>` — Avisa, salva e reinicia *(admin)*\n"
                f"`{p}arkajuda` / `{p}arkhelp` — Guia completo de comandos ARK *(admin)*\n"
                f"Mapas: `Ragnarok Omega` · `Rotativo` · `Genesis 2` · `Alps`"
            ),
            inline=False
        )

        e4.add_field(
            name="👤 ARK: Moderação de Jogadores *(admin)*",
            value=(
                f"`{p}setuppainel [canal_id]` — Cria o painel de vinculação Steam ↔ Discord\n"
                f"`{p}arkkick @user [motivo]` — Kick em todos os servidores via RCON\n"
                f"`{p}arkhistorico @user [limite]` — Histórico de ações de um jogador\n"
                f"`{p}arkatualizar` — Força atualização imediata do monitor de jogadores\n"
                f"`{p}arkmonitor` — Estatísticas do monitor de jogadores"
            ),
            inline=False
        )

        e4.add_field(
            name="📊 Monitor RCON *(admin)*",
            value=(
                f"`{p}monitor_status` / `{p}monitorstatus` — Status do monitoramento e servidores\n"
                f"`{p}monitor_log` / `{p}monitorlog` [mapa] [qtd]` — Últimos eventos do monitoramento\n"
                f"`{p}setup_monitor` — Cria/recria os painéis de dashboards no canal configurado"
            ),
            inline=False
        )

        e4.set_footer(text=f"Prefixo: {p}  •  Página 4 de 5")

        # ── embed 5: admin + changelog + testes ───────────────────────
        e5 = discord.Embed(
            title="📚 Comandos do Bobonic — Parte 5/5",
            color=discord.Color.red()
        )

        e5.add_field(
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

        e5.add_field(
            name="📋 Changelog *(admin)*",
            value=(
                f"`{p}chang <texto>` / `{p}changelog <texto>` — Publica changelog versionado (v0.1, v0.2…)\n"
                f"`{p}versao` / `{p}version` — Exibe a versão atual e o histórico de changelogs"
            ),
            inline=False
        )

        e5.add_field(
            name="🧪 Testes *(admin)*",
            value=(
                f"`{p}testar_boas_vindas` — Envia uma mensagem de boas-vindas de teste"
            ),
            inline=False
        )

        e5.add_field(
            name="💡 Legenda",
            value=(
                "*(admin)* → requer permissão de Administrador\n"
                "*(MOD)* → requer cargo de Moderador\n"
                "*(manage_messages)* → requer permissão de Gerenciar Mensagens"
            ),
            inline=False
        )

        e5.set_footer(text=f"Prefixo: {p}  •  Página 5 de 5")

        await ctx.send(embeds=[e1, e2, e3, e4, e5])

    @commands.command(name="echo")
    @commands.has_permissions(administrator=True)
    async def echo_command(self, ctx: commands.Context[Any], *, message: str):
        """Repete a mensagem enviada."""
        await ctx.send(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(ComandosCog(bot))
