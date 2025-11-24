# cogs/sales.py
import discord
from discord.ext import commands, tasks
import aiohttp
from bs4 import BeautifulSoup
import asyncio
import json
import os
from datetime import datetime, timedelta
import pytz
import config
from typing import List, Dict, Any

# ======================================================================
# Sales Cog — Radar Arcano de Promoções
# - Scrapes: Steam / Nuuvem / Epic (melhor esforço)
# - Envia cada promoção em embed separado
# - Inclui botão "Ver Promoção"
# - Cache persistente para evitar duplicatas
# - Agendado para rodar todo dia às 00:00 (America/Sao_Paulo)
# ======================================================================

CACHE_FILE = "data/sales_cache.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
             "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# cores por loja
COR_LOJAS = {
    "epic": discord.Color.purple(),
    "nuuvem": discord.Color.teal(),
    "steam": discord.Color.dark_blue()
}

# endpoints (padrão) - podem ser alterados conforme necessidade
STEAM_SEARCH_URL = "https://store.steampowered.com/search/?specials=1"
NUUVEM_PROMO_URL = "https://www.nuuvem.com/br-pt/promo"
EPIC_STORE_URL = "https://store.epicgames.com/pt-BR/browse?sortBy=currentPrice&sortDir=asc&discountType=ALL"

# ======================================================================
# Utilitários: cache
# ======================================================================
def ensure_data_dir():
    if not os.path.exists("data"):
        os.makedirs("data")

def load_cache() -> Dict[str, Any]:
    ensure_data_dir()
    if not os.path.exists(CACHE_FILE):
        return {"sent": []}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"sent": []}

def save_cache(cache: Dict[str, Any]):
    ensure_data_dir()
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[sales] ❌ Erro ao salvar cache: {e}")

def is_new_promo(cache: Dict[str, Any], promo_id: str) -> bool:
    return promo_id not in cache.get("sent", [])

def mark_promo_sent(cache: Dict[str, Any], promo_id: str):
    cache.setdefault("sent", []).append(promo_id)
    # mantem cache com limite (por ex. 200 entradas)
    if len(cache["sent"]) > 500:
        cache["sent"] = cache["sent"][-500:]
    save_cache(cache)

# ======================================================================
# Helpers de scraping (tenta extrair o máximo — robusto contra mudanças)
# ======================================================================

async def fetch_text(session: aiohttp.ClientSession, url: str, timeout=20) -> str:
    headers = {"User-Agent": USER_AGENT}
    try:
        async with session.get(url, headers=headers, timeout=timeout) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                print(f"[sales] ❌ {url} retornou status {resp.status}")
                return ""
    except Exception as e:
        print(f"[sales] ❌ Erro fetch {url}: {e}")
        return ""

async def fetch_steam_promos(session: aiohttp.ClientSession) -> List[Dict[str, str]]:
    """Busca promoções na Steam (página de specials)."""
    html = await fetch_text(session, STEAM_SEARCH_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []
    # Steam usa 'search_result_row' para itens
    for row in soup.select(".search_result_row"):
        try:
            title = row.get("data-ds-appid")
            # fallback para texto se data-ds-appid nao existir
            name_tag = row.select_one(".title")
            name = name_tag.text.strip() if name_tag else row.get("data-ds-appid", "Jogo Steam")
            link = row.get("href")
            # tenta pegar preço descontado
            price_elem = row.select_one(".search_price")
            price_text = price_elem.text.strip() if price_elem else ""
            # cria id unico por link
            promo_id = link or (name + price_text)
            results.append({
                "id": str(promo_id),
                "nome": name,
                "link": link,
                "preco": price_text,
                "loja": "steam"
            })
        except Exception:
            continue
    return results

async def fetch_nuuvem_promos(session: aiohttp.ClientSession) -> List[Dict[str, str]]:
    """Busca promoções na Nuuvem."""
    html = await fetch_text(session, NUUVEM_PROMO_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []

    # A página da Nuuvem costuma ter cards - tentamos alguns seletores comuns
    # Procura por links de produto
    for a in soup.select("a[href]"):
        href = a.get("href")
        if href and "/products/" in href or "nuuvem.com" in href and "/game" in href:
            try:
                name = a.get("title") or (a.text.strip()[:80])
                link = href if href.startswith("http") else f"https://www.nuuvem.com{href}"
                promo_id = link
                # tenta extrair preço ou desconto próximo ao elemento
                parent = a.parent
                price_text = ""
                if parent:
                    price_tag = parent.select_one(".price") or parent.select_one(".product-price") or parent.select_one(".value")
                    if price_tag:
                        price_text = price_tag.text.strip()
                results.append({
                    "id": promo_id,
                    "nome": name,
                    "link": link,
                    "preco": price_text,
                    "loja": "nuuvem"
                })
            except Exception:
                continue
    # Deduplicate by link
    uniq = {}
    for r in results:
        uniq[r["link"]] = r
    return list(uniq.values())[:60]

async def fetch_epic_promos(session: aiohttp.ClientSession) -> List[Dict[str, str]]:
    """Tenta buscar promoções na Epic Store (melhor esforço)."""
    html = await fetch_text(session, EPIC_STORE_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []
    # Epic tem muitos scripts - tentaremos achar links de produtos
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        # heurística: links com '/p/' ou '/product/' ou '/store/p/' costumam ser produtos
        if "/p/" in href or "/product/" in href or "/store/p/" in href:
            try:
                name = a.get("aria-label") or a.get("title") or a.text.strip()[:80]
                link = href if href.startswith("http") else f"https://www.epicgames.com{href}"
                promo_id = link
                results.append({
                    "id": promo_id,
                    "nome": name or "Jogo Epic",
                    "link": link,
                    "preco": "",
                    "loja": "epic"
                })
            except Exception:
                continue
    # Deduplicate
    uniq = {}
    for r in results:
        uniq[r["link"]] = r
    return list(uniq.values())[:60]

# ======================================================================
# View com botão "Ver Promoção"
# ======================================================================
class PromoView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__(timeout=None)
        # Botão de link
        self.add_item(discord.ui.Button(label="Ver Promoção", style=discord.ButtonStyle.link, url=url))

# ======================================================================
# Cog
# ======================================================================

class Sales(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.canal_promo_id = config.CANAL_PROMO_ID
        self.cache = load_cache()
        # inicia a tarefa diária que aguarda até meia-noite e roda a cada 24h
        self.send_daily_promos.start()

    def cog_unload(self):
        try:
            self.send_daily_promos.cancel()
        except Exception:
            pass

    # ------------------------------------------------------------
    # Função central: coleta promos de todas as lojas e envia
    # ------------------------------------------------------------
    async def collect_all_promos(self) -> List[Dict[str, str]]:
        promos = []
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # paraleliza as chamadas
            tasks_fetch = [
                fetch_steam_promos(session),
                fetch_nuuvem_promos(session),
                fetch_epic_promos(session)
            ]
            try:
                results = await asyncio.gather(*tasks_fetch, return_exceptions=True)
            except Exception as e:
                print(f"[sales] ❌ Erro ao rodar fetches: {e}")
                results = []

            for res in results:
                if isinstance(res, Exception) or not res:
                    continue
                promos.extend(res)
        return promos

    # ------------------------------------------------------------
    # Envia promoções — respeita cache para não reenviar repetidas
    # ------------------------------------------------------------
    async def send_promotions(self, promotions: List[Dict[str, str]]):
        canal = self.bot.get_channel(self.canal_promo_id)
        if not canal:
            print(f"[sales] ❌ Canal de promoções não encontrado (ID: {self.canal_promo_id})")
            return

        sent_count = 0
        for promo in promotions:
            # identifica promo unicamente por link/id/nome
            promo_id = promo.get("id") or promo.get("link") or (promo.get("nome") + promo.get("loja", ""))
            if not promo_id:
                continue

            if not is_new_promo(self.cache, promo_id):
                # já enviado antes -> pular
                continue

            nome = promo.get("nome", "Promoção")
            link = promo.get("link", "")
            loja = (promo.get("loja") or "epic").lower()
            preco = promo.get("preco", "")

            cor = COR_LOJAS.get(loja, discord.Color.default())

            embed = discord.Embed(
                title=f"🎮 {nome}",
                description=f"{preco}\n\n[Ver oferta]({link})" if link else (preco or "Promoção disponível"),
                color=cor,
                url=link if link else None
            )
            embed.set_footer(text=f"Loja: {loja.capitalize()}")

            view = PromoView(link) if link else None

            try:
                if view:
                    await canal.send(embed=embed, view=view)
                else:
                    await canal.send(embed=embed)
                mark_promo_sent(self.cache, promo_id)
                sent_count += 1
                # espera curta para evitar ratelimit
                await asyncio.sleep(0.8)
            except Exception as e:
                print(f"[sales] ❌ Falha ao enviar promoção '{nome}': {e}")
                continue

        print(f"[sales] ✅ {sent_count} novas promoções enviadas.")
        return sent_count

    # ------------------------
    # Comando manual: !promo
    # ------------------------
    @commands.command(name="promo")
    async def promo_command(self, ctx):
        """Força a checagem e envio de promoções agora."""
        await ctx.send("🔎 Buscando promoções... (isso pode levar alguns segundos)")
        try:
            promos = await self.collect_all_promos()
            if not promos:
                await ctx.send("⚠️ Nenhuma promoção encontrada no momento.")
                return
            sent = await self.send_promotions(promos)
            await ctx.send(f"✅ Processo concluído. {sent} novas promoções enviadas.")
        except Exception as e:
            await ctx.send(f"❌ Erro ao processar promoções: {e}")

    # =================================================================
    # Tarefa agendada: roda a cada 24 horas, mas espera até a próxima
    # meia-noite São Paulo antes de iniciar (sincroniza com 00:00)
    # =================================================================
    @tasks.loop(hours=24)
    async def send_daily_promos(self):
        try:
            print("[sales] ⏰ Iniciando rotina diária de promoções (00:00 America/Sao_Paulo).")
            promos = await self.collect_all_promos()
            if promos:
                await self.send_promotions(promos)
            else:
                print("[sales] ℹ️ Nenhuma promoção encontrada na rotina diária.")
        except Exception as e:
            print(f"[sales] ❌ Erro na rotina diária de promoções: {e}")

    @send_daily_promos.before_loop
    async def before_send_daily_promos(self):
        # aguarda o bot ficar pronto
        await self.bot.wait_until_ready()

        # calcula segundos até a próxima meia-noite em America/Sao_Paulo
        tz = pytz.timezone("America/Sao_Paulo")
        now = datetime.now(tz)
        # próxima meia-noite (hoje às 00:00 já passou), então pega amanhã 00:00
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_until = (tomorrow - now).total_seconds()
        print(f"[sales] ⏳ Aguardando {int(seconds_until)}s até a próxima meia-noite (São Paulo).")
        # espera até meia-noite
        await asyncio.sleep(seconds_until)

# ------------------------
# Setup (modo oficial, sem kwargs)
# ------------------------
async def setup(bot):
    await bot.add_cog(Sales(bot))
