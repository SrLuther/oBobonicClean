import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import Any, Dict, List, Optional, Union
import json
import os
import ssl
from datetime import datetime, timedelta
import pytz
import config

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

CACHE_FILE = "data/sales_cache.json"

STORE_COLORS: Dict[str, discord.Color] = {
    "gmg": discord.Color.green(),
    "fanatical": discord.Color.dark_orange(),
    "gamesplanet": discord.Color.dark_blue(),
    "nuuvem": discord.Color.blue(),
    "humble": discord.Color.dark_gray(),
}

GMG_URL = "https://www.greenmangaming.com/pt/sales/"
FANATICAL_URL = "https://www.fanatical.com/en/search?sort_by=discount_desc"
GAMESPLANET_URL = "https://us.gamesplanet.com/games/offers"
NUUVEM_URL = "https://www.nuuvem.com/catalog?filter%5Btype%5D=game&sort=discount_desc"
HUMBLE_URL = "https://www.humblebundle.com/store" 

def ensure_data_dir() -> None:
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

def save_cache(cache: Dict[str, Any]) -> None:
    ensure_data_dir()
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def is_new(cache: Dict[str, Any], pid: str) -> bool:
    return pid not in cache.get("sent", [])

def mark(cache: Dict[str, Any], pid: str) -> None:
    cache.setdefault("sent", []).append(pid)
    if len(cache["sent"]) > 500:
        cache["sent"] = cache["sent"][-500:]
    save_cache(cache)

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

async def fetch_text(session: aiohttp.ClientSession, url: str, timeout: int = 25) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
    }
    try:
        async with session.get(url, headers=headers, timeout=timeout, allow_redirects=True) as resp:
            if resp.status == 200:
                return await resp.text()
            return ""
    except Exception as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            try:
                try:
                    import certifi
                    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
                    async with session.get(url, headers=headers, timeout=timeout, allow_redirects=True, ssl=ssl_ctx) as resp2:
                        if resp2.status == 200:
                            return await resp2.text()
                except Exception:
                    pass
                async with session.get(url, headers=headers, timeout=timeout, allow_redirects=True, ssl=False) as resp3:
                    if resp3.status == 200:
                        return await resp3.text()
            except Exception:
                return ""
        return ""

async def fetch_via_proxy(session: aiohttp.ClientSession, url: str, timeout: int = 25) -> str:
    try:
        from urllib.parse import urlsplit
        parts = urlsplit(url)
        prox = f"https://r.jina.ai/http://{parts.netloc}{parts.path or ''}"
        if parts.query:
            prox += f"?{parts.query}"
        return await fetch_text(session, prox, timeout)
    except Exception:
        return ""

def normalize_image(src: Optional[str], base: str) -> str:
    if not src:
        return ""
    if src.startswith("//"):
        return f"https:{src}"
    if src.startswith("/"):
        return base.rstrip("/") + src
    return src

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
        img = elem.select_one("img")
        if img:
            alt = img.get("alt")
            if isinstance(alt, str) and alt:
                candidates.append(alt)
        if parent:
            for sel in (".product-title", ".product-name", "[data-qa='product-card-title']", ".name", "h3", "h2", "h4", ".title"):
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
            c2 = norm(c)
            if len(c2) >= 2:
                return c2[:120]
    except Exception:
        return None
    return None

def pick_image(elem: Any, parent: Any, base: str) -> str:
    img = elem.select_one("img")
    if img and (img.get("src") or img.get("data-src")):
        return normalize_image(img.get("src") or img.get("data-src"), base)
    if parent:
        img2 = parent.select_one("img")
        if img2 and (img2.get("src") or img2.get("data-src")):
            return normalize_image(img2.get("src") or img2.get("data-src"), base)
    return ""

async def scrape_generic(session: aiohttp.ClientSession, base_url: str, store_key: str, required_path: Optional[str] = None) -> List[Dict[str, Any]]:
    html = await fetch_text(session, base_url)
    if not html:
        html = await fetch_via_proxy(session, base_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, Any]] = []
    anchors = soup.select("a[href]")
    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        if required_path and required_path not in str(href):
            continue
        if str(href).startswith("http"):
            link = str(href)
        else:
            try:
                from urllib.parse import urlsplit
                parts = urlsplit(base_url)
                link = f"{parts.scheme}://{parts.netloc}{href}"
            except Exception:
                link = href
        parent = a.parent
        parent_text = parent.get_text(" ", strip=True) if parent else ""
        discount = extract_discount(parent_text)
        price_text = ""
        if parent:
            pt = parent.select_one(".price") or parent.select_one(".product-price") or parent.select_one(".final-price")
            if pt:
                try:
                    price_text = pt.get_text(" ", strip=True)
                except Exception:
                    price_text = ""
        if discount <= 0 and not price_text:
            continue
        name = pick_name(a, parent) or "Oferta"
        image = pick_image(a, parent, base_url)
        results.append({
            "id": link,
            "nome": name,
            "link": link,
            "preco": price_text,
            "loja": store_key,
            "discount": discount,
            "image": image,
        })
    uniq: Dict[str, Dict[str, Any]] = {}
    for r in results:
        uniq[r["link"]] = r
    return list(uniq.values())

async def fetch_gmg(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    return await scrape_generic(session, GMG_URL, "gmg", required_path="/pt/")

async def fetch_fanatical(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    return await scrape_generic(session, FANATICAL_URL, "fanatical", required_path="/en/")

async def fetch_gamesplanet(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    return await scrape_generic(session, GAMESPLANET_URL, "gamesplanet", required_path="/game/")

async def fetch_nuuvem(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    return await scrape_generic(session, NUUVEM_URL, "nuuvem")

async def fetch_humble(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    return await scrape_generic(session, HUMBLE_URL, "humble")

class PromoView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Ver Promoção", style=discord.ButtonStyle.link, url=url))

class Sales(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = config.CANAL_PROMO_ID
        self.cache = load_cache()
        self.send_daily_promos.start()

    async def cog_unload(self) -> None:
        try:
            self.send_daily_promos.cancel()
        except Exception:
            pass

    async def collect(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        timeout = aiohttp.ClientTimeout(total=35)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks: List[asyncio.Task[List[Dict[str, Any]]]] = [
                asyncio.create_task(fetch_gmg(session)),
                asyncio.create_task(fetch_fanatical(session)),
                asyncio.create_task(fetch_gamesplanet(session)),
                asyncio.create_task(fetch_nuuvem(session)),
                asyncio.create_task(fetch_humble(session)),
            ]
            try:
                results: List[Union[List[Dict[str, Any]], BaseException]] = await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                results = []
        for r in results:
            if isinstance(r, list):
                out.extend(r)
        return out

    async def send(self, promotions: List[Dict[str, Any]]) -> int:
        channel = self.bot.get_channel(self.channel_id)
        if not isinstance(channel, discord.TextChannel):
            return 0
        filtered = [x for x in promotions if int(x.get("discount", 0)) >= 50]
        filtered.sort(key=lambda x: int(x.get("discount", 0)), reverse=True)
        filtered = filtered[:20]
        sent_count = 0
        for p in filtered:
            pid = p.get("id") or p.get("link") or (p.get("nome", "") + p.get("loja", ""))
            if not pid:
                continue
            if not is_new(self.cache, pid):
                continue
            nome = p.get("nome", "Oferta")
            link = p.get("link", "")
            loja = (p.get("loja") or "").lower()
            preco = p.get("preco", "")
            discount = int(p.get("discount", 0))
            image_url = p.get("image") or ""
            color = STORE_COLORS.get(loja, discord.Color.default())
            embed = discord.Embed(
                title=f"🎮 {nome}",
                description=(f"{preco}\nDesconto: {discount}%\n\n[Ver oferta]({link})" if link else (preco or f"Desconto: {discount}%")),
                color=color,
                url=link or None,
            )
            embed.set_footer(text=f"Loja: {loja.capitalize()}")
            if image_url:
                embed.set_thumbnail(url=image_url)
            view = PromoView(link) if link else None
            try:
                if view:
                    await channel.send(embed=embed, view=view)
                else:
                    await channel.send(embed=embed)
                mark(self.cache, pid)
                sent_count += 1
                await asyncio.sleep(0.8)
            except Exception:
                continue
        return sent_count

    @commands.command(name="promo")
    async def promo(self, ctx: commands.Context[Any]) -> None:
        await ctx.send("🔎 Buscando promoções...")
        try:
            promos = await self.collect()
            if not promos:
                await ctx.send("⚠️ Nenhuma promoção encontrada agora.")
                return
            sent = await self.send(promos)
            await ctx.send(f"✅ {sent} promoções enviadas.")
        except Exception as e:
            await ctx.send(f"❌ Erro: {e}")

    @tasks.loop(hours=24)
    async def send_daily_promos(self) -> None:
        try:
            promos = await self.collect()
            if promos:
                await self.send(promos)
        except Exception:
            pass

    @send_daily_promos.before_loop
    async def before_daily(self) -> None:
        await self.bot.wait_until_ready()
        tz = pytz.timezone("America/Sao_Paulo")
        now = datetime.now(tz)
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_until = (tomorrow - now).total_seconds()
        await asyncio.sleep(seconds_until)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Sales(bot))
