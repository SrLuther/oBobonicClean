import discord
from discord.ext import commands

# ==============================================================================
# 🚀 CLASSE PRINCIPAL: ComandosBasicos
# ==============================================================================
class ComandosBasicos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------ Comandos Básicos ------------------

    @commands.command(name="ping")
    async def ping(self, ctx):
        """Mostra a latência do bot."""
        latency_ms = round(self.bot.latency * 1000)
        await ctx.send(f"🏓 Pong! Latência: **{latency_ms}ms**")


    # ------------------ Menu de Ajuda Principal ------------------

    @commands.command(name="ajuda", aliases=['help'])
    async def ajuda(self, ctx):
        """Exibe o menu de ajuda com todos os módulos do bot."""
        
        embed = discord.Embed(
            title="🤖 Menu de Ajuda do Bobonic",
            description="Use `!` seguido do comando para interagir. Se precisar de um tutorial, a equipe pode ajudar!",
            color=discord.Color.blue()
        )
        
        # 1. Módulo Básico
        embed.add_field(
            name="🛠️ Básico/Utilidades",
            value="`!ajuda` / `!help`: Exibe este menu completo.\n`!ping`: Verifica a latência do bot.",
            inline=False
        )
        
        # 2. Módulo de Inteligência Artificial (AI)
        embed.add_field(
            name="🧠 Inteligência Artificial (Gemini)",
            value=(
                "`!ia <pergunta>` / `!chat`: Inicia um chat com memória.\n"
                "`!imagem <prompt>` / `!gerar`: Gera uma imagem a partir do seu prompt."
            ),
            inline=False
        )
        
        # 3. Módulo de XP e Ranking
        embed.add_field(
            name="⭐ XP e Ranking",
            value=(
                "`!xp [membro]`: Mostra seu nível e progresso.\n"
                "`!rank`: Exibe o Top 10 do servidor.\n"
                "`!xpinfo`: Regras de ganho de XP e níveis."
            ),
            inline=False
        )

        # 4. Módulo de Moderação (CORRIGIDO: !faxina e argumentos completos)
        embed.add_field(
            name="🛡️ Moderação (Requer Permissão)",
            value=(
                "`!faxina <num>` / (`!purgeall`): Deleta mensagens em massa.\n" # <-- CORRIGIDO
                "`!ban <membro> [motivo]`: Bane um usuário.\n"
                "`!kick <membro> [motivo]`: Expulsa um usuário.\n"
                "`!mute <membro> <tempo>`: Silencia temporariamente.\n"
                "`!warn <membro> <motivo>`: Adiciona uma advertência.\n"
                "`!warnings <membro>`: Vê o histórico de advertências."
            ),
            inline=False
        )
        
        # 5. Módulo de Tickets
        embed.add_field(
            name="🎫 Tickets e Suporte",
            value=(
                "`!ticketpanel`: Envia o painel de criação de tickets (Admin).\n"
                "`!fechar`: Fecha o ticket atual.\n"
                "`!arquivar`: Arquiva (deleta) o ticket após gerar o transcript."
            ),
            inline=False
        )
        
        # 6. Módulo de Administração (Apenas para Dono)
        embed.add_field(
            name="⚙️ Admin/Dev (Apenas para o Dono do Bot)",
            value=(
                "`!carregar <cog>` / `!descarregar <cog>`\n"
                "`!recarregar <cog>`: Gerencia os módulos do bot em tempo real."
            ),
            inline=False
        )

        embed.set_footer(text="Agradecemos por usar o Bobonic! Sempre ativo e melhorando.")
        
        await ctx.send(embed=embed)


# ==============================================================================
# ⚙️ FUNÇÃO DE SETUP
# ==============================================================================
async def setup(bot):
    await bot.add_cog(ComandosBasicos(bot))