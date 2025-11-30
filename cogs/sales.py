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
import ssl
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
    "gmg": discord.Color.green()
}

DEBUG_PROMOS = getattr(config, "DEBUG_PROMOS", False)

# endpoints de referência (apenas GMG)
GMG_BASE_URL = "https://www.greenmangaming.com"
GMG_HOME_PT = "https://www.greenmangaming.com/pt/sales/"

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
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
        "DNT": "1"
    }
    try:
        async with session.get(url, headers=headers, timeout=timeout, allow_redirects=True) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                print(f"[sales] ❌ {url} retornou status {resp.status}")
                return ""
    except Exception as e:
        print(f"[sales] ❌ Erro fetch {url}: {e}")
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            try:
                try:
                    import certifi
                    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
                    async with session.get(url, headers=headers, timeout=timeout, allow_redirects=True, ssl=ssl_ctx) as resp:
                        if resp.status == 200:
                            return await resp.text()
                        else:
                            print(f"[sales] ❌ {url} retornou status {resp.status} (certifi)")
                except Exception:
                    pass
                async with session.get(url, headers=headers, timeout=timeout, allow_redirects=True, ssl=False) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    else:
                        print(f"[sales] ❌ {url} retornou status {resp.status} (ssl=False)")
                        return ""
            except Exception as e2:
                print(f"[sales] ❌ Erro fetch {url} com ssl=False: {e2}")
        return ""

async def fetch_text_cf(session: aiohttp.ClientSession, url: str, timeout: int = 20) -> str:
    base = await fetch_text(session, url, timeout)
    if base:
        return base
    try:
        from urllib.parse import urlsplit
        parts = urlsplit(url)
        proxy_url = f"https://r.jina.ai/http://{parts.netloc}{parts.path or ''}"
        if parts.query:
            proxy_url += f"?{parts.query}"
        proxy_html = await fetch_text(session, proxy_url, timeout)
        if proxy_html:
            return proxy_html
    except Exception:
        pass
    def run_sync_cf() -> str:
        try:
            import importlib
            cs = importlib.import_module("cloudscraper")
            scraper: Any = cs.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "mobile": False}
            )
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://www.google.com/",
                "sec-ch-ua": '"Chromium";v="120", "Google Chrome";v="120", "Not?A_Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "navigate",
                "sec-fetch-user": "?1",
                "sec-fetch-dest": "document",
            }
            resp = scraper.get(url, headers=headers, timeout=timeout, verify=False)
            if getattr(resp, "status_code", None) == 200:
                return resp.text
            return ""
        except Exception:
            return ""
    try:
        return await asyncio.to_thread(run_sync_cf)
    except Exception:
        pass
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

def pick_name(elem: Any, parent: Any) -> Optional[str]:
    try:
        import re
        def norm(s: str) -> str:
            return re.sub(r"\s+", " ", s).strip()
        candidates: List[str] = []
        for key in ("aria-label", "title", "data-name"):
            v = elem.get(key)
            if isinstance(v, str) and v:
                candidates.append(v)
        img: Any = elem.select_one("img")
        if img:
            alt = img.get("alt")
            if isinstance(alt, str) and alt:
                candidates.append(alt)
        if parent:
            for sel in ("[data-qa='product-card-title']", ".product-title", ".product-name", ".name", "h3", "h2", "h4", ".title"):
                t = parent.select_one(sel)
                if t:
                    tt = t.get_text(" ", strip=True)
                    if isinstance(tt, str) and tt:
                        candidates.append(tt)
        try:
            txt = " ".join(list(elem.stripped_strings))
            if txt:
                candidates.append(txt)
        except Exception:
            pass
        for c in candidates:
            c2 = re.sub(r"<!--.*?-->", " ", c)
            c2 = norm(c2)
            if len(c2) >= 2:
                return c2[:120]
    except Exception:
        return None
    return None

async def fetch_steam_promos(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    return []

async def fetch_nuuvem_promos(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    return []

async def fetch_epic_promos(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    return []

async def fetch_ggdeals_promos(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    return []

async def fetch_gmg_promos(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    html = await fetch_text_cf(session, GMG_HOME_PT)
    if not html:
        return []
    soup: Any = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, Any]] = []
    aitems: Any = soup.select("a[href]")
    for a in aitems:
        href: Any = a.get("href")
        if not href:
            continue
        if "/pt/" not in href:
            continue
        if str(href).rstrip("/") == "/pt/sales" or str(href).endswith("/pt/sales/"):
            continue
        try:
            link: Any = href if str(href).startswith("http") else f"{GMG_BASE_URL}{href}"
            parent: Any = a.parent
            price_text: Any = ""
            disc_src: Any = ""
            if parent:
                txt: Any = parent.get_text(" ", strip=True)
                disc_src = txt
                price_tag: Any = parent.select_one(".price") or parent.select_one(".product-price")
                if price_tag:
                    price_text = price_tag.text.strip()
            discount = extract_discount(str(disc_src))
            image = pick_image_url(a) or (parent and pick_image_url(parent))
            if image:
                if image.startswith("//"):
                    image = f"https:{image}"
                elif image.startswith("/"):
                    image = f"{GMG_BASE_URL}{image}"
            name = pick_name(a, parent)
            if not discount and not price_text:
                continue
            if not name:
                continue
            results.append({
                "id": link,
                "nome": name or "Oferta GMG",
                "link": link,
                "preco": str(price_text),
                "loja": "gmg",
                "discount": discount,
                "image": image or ""
            })
        except Exception:
            continue
    uniq: Dict[str, Dict[str, Any]] = {}
    for r in results:
        uniq[r["link"]] = r
    return list(uniq.values())[:200]

async def fetch_itad_promos(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    return []

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
            tasks_fetch: List[Any] = [
                fetch_gmg_promos(session)
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

        filtered: List[Dict[str, Any]] = [x for x in promotions if int(x.get("discount", 0)) >= 50]
        filtered.sort(key=lambda x: int(x.get("discount", 0)), reverse=True)
        filtered = filtered[:20]

        if DEBUG_PROMOS:
            cnt_all = len(promotions)
            cnt_50 = len(filtered)
            print(f"[sales] debug total={cnt_all} ge50={cnt_50}")

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
