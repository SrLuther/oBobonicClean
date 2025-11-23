# cogs/comandos.py
import discord
from discord.ext import commands

class ComandosCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="bobo", aliases=["comandos", "ajuda"])
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="📚 Comandos do Bot",
            description="Aqui está uma visão geral dos meus comandos disponíveis.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Geral",
            value="`!bobo` ou `!comandos` - Exibe esta mensagem de ajuda.\n"
                  "`!xp` - Mostra seu nível e progresso de XP.\n"
                  "`!rank` - Mostra o Top 10 do ranking do servidor.",
            inline=False
        )
        embed.add_field(
            name="Tickets",
            value="`!ticketpanel` (Admin) - Envia o painel de tickets.\n"
                  "`!fechar` - Fecha o ticket atual (apenas remove a permissão de envio).\n"
                  "`!reabrir` - Reabre um ticket fechado.\n"
                  "`!transcript` - Gera o histórico de mensagens do ticket.\n"
                  "`!arquivar` - Encerra, gera transcript e deleta o canal.",
            inline=False
        )
        embed.add_field(
            name="Moderação (Requer Permissão)",
            value="`!kick <@user>` - Expulsa um usuário.\n"
                  "`!ban <@user>` - Bane um usuário.\n"
                  "`!clear <quantia>` - Limpa mensagens no canal.",
            inline=False
        )
        embed.set_footer(text=f"Use o prefixo ! antes dos comandos.")
        await ctx.send(embed=embed)

    @commands.command(name="echo")
    async def echo_command(self, ctx, *, message):
        await ctx.send(message)

async def setup(bot):
    await bot.add_cog(ComandosCog(bot))

# ============================================================
# Atualizado em: 2025-11-23 22:41:53 (Horário de Brasília)
# ============================================================
