# cogs/sales.py
import discord
from discord.ext import commands, tasks
import time
import json
import os
import asyncio
from typing import List, Dict, Any
import config

DATA_FILE = "data/sales_history.json"
PLATFORM_URLS = {
    "steam": "https://store.steampowered.com/search/?specials=1",
    "nuuvem": "https://www.nuuvem.com/br-pt/promo",
    "epic_games": "https://store.epicgames.com/pt-BR/browse?sortBy=currentPrice&sortDir=asc&maxPrice=50&minPrice=0&priceRange=0%2C50&category=Game&discountType=ALL"
}

def load_sales_history() -> Dict[str, Any]:
    if not os.path.exists('data'):
        os.makedirs('data')
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Histórico de vendas corrompido. Iniciando um novo.")
    return {"last_run": 0, "sales": []}

def save_sales_history(data: Dict[str, Any]):
    if not os.path.exists('data'):
        os.makedirs('data')
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

class MultiPlatformSales(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # pega o canal de promo diretamente do config
        self.canal_promo_id = config.CANAL_PROMO_ID
        self.sales_history = load_sales_history()
        self.checar_promocoes.start()
        print(f"[SALES] Cog inicializado. Canal de destino: {self.canal_promo_id}")

    def cog_unload(self):
        self.checar_promocoes.cancel()

    async def fetch_sales(self, platform: str) -> List[Dict[str, str]]:
        url = PLATFORM_URLS.get(platform)
        if not url:
            return []
        print(f"Buscando em {platform}...")
        await asyncio.sleep(2)
        if platform == "steam":
            return [
                {"title": "Deep Rock Galactic", "price": "R$ 19,99", "link": "link_drg"},
                {"title": "Hollow Knight", "price": "R$ 9,99", "link": "link_hk"},
            ]
        elif platform == "nuuvem":
            return [
                {"title": "Resident Evil 4 Remake", "price": "R$ 150,00", "link": "link_re4"},
            ]
        return []

    async def raspar_e_enviar_promocoes(self, enviar_novas: bool = True):
        all_new_sales = []
        for platform in PLATFORM_URLS:
            sales = await self.fetch_sales(platform)
            all_new_sales.extend(sales)

        if enviar_novas:
            canal = self.bot.get_channel(self.canal_promo_id)
            if canal:
                embed = discord.Embed(
                    title="🔥 Novas Ofertas de Jogos!",
                    description=f"Encontradas {len(all_new_sales)} promoções atualizadas.",
                    color=discord.Color.red()
                )
                for sale in all_new_sales:
                    embed.add_field(
                        name=f"{sale['title']} - {sale['price']}",
                        value=f"[Ver Oferta]({sale['link']})",
                        inline=False
                    )
                try:
                    await canal.send(embed=embed)
                    print(f"[SALES] {len(all_new_sales)} promoções enviadas para o canal {canal.id}.")
                except Exception as e:
                    print(f"[ERRO] Falha ao enviar promoções para o Discord: {e}")

        self.sales_history['sales'] = all_new_sales
        self.sales_history['last_run'] = int(time.time())
        save_sales_history(self.sales_history)

    @commands.command(name="rasparpromos")
    async def rasparpromos_command(self, ctx):
        await ctx.send("⌛ Iniciando verificação manual de promoções...")
        await self.raspar_e_enviar_promocoes(enviar_novas=True)
        await ctx.send("✅ Verificação de promoções concluída!")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # Tratamento básico de erros específicos do cog
        print(f"[SALES] Erro no comando: {error}")

    @tasks.loop(hours=24)
    async def checar_promocoes(self):
        await self.raspar_e_enviar_promocoes(enviar_novas=True)

    @checar_promocoes.before_loop
    async def before_checar_promocoes(self):
        await self.bot.wait_until_ready()
        print("[SALES] Tarefa agendada iniciada e aguardando a hora de execução.")

async def setup(bot):
    await bot.add_cog(MultiPlatformSales(bot))

# ============================================================
# Atualizado em: 2025-11-23 22:41:53 (Horário de Brasília)
# ============================================================
