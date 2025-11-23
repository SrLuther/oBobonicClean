# cogs/sales.py
import discord
from discord.ext import commands, tasks
import asyncio
import config
from datetime import datetime, timedelta
import pytz

# Para o exemplo, vamos usar placeholders para promoções
# Cada item é um dicionário: {'nome': str, 'link': str, 'loja': 'epic'|'nuuvem'|'steam'}
# Na prática você pode substituir por fetch de API ou scraping
EXEMPLO_PROMOS = [
    {'nome': 'Jogo A', 'link': 'https://epicgames.com/jogoA', 'loja': 'epic'},
    {'nome': 'Jogo B', 'link': 'https://nuuvem.com/jogoB', 'loja': 'nuuvem'},
    {'nome': 'Jogo C', 'link': 'https://store.steampowered.com/jogoC', 'loja': 'steam'},
]

COR_LOJAS = {
    'epic': discord.Color.purple(),
    'nuuvem': discord.Color.teal(),
    'steam': discord.Color.dark_blue()
}

class Sales(commands.Cog):
    def __init__(self, bot, canal_promo_id: int):
        self.bot = bot
        self.canal_promo_id = canal_promo_id
        self.send_daily_promos.start()  # inicia a tarefa automática

    # ------------------------
    # Função para enviar promoções
    # ------------------------
    async def send_promotions(self, promotions):
        canal = self.bot.get_channel(self.canal_promo_id)
        if not canal:
            print(f"❌ Canal de promoções não encontrado: {self.canal_promo_id}")
            return

        for promo in promotions:
            nome = promo.get('nome', 'Promoção')
            link = promo.get('link', '')
            loja = promo.get('loja', 'epic')
            cor = COR_LOJAS.get(loja, discord.Color.default())
            embed = discord.Embed(
                title=f"🎮 Promoção: {nome}",
                description=f"[Clique aqui para a promoção]({link})",
                color=cor
            )
            embed.set_footer(text=f"Loja: {loja.capitalize()}")
            try:
                await canal.send(embed=embed)
            except Exception as e:
                print(f"❌ Erro ao enviar embed da promoção '{nome}': {e}")

    # ------------------------
    # Comando manual
    # ------------------------
    @commands.command(name="promo")
    async def promo(self, ctx):
        """Envia as promoções atuais."""
        await self.send_promotions(EXEMPLO_PROMOS)
        await ctx.send(f"✅ {len(EXEMPLO_PROMOS)} promoções enviadas!")

    # ------------------------
    # Tarefa automática diária (00h horário de Brasília)
    # ------------------------
    @tasks.loop(minutes=1)
    async def send_daily_promos(self):
        tz = pytz.timezone("America/Sao_Paulo")
        agora = datetime.now(tz)
        # verifica se é meia-noite exata
        if agora.hour == 0 and agora.minute == 0:
            print("⏰ Enviando promoções diárias automáticas...")
            await self.send_promotions(EXEMPLO_PROMOS)

    @send_daily_promos.before_loop
    async def before_send_daily_promos(self):
        await self.bot.wait_until_ready()
        print("✅ Tarefa automática de promoções iniciada, aguardando 00h...")

# ------------------------
# Setup do Cog
# ------------------------
async def setup(bot, **kwargs):
    canal_promo_id = kwargs.get("canal_promo_id")
    if canal_promo_id is None:
        print("❌ ERRO: 'canal_promo_id' não fornecido para Sales Cog.")
        return
    await bot.add_cog(Sales(bot, canal_promo_id=canal_promo_id))
