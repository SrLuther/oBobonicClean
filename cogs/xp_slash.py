import discord
from discord import app_commands
from discord.ext import commands

class XPSystemSlash(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="xphelp", description="Explica detalhadamente como funciona o XP, ranking e premiação.")
    async def xphelp(self, interaction: discord.Interaction):
        texto = (
            "**Como funciona o XP e Ranking:**\n"
            "\n"
            "**XP por Mensagens:**\n"
            "- Cada mensagem enviada (máx. 1 por minuto) concede um valor aleatório entre **15 e 25 XP**.\n"
            "- Se enviar várias mensagens em menos de 1 minuto, só a primeira conta para XP.\n"
            "\n"
            "**XP por Voz:**\n"
            "- A cada 5 minutos, todos que estiverem em um canal de voz ganham um valor aleatório entre **30 e 60 XP**.\n"
            "- Basta estar presente no momento da varredura para receber.\n"
            "- Não precisa estar desde a varredura anterior.\n"
            "\n"
            "**Indicações (Convites):**\n"
            "- Cada indicação aprovada (quando alguém usa seu convite e é validado) vale **5.000 pontos** no ranking.\n"
            "- Indicações só contam após aprovação manual pela staff.\n"
            "- Veja seu total de indicações no painel do ranking.\n"
            "\n"
            "**Evento Rotativo:**\n"
            "- Durante eventos especiais (ex: Treasure Hunt), você pode acumular pontos participando das atividades do evento.\n"
            "- Cada ponto de evento conquistado vale **500 pontos** no ranking.\n"
            "- Quanto mais você participar e pontuar no evento, mais pontos de ranking irá ganhar.\n"
            "- Os eventos são anunciados no Discord e têm regras próprias.\n"
            "- Sua pontuação de evento aparece no ranking enquanto durar o evento.\n"
            "\n"
            "**Cálculo do Ranking:**\n"
            "- O ranking soma: XP de mensagens, XP de voz (com peso 0,3), indicações aprovadas e pontos de evento.\n"
            "- Fórmula: (nível × 100.000) + XP mensagens + (XP voz × 0,3) + indicações × 5.000 + evento × 500.\n"
            "\n"
            "**Premiação:**\n"
            "- Top 10 do ranking recebe pontos na loja do jogo todo mês.\n"
            "- Premiação entregue entre os dias 1 e 3 de cada mês.\n"
            "\n"
            "Use `/xphelp` para ver esta explicação a qualquer momento!"
        )
        await interaction.response.send_message(texto, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(XPSystemSlash(bot))
