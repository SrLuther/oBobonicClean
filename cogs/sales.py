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
from typing import List, Dict, Any, Optional, cast

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

async def fetch_text(session: aiohttp.ClientSession, url: str, timeout: int = 20) -> str:
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

def extract_discount(text: str) -> int:
    try:
        import re
        m = re.search(r"(-?\d+)\s*%", text)
        if not m:
            return 0
        val = int(m.group(1))
        return abs(val)
    except Exception:
        return 0

def pick_image_url(elem: Any) -> Optional[str]:
    try:
        # tenta achar <img> direto
        img: Any = elem.select_one("img")
        if img and (img.get("src") or img.get("data-src")):
            return img.get("src") or img.get("data-src")
        # procura em ancestrais próximos
        parent: Any = elem.parent
        for _ in range(3):
            if not parent:
                break
            img = parent.select_one("img")
            if img and (img.get("src") or img.get("data-src")):
                return img.get("src") or img.get("data-src")
            parent = parent.parent
    except Exception:
        return None
    return None

async def fetch_steam_promos(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """Busca promoções na Steam (página de specials)."""
    html = await fetch_text(session, STEAM_SEARCH_URL)
    if not html:
        return []

    soup: Any = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, Any]] = []
    # Steam usa 'search_result_row' para itens
    rows: Any = soup.select(".search_result_row")
    for row in rows:
        try:
            # fallback para texto se data-ds-appid nao existir
            name_tag: Any = row.select_one(".title")
            name = name_tag.text.strip() if name_tag else row.get("data-ds-appid", "Jogo Steam")
            link: Any = row.get("href")
            # tenta pegar preço descontado
            price_elem: Any = row.select_one(".search_price")
            price_text = price_elem.text.strip() if price_elem else ""
            # cria id unico por link
            promo_id = link or (name + price_text)
            # desconto
            disc_elem: Any = row.select_one(".search_discount") or row.select_one(".search_discount span")
            discount = extract_discount(disc_elem.text.strip() if disc_elem else "")
            # imagem
            image = pick_image_url(row)
            results.append({
                "id": str(promo_id),
                "nome": name,
                "link": link,
                "preco": price_text,
                "loja": "steam",
                "discount": discount,
                "image": image or ""
            })
        except Exception:
            continue
    return results

async def fetch_nuuvem_promos(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """Busca promoções na Nuuvem."""
    html = await fetch_text(session, NUUVEM_PROMO_URL)
    if not html:
        return []

    soup: Any = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, Any]] = []

    # A página da Nuuvem costuma ter cards - tentamos alguns seletores comuns
    # Procura por links de produto
    aitems: Any = soup.select("a[href]")
    for a in aitems:
        href: Any = a.get("href")
        if href and "/products/" in href or "nuuvem.com" in href and "/game" in href:
            try:
                name: Any = a.get("title") or (a.text.strip()[:80])
                link: Any = href if str(href).startswith("http") else f"https://www.nuuvem.com{href}"
                promo_id = link
                # tenta extrair preço ou desconto próximo ao elemento
                parent: Any = a.parent
                price_text = ""
                if parent:
                    price_tag: Any = parent.select_one(".price") or parent.select_one(".product-price") or parent.select_one(".value")
                    if price_tag:
                        price_text = price_tag.text.strip()
                # desconto
                disc_src: Any = ""
                if parent:
                    disc_tag: Any = parent.select_one(".discount") or parent.select_one(".discount-tag") or parent.select_one(".badge-discount")
                    disc_src = disc_tag.text.strip() if disc_tag else price_text
                discount = extract_discount(str(disc_src))
                # imagem
                image = pick_image_url(a) or (parent and pick_image_url(parent))
                if image and image.startswith("//"):
                    image = f"https:{image}"
                if image and image.startswith("/"):
                    image = f"https://www.nuuvem.com{image}"
                results.append({
                    "id": promo_id,
                    "nome": name,
                    "link": link,
                    "preco": price_text,
                    "loja": "nuuvem",
                    "discount": discount,
                    "image": image or ""
                })
            except Exception:
                continue
    # Deduplicate by link
    uniq: Dict[str, Dict[str, Any]] = {}
    for r in results:
        uniq[r["link"]] = r
    return list(uniq.values())[:60]

async def fetch_epic_promos(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """Tenta buscar promoções na Epic Store (melhor esforço)."""
    html = await fetch_text(session, EPIC_STORE_URL)
    if not html:
        return []

    soup: Any = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, Any]] = []
    # Epic tem muitos scripts - tentaremos achar links de produtos
    aitems: Any = soup.select("a[href]")
    for a in aitems:
        href = a.get("href")
        if not href:
            continue
        # heurística: links com '/p/' ou '/product/' ou '/store/p/' costumam ser produtos
        if "/p/" in href or "/product/" in href or "/store/p/" in href:
            try:
                name: Any = a.get("aria-label") or a.get("title") or a.text.strip()[:80]
                link: Any = href if str(href).startswith("http") else f"https://www.epicgames.com{href}"
                promo_id = link
                # tenta pegar desconto próximo
                parent: Any = a.parent
                disc_src: Any = ""
                if parent:
                    disc_tag: Any = parent.select_one(".discount") or parent.select_one(".PriceSaleBadge") or parent.select_one(".sale")
                    disc_src = disc_tag.text.strip() if disc_tag else ""
                discount = extract_discount(str(disc_src))
                # imagem
                image = pick_image_url(a) or (parent and pick_image_url(parent))
                results.append({
                    "id": promo_id,
                    "nome": name or "Jogo Epic",
                    "link": link,
                    "preco": "",
                    "loja": "epic",
                    "discount": discount,
                    "image": image or ""
                })
            except Exception:
                continue
    # Deduplicate
    uniq: Dict[str, Dict[str, Any]] = {}
    for r in results:
        uniq[r["link"]] = r
    list_values: List[Dict[str, Any]] = list(uniq.values())
    return list_values[:60]

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
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.canal_promo_id = config.CANAL_PROMO_ID
        self.cache = load_cache()
        # inicia a tarefa diária que aguarda até meia-noite e roda a cada 24h
        loop = cast(tasks.Loop[Any], self.send_daily_promos)
        loop.start()

    async def cog_unload(self) -> None:
        try:
            loop = cast(tasks.Loop[Any], self.send_daily_promos)
            loop.cancel()
        except Exception:
            pass

    # ------------------------------------------------------------
    # Função central: coleta promos de todas as lojas e envia
    # ------------------------------------------------------------
    async def collect_all_promos(self) -> List[Dict[str, Any]]:
        promos: List[Dict[str, Any]] = []
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # paraleliza as chamadas
            tasks_fetch = [
                fetch_steam_promos(session),
                fetch_nuuvem_promos(session),
                fetch_epic_promos(session)
            ]
            try:
                results: List[Any] = await asyncio.gather(*tasks_fetch, return_exceptions=True)
            except Exception as e:
                print(f"[sales] ❌ Erro ao rodar fetches: {e}")
                results = []

            for res in results:
                if isinstance(res, Exception) or not res:
                    continue
                promos.extend(cast(List[Dict[str, Any]], res))
        return promos

    # ------------------------------------------------------------
    # Envia promoções — respeita cache para não reenviar repetidas
    # ------------------------------------------------------------
    async def send_promotions(self, promotions: List[Dict[str, Any]]):
        canal: Optional[discord.TextChannel] = self.bot.get_channel(self.canal_promo_id)  # type: ignore[assignment]
        if not isinstance(canal, discord.TextChannel):
            print(f"[sales] ❌ Canal de promoções não encontrado (ID: {self.canal_promo_id})")
            return

        # agrupa por loja e filtra desconto >= 50; pega top-10 por loja
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for p in promotions:
            loja = (p.get("loja") or "").lower()
            grouped.setdefault(loja, []).append(p)

        filtered: List[Dict[str, Any]] = []
        for loja, items in grouped.items():
            with_disc = [x for x in items if int(x.get("discount", 0)) >= 50]
            with_disc.sort(key=lambda x: int(x.get("discount", 0)), reverse=True)
            filtered.extend(with_disc[:10])

        sent_count = 0
        for promo in filtered:
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
            discount = int(promo.get("discount", 0))
            image_url = promo.get("image") or ""

            cor = COR_LOJAS.get(loja, discord.Color.default())

            embed = discord.Embed(
                title=f"🎮 {nome}",
                description=f"{preco}\nDesconto: {discount}%\n\n[Ver oferta]({link})" if link else (preco or f"Desconto: {discount}%"),
                color=cor,
                url=link if link else None
            )
            embed.set_footer(text=f"Loja: {loja.capitalize()}")
            if image_url:
                embed.set_thumbnail(url=image_url)

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
    async def promo_command(self, ctx: commands.Context[Any]):
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

    @cast(tasks.Loop[Any], send_daily_promos).before_loop
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
async def setup(bot: commands.Bot):
    await bot.add_cog(Sales(bot))
