# cogs/sales.py
import discord
from discord.ext import commands, tasks
import datetime
import time
import json
import os
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import asyncio 

# Define o nome do arquivo para persistência de dados
DATA_FILE = "data/sales_history.json"
# URLs das plataformas (simplificadas para o exemplo)
PLATFORM_URLS = {
    "steam": "https://store.steampowered.com/search/?specials=1",
    "nuuvem": "https://www.nuuvem.com/br-pt/promo",
    "epic_games": "https://store.epicgames.com/pt-BR/browse?sortBy=currentPrice&sortDir=asc&maxPrice=50&minPrice=0&priceRange=0%2C50&category=Game&discountType=ALL"
}

def load_sales_history() -> Dict[str, Any]:
    """Carrega o histórico de vendas de um arquivo JSON."""
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
    """Salva o histórico de vendas no arquivo JSON."""
    if not os.path.exists('data'):
        os.makedirs('data')
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==============================================================================
# CLASSE PRINCIPAL DO COG
# ==============================================================================

class MultiPlatformSales(commands.Cog):
    
    def __init__(self, bot, canal_promo_id: int):
        self.bot = bot
        self.canal_promo_id = canal_promo_id 
        self.sales_history = load_sales_history()
        self.checar_promocoes.start() 
        print(f"[SALES] Cog inicializado. Canal de destino: {self.canal_promo_id}")
        
    def cog_unload(self):
        self.checar_promocoes.cancel()

    # --- LÓGICA DE SCRAPING (Simulado) ---
    async def fetch_sales(self, platform: str) -> List[Dict[str, str]]:
        """Função simulada para buscar promoções de uma plataforma."""
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
        """Executa o scraping, compara e envia as novas promoções."""
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


    # --- TAREFA AGENDADA ---
    @tasks.loop(hours=24) 
    async def checar_promocoes(self):
        await self.raspar_e_enviar_promocoes(enviar_novas=True)
        
    @checar_promocoes.before_loop
    async def before_checar_promocoes(self):
        await self.bot.wait_until_ready()
        print("[SALES] Tarefa agendada iniciada e aguardando a hora de execução.")

    # --- COMANDO MANUAL ---
    @commands.command(name="rasparpromos")
    async def rasparpromos_command(self, ctx):
        """Força a verificação e envio imediato de promoções."""
        await ctx.send("⌛ Iniciando verificação manual de promoções...")
        await self.raspar_e_enviar_promocoes(enviar_novas=True)
        await ctx.send("✅ Verificação de promoções concluída!")

# ==============================================================================
# SETUP DO COG
# ==============================================================================

# ✅ CORREÇÃO: A função setup deve aceitar **kwargs para evitar o TypeError
async def setup(bot, **kwargs): 
    if 'canal_promo_id' in kwargs:
        await bot.add_cog(MultiPlatformSales(bot, canal_promo_id=kwargs['canal_promo_id']))
    else:
        print("❌ ERRO: 'canal_promo_id' não foi fornecido para o cog sales.py.")