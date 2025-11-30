import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import Any, Dict, List, Optional, Union, cast
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

STORE_COLORS: Dict[str, int] = {
    "gmg": discord.Color.from_rgb(67, 160, 71).value,
    "fanatical": discord.Color.from_rgb(255, 140, 0).value,
    "gamesplanet": discord.Color.from_rgb(25, 118, 210).value,
    "nuuvem": discord.Color.from_rgb(33, 150, 243).value,
    "humble": discord.Color.from_rgb(96, 96, 96).value,
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
            c2 = re.sub(r"<!--[\s\S]*?-->", " ", c)
            c2 = norm(c2)
            if len(c2) >= 2 and c2.lower() != "icon":
                return c2[:120]
    except Exception:
        return None
    return None

def _parse_prices_from_text(text: str) -> tuple[str, str]:
    try:
        import re
        patt = r"(?:R\$|US\$|\$|€|£)\s?\d+(?:[\.,]\d{2})?"
        found = re.findall(patt, text)
        if not found:
            patt2 = r"\b\d+(?:[\.,]\d{2})\b"
            found = re.findall(patt2, text)
        def to_val(s: str) -> float:
            s2 = re.sub(r"[^0-9,\.]", "", s)
            s2 = s2.replace(".", "_").replace(",", ".").replace("_", "")
            try:
                return float(s2)
            except Exception:
                return 0.0
        uniq: List[str] = []
        for x in found:
            if x not in uniq:
                uniq.append(x)
        if not uniq:
            return "", ""
        values = sorted([(to_val(x), x) for x in uniq], key=lambda y: y[0])
        if len(values) >= 2:
            cur = values[0][1]
            orig = values[-1][1]
            return cur, orig
        return values[0][1], ""
    except Exception:
        return "", ""

def extract_prices(parent: Any, parent_text: str) -> tuple[str, str]:
    price_current = ""
    price_original = ""
    try:
        selectors_cur = [
            ".price", ".product-price", ".final-price", ".sale-price", ".current-price",
            ".price--discount", ".price-new"
        ]
        selectors_old = [
            ".rrp", ".was", ".was-price", ".old-price", ".list-price",
            ".original-price", ".price-was", ".normal-price", ".price-old"
        ]
        if parent:
            for sel in selectors_cur:
                node = parent.select_one(sel)
                if node:
                    try:
                        price_current = node.get_text(" ", strip=True)
                        if price_current:
                            break
                    except Exception:
                        pass
            for sel in selectors_old:
                node = parent.select_one(sel)
                if node:
                    try:
                        price_original = node.get_text(" ", strip=True)
                        if price_original:
                            break
                    except Exception:
                        pass
        if not price_current or not price_original:
            cur2, orig2 = _parse_prices_from_text(parent_text)
            price_current = price_current or cur2
            price_original = price_original or orig2
    except Exception:
        pass
    return price_current, price_original

def pick_image(elem: Any, parent: Any, base: str) -> str:
    img = elem.select_one("img")
    if img and (img.get("src") or img.get("data-src")):
        return normalize_image(img.get("src") or img.get("data-src"), base)
    if parent:
        img2 = parent.select_one("img")
        if img2 and (img2.get("src") or img2.get("data-src")):
            return normalize_image(img2.get("src") or img2.get("data-src"), base)
    return ""

def detect_steam(elem: Any, parent: Any, link: str) -> bool:
    try:
        import re
        texts: List[str] = []
        for key in ("aria-label", "title", "data-name"):
            v = elem.get(key)
            if isinstance(v, str) and v:
                texts.append(v)
        if parent:
            try:
                pt = parent.get_text(" ", strip=True)
                if isinstance(pt, str) and pt:
                    texts.append(pt)
            except Exception:
                pass
            try:
                cls_attr = parent.get("class")
                if isinstance(cls_attr, list) and cls_attr:
                    cls_list = cast(List[str], cls_attr)
                    if cls_list:
                        texts.append(" ".join(cls_list))
                elif isinstance(cls_attr, str) and cls_attr:
                    texts.append(cls_attr)
            except Exception:
                pass
            for sel in (".badge", ".label", ".product-platform", ".platform", ".drm", "[data-qa='drm']"):
                n = parent.select_one(sel)
                if n:
                    try:
                        nt = n.get_text(" ", strip=True)
                        if isinstance(nt, str) and nt:
                            texts.append(nt)
                    except Exception:
                        pass
                    try:
                        ncls_attr = n.get("class")
                        if isinstance(ncls_attr, list) and ncls_attr:
                            ncls_list = cast(List[str], ncls_attr)
                            if ncls_list:
                                texts.append(" ".join(ncls_list))
                        elif isinstance(ncls_attr, str) and ncls_attr:
                            texts.append(ncls_attr)
                    except Exception:
                        pass
        if "steam" in link.lower():
            return True
        blob = " ".join(texts)
        if re.search(r"steam", blob, re.I):
            return True
    except Exception:
        return False
    return False

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
                link = f"{parts.scheme}://{parts.netloc}{str(href)}"
            except Exception:
                link = str(href)
        parent = a.parent
        parent_text = parent.get_text(" ", strip=True) if parent else ""
        discount = extract_discount(parent_text)
        price_current, price_original = extract_prices(parent, parent_text)
        if discount <= 0 and not price_current:
            continue
        name = pick_name(a, parent) or "Oferta"
        image = pick_image(a, parent, base_url)
        steam = detect_steam(a, parent, link)
        results.append({
            "id": link,
            "nome": name,
            "link": link,
            "preco": price_current or "",
            "preco_atual": price_current,
            "preco_original": price_original,
            "loja": store_key,
            "discount": discount,
            "image": image,
            "steam": steam,
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
        self._rates: Dict[str, float] = {"USD": 0.0, "EUR": 0.0, "GBP": 0.0}
        self._rates_ts: float = 0.0
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
        await self._ensure_rates()
        filtered = [x for x in promotions if int(x.get("discount", 0)) >= 50]
        filtered.sort(key=lambda x: (0 if x.get("steam") else 1, -int(x.get("discount", 0))))
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
            preco_atual = p.get("preco_atual", "")
            preco_original = p.get("preco_original", "")
            discount = int(p.get("discount", 0))
            image_url = p.get("image") or ""
            steam_flag = bool(p.get("steam"))
            color_val = STORE_COLORS.get(loja)
            color = discord.Color(color_val) if isinstance(color_val, int) else discord.Color.default()
            preco_atual_d = await self._to_brl_str(preco_atual)
            preco_original_d = await self._to_brl_str(preco_original)
            preco_d = await self._to_brl_str(preco)
            if preco_original_d and preco_atual_d:
                preco_line = f"De {preco_original_d} por {preco_atual_d}"
            elif preco_atual_d:
                preco_line = preco_atual_d
            elif preco_original_d:
                preco_line = f"Preço original: {preco_original_d}"
            else:
                preco_line = preco_d

            desc = f"{preco_line}\nDesconto: {discount}%"
            if steam_flag:
                desc += "\nAtivação: Steam"
            if link:
                desc += f"\n\n[Ver oferta]({link})"

            embed = discord.Embed(
                title=f"🎮 {nome}",
                description=desc,
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

    async def _ensure_rates(self) -> None:
        try:
            now_ts = datetime.now().timestamp()
            if self._rates_ts and (now_ts - self._rates_ts) < 10800:
                return
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async def fetch_rate(base: str) -> float:
                    url = f"https://api.exchangerate.host/latest?base={base}&symbols=BRL"
                    try:
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                js = await resp.json()
                                val = js.get("rates", {}).get("BRL")
                                return float(val) if isinstance(val, (int, float)) else 0.0
                    except Exception:
                        return 0.0
                    return 0.0
                usd, eur, gbp = await asyncio.gather(
                    fetch_rate("USD"), fetch_rate("EUR"), fetch_rate("GBP")
                )
            self._rates = {"USD": usd, "EUR": eur, "GBP": gbp}
            self._rates_ts = now_ts
        except Exception:
            pass

    async def _to_brl_str(self, s: str) -> str:
        try:
            import re
            x = (s or "").strip()
            if not x:
                return ""
            cur = "BRL"
            if re.search(r"R\$", x):
                cur = "BRL"
            elif re.search(r"US\$|\$", x):
                cur = "USD"
            elif "€" in x:
                cur = "EUR"
            elif "£" in x:
                cur = "GBP"
            m = re.search(r"(\d+[\.,]?\d*)", x)
            if not m:
                return x
            raw = m.group(1)
            norm = raw.replace(".", "_").replace(",", ".").replace("_", "")
            try:
                val = float(norm)
            except Exception:
                return x
            if cur == "BRL":
                return f"R$ {self._fmt_brl(val)}"
            rate = self._rates.get(cur, 0.0)
            if rate and rate > 0:
                brl = val * rate
                return f"R$ {self._fmt_brl(brl)}"
            return x
        except Exception:
            return s

    def _fmt_brl(self, amount: float) -> str:
        try:
            s = f"{amount:,.2f}"
            s = s.replace(",", "X").replace(".", ",").replace("X", ".")
            return s
        except Exception:
            return f"{amount:.2f}"

    @commands.command(name="promo")
    async def promo(self, ctx: commands.Context[Any], *, filtro: Optional[str] = None) -> None:
        await ctx.send("🔎 Buscando promoções...")
        try:
            promos = await self.collect()
            if not promos:
                await ctx.send("⚠️ Nenhuma promoção encontrada agora.")
                return
            if isinstance(filtro, str) and filtro.strip().lower() == "steam":
                promos = [p for p in promos if bool(p.get("steam"))]
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
