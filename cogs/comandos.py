import discord
from discord.ext import commands

class Comandos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ajuda")
    async def ajuda(self, ctx):
        embed = discord.Embed(
            title="📜 Lista de Comandos do oBobonic",
            description="Aqui estão todos os comandos disponíveis e o que eles fazem:",
            color=discord.Color.green()
        )

        # --- Tickets ---
        embed.add_field(name="🎫 Comandos de Tickets", value=(
            "`!abrirticket` — Abre um ticket de suporte.\n"
            "`!aceitarticket <ticket>` — Moderador aceita um ticket.\n"
            "`!fecharticket <ticket>` — Moderador fecha e arquiva um ticket.\n"
        ), inline=False)

        # --- Limpeza / Mensagens ---
        embed.add_field(name="🧹 Limpeza de Mensagens", value=(
            "`!limpar <caracteres>` — Deleta mensagens cumulativas até atingir a quantidade de caracteres.\n"
            "`!limpartudo` — Deleta todas as mensagens do canal.\n"
        ), inline=False)

        # --- Administração ---
        embed.add_field(name="⚙️ Administração", value=(
            "`!reload <cog>` — Recarrega uma extensão (admin/moderador).\n"
            "`!load <cog>` — Carrega uma extensão.\n"
            "`!unload <cog>` — Descarrega uma extensão.\n"
        ), inline=False)

        # --- Moderação ---
        embed.add_field(name="🛡️ Moderação", value=(
            "`!ban <usuário> [motivo]` — Bane um usuário.\n"
            "`!kick <usuário> [motivo]` — Expulsa um usuário.\n"
            "`!mute <usuário> [tempo]` — Silencia um usuário.\n"
            "`!unmute <usuário>` — Remove o silêncio.\n"
            "`!warn <usuário> [motivo]` — Adiciona advertência.\n"
            "`!warnings <usuário>` — Mostra advertências de um usuário.\n"
        ), inline=False)

        # --- XP / Experiência ---
        embed.add_field(name="⭐ XP", value=(
            "`!xp <usuário>` — Mostra o XP atual de um usuário.\n"
            "`!rank <usuário>` — Mostra a posição no ranking.\n"
        ), inline=False)

        # --- Comando de ajuda ---
        embed.add_field(name="📌 Utilitário", value="`!ajuda` — Mostra esta mensagem de ajuda.", inline=False)

        await ctx.send(embed=embed)

# --- Setup da cog ---
async def setup(bot):
    await bot.add_cog(Comandos(bot))
