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
import pytz  # type: ignore
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
    "instant_gaming": discord.Color.from_rgb(0, 204, 102).value,
}

GMG_URL = "https://www.greenmangaming.com/pt/sales/"
FANATICAL_URL = "https://www.fanatical.com/en/search?sort_by=discount_desc"
GAMESPLANET_URL = "https://us.gamesplanet.com/games/offers"
NUUVEM_URL = "https://www.nuuvem.com/catalog?filter%5Btype%5D=game&sort=discount_desc"
HUMBLE_URL = "https://www.humblebundle.com/store"
INSTANT_GAMING_URL = "https://www.instant-gaming.com/pt/pesquisar/?sort_by=discount_desc"
INSTANT_GAMING_AFFILIATE = "igr=arkland"


def _ig_affiliate(url: str) -> str:
    """Adiciona o parâmetro de afiliação a qualquer link do Instant Gaming."""
    if not url or "instant-gaming.com" not in url:
        return url
    sep = "&" if "?" in url else "?"
    if INSTANT_GAMING_AFFILIATE in url:
        return url
    return f"{url}{sep}{INSTANT_GAMING_AFFILIATE}" 

def ensure_data_dir() -> None:
    if not os.path.exists("data"):
        os.makedirs("data")

def load_cache() -> Dict[str, Any]:
    """Carrega cache com fallback otimizado."""
    ensure_data_dir()
    if not os.path.exists(CACHE_FILE):
        return {"sent": []}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Limpa cache muito grande na memória
            sent_list = data.get("sent", [])
            if len(sent_list) > 500:
                data["sent"] = sent_list[-500:]
            return data
    except Exception:
        return {"sent": []}

def save_cache(cache: Dict[str, Any]) -> None:
    """Salva cache de forma otimizada."""
    ensure_data_dir()
    try:
        # Limita tamanho antes de salvar
        sent_list = cache.get("sent", [])
        if len(sent_list) > 500:
            cache["sent"] = sent_list[-500:]
        
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def is_new(cache: Dict[str, Any], pid: str) -> bool:
    return pid not in cache.get("sent", [])

def mark(cache: Dict[str, Any], pid: str) -> None:
    """Marca promoção como enviada (otimizado para evitar escritas excessivas)."""
    cache.setdefault("sent", []).append(pid)
    # Limita tamanho, mas não salva toda vez (save_cache é chamado periodicamente)
    if len(cache["sent"]) > 1000:  # Limite maior em memória
        cache["sent"] = cache["sent"][-500:]  # Mantém apenas os últimos 500

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

async def fetch_text(session: aiohttp.ClientSession, url: str, timeout: int = 25, label: str = "") -> str:
    tag = f"[{label}] " if label else ""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://www.google.com/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout), allow_redirects=True) as resp:
            if resp.status == 200:
                text = await resp.text()
                print(f"[SALES] {tag}✅ {url[:60]} → {resp.status} ({len(text)} bytes)")
                return text
            print(f"[SALES] {tag}⚠️ {url[:60]} → HTTP {resp.status}")
            return ""
    except asyncio.TimeoutError:
        print(f"[SALES] {tag}⏱️ Timeout: {url[:60]}")
        return ""
    except Exception as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            try:
                try:
                    import certifi
                    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout), allow_redirects=True, ssl=ssl_ctx) as resp2:
                        if resp2.status == 200:
                            return await resp2.text()
                except Exception:
                    pass
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout), allow_redirects=True, ssl=False) as resp3:
                    if resp3.status == 200:
                        return await resp3.text()
            except Exception:
                pass
        print(f"[SALES] {tag}❌ Erro em {url[:60]}: {type(e).__name__}: {e}")
        return ""

async def fetch_via_proxy(session: aiohttp.ClientSession, url: str, timeout: int = 25) -> str:
    try:
        from urllib.parse import urlsplit
        parts = urlsplit(url)
        prox = f"https://r.jina.ai/http://{parts.netloc}{parts.path or ''}"
        if parts.query:
            prox += f"?{parts.query}"
        print(f"[SALES] 🔄 Tentando proxy Jina: {url[:60]}")
        result = await fetch_text(session, prox, timeout)
        if result:
            print(f"[SALES] ✅ Proxy funcionou para {url[:60]}")
        return result
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

async def _parse_anchors(html: str, base_url: str, store_key: str, required_path: Optional[str]) -> List[Dict[str, Any]]:
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
        a_text = a.get_text(" ", strip=True)
        search_text = (parent_text + " " + a_text).strip()
        discount = extract_discount(search_text)
        price_current, price_original = extract_prices(parent, search_text)
        if not price_current:
            price_current, price_original = extract_prices(a, a_text)
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

async def scrape_generic(session: aiohttp.ClientSession, base_url: str, store_key: str, required_path: Optional[str] = None) -> List[Dict[str, Any]]:
    html = await fetch_text(session, base_url, label=store_key)
    if not html:
        html = await fetch_via_proxy(session, base_url)
    if not html:
        return []
    results = await _parse_anchors(html, base_url, store_key, required_path)
    # Se o HTML direto não rendeu resultados (provável renderização JS), tenta proxy
    if not results:
        print(f"[SALES] 🔄 [{store_key}] HTML direto sem resultados, tentando proxy...")
        proxy_html = await fetch_via_proxy(session, base_url)
        if proxy_html and proxy_html != html:
            results = await _parse_anchors(proxy_html, base_url, store_key, required_path)
    if not results:
        print(f"[SALES] ⚠️ [{store_key}] Nenhum item encontrado após tentativas direto + proxy.")
    return results

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

def _ig_extract_page_data(html: str) -> Dict[str, Dict[str, Any]]:
    """
    Extrai preços e imagens de dados JSON embutidos no HTML do IG.
    Cobre JSON-LD (structured data), Next.js (__NEXT_DATA__) e inline JS.
    Retorna {game_id_str: {price, oldprice, image, discount}}
    """
    import json, re
    result: Dict[str, Dict[str, Any]] = {}

    def _walk(obj: Any, depth: int = 0) -> None:
        if depth > 8 or not obj:
            return
        if isinstance(obj, list):
            for it in obj:
                _walk(it, depth + 1)
        elif isinstance(obj, dict):
            raw_id = obj.get("id") or obj.get("game_id") or obj.get("product_id") or ""
            has_price    = "price" in obj or "finalprice" in obj
            has_discount = "discount" in obj or "reduction" in obj
            if raw_id and (has_price or has_discount):
                gid = str(raw_id)
                p_cur  = obj.get("price") or obj.get("finalprice") or obj.get("final_price") or 0
                p_old  = obj.get("oldprice") or obj.get("baseprice") or obj.get("rrp") or obj.get("old_price") or 0
                disc   = abs(int(obj.get("discount") or obj.get("reduction") or 0))
                img    = str(obj.get("image") or obj.get("cover") or obj.get("picture") or obj.get("img") or "")
                result[gid] = {
                    "price":    float(p_cur) if p_cur else 0.0,
                    "oldprice": float(p_old) if p_old else 0.0,
                    "discount": disc,
                    "image":    img,
                }
            else:
                for v in obj.values():
                    _walk(v, depth + 1)

    soup = BeautifulSoup(html, "html.parser")

    # 1. JSON-LD structured data — IG usa para SEO, contém offers com price
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            items_ld = []
            if isinstance(data, dict):
                t = data.get("@type", "")
                if t in ("Product", "VideoGame", "SoftwareApplication"):
                    items_ld = [data]
                elif "@graph" in data:
                    items_ld = [x for x in data["@graph"] if isinstance(x, dict)]
                elif "itemListElement" in data:
                    items_ld = [x.get("item", x) for x in data["itemListElement"] if isinstance(x, dict)]
            elif isinstance(data, list):
                items_ld = data
            for prod in items_ld:
                if not isinstance(prod, dict):
                    continue
                # Extrai URL do produto para pegar game_id
                prod_url = str(prod.get("url") or prod.get("@id") or "")
                gid_m = re.search(r"/(\d+)-comprar-", prod_url)
                if not gid_m:
                    continue
                gid = gid_m.group(1)
                offers = prod.get("offers") or {}
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                p_cur  = float(offers.get("price") or 0)
                p_old  = float(offers.get("highPrice") or offers.get("priceBeforeDiscount") or 0)
                img    = str(prod.get("image") or "")
                if isinstance(img, list):
                    img = img[0] if img else ""
                result[gid] = {"price": p_cur, "oldprice": p_old, "discount": 0, "image": img}
        except Exception:
            pass

    if result:
        return result

    # 2. Next.js __NEXT_DATA__
    nd = soup.find("script", {"id": "__NEXT_DATA__"})
    if nd and nd.string:
        try:
            _walk(json.loads(nd.string))
        except Exception:
            pass

    if result:
        return result

    # 3. Inline JS — busca arrays de objetos com price+discount
    for script in soup.find_all("script"):
        content = script.string or ""
        if len(content) < 200 or "price" not in content or "discount" not in content:
            continue
        for m in re.finditer(r'(\[{.+?}\])', content, re.DOTALL):
            try:
                obj = json.loads(m.group(1))
                _walk(obj)
                if result:
                    break
            except Exception:
                pass
        if result:
            break

    return result


def _ig_clean_name(raw: str) -> str:
    """Remove prefixos/sufixos do IG como 'comprar X - PC (Steam)'."""
    import re
    s = raw.strip()
    # Remove prefixo "comprar " (pt) / "buy " (en) / "acheter " (fr)
    s = re.sub(r"^(?:comprar|buy|acheter)\s+", "", s, flags=re.I)
    # Remove sufixo de plataforma: " - PC (Steam)", " - PC & Mac (Steam)", etc.
    s = re.sub(r"\s*[-–]\s*(?:PC|Mac|PC & Mac|Xbox|PS\d|Nintendo Switch)[^\)]*(?:\([^\)]*\))?\s*$", "", s, flags=re.I)
    # Remove sufixo "(Steam)", "(GOG)", "(Epic)" solto
    s = re.sub(r"\s*\((?:Steam|GOG|Epic|Origin|Uplay|Battle\.net)\)\s*$", "", s, flags=re.I)
    return s.strip()[:120]


def _ig_parse_card(item: Any, base: str, weekly: bool = False) -> Optional[Dict[str, Any]]:
    """Extrai dados de um card <a> do HTML do Instant Gaming via atributos data-*."""
    import re

    href = str(item.get("href", ""))
    if not href:
        return None
    link = href if href.startswith("http") else f"{base}{href}"
    link = _ig_affiliate(link)

    # ID do jogo a partir da URL: /pt/1234-comprar-nome/
    game_id_match = re.search(r"/(\d+)-comprar-", href)
    game_id = game_id_match.group(1) if game_id_match else ""

    # Nome — prioridade: data-name > alt da img > seletor CSS > title (sujo, limpa depois)
    name = str(item.get("data-name", "") or item.get("data-title", "")).strip()
    if not name:
        name_el = item.select_one(".title, .name, h2, h3, h4, [class*='title'], [class*='name']")
        if name_el:
            name = name_el.get_text(strip=True)
    if not name:
        img = item.select_one("img")
        if img:
            name = str(img.get("alt", "") or img.get("title", "")).strip()
    if not name:
        # title do <a> vem como "comprar X - PC (Steam)" — limpa
        name = _ig_clean_name(str(item.get("title", "") or item.get("aria-label", "")))
    if not name:
        raw_text = item.get_text(" ", strip=True)
        name = re.sub(r"\s*-\d+%.*", "", raw_text).strip()
    # Sempre passa pelo limpador para garantir
    name = _ig_clean_name(name)
    if len(name) < 2:
        return None

    # Desconto — data-discount, elemento .discount, ou texto do card
    discount = 0
    raw_disc = item.get("data-discount") or item.get("data-reduction") or ""
    if raw_disc:
        discount = abs(extract_discount(str(raw_disc)))
    if not discount:
        disc_el = item.select_one(".discount, [class*='discount'], [class*='reduction'], [class*='promo']")
        if disc_el:
            discount = abs(extract_discount(disc_el.get_text(strip=True)))
    if not discount:
        discount = abs(extract_discount(item.get_text(" ", strip=True)))
    if discount < 5:
        return None

    # Preços — O IG coloca o preço no <article> pai, fora do <a>.
    # Subimos para o article (ou li/div) para encontrar o .price
    _parent = item.parent
    price_scope = _parent if (_parent and getattr(_parent, "name", "") in ("article", "li", "section")) else item

    p_cur_raw  = str(item.get("data-price", "") or item.get("data-finalprice", "")).strip()
    p_old_raw  = str(item.get("data-oldprice", "") or item.get("data-baseprice", "") or item.get("data-rrp", "")).strip()

    def _fmt_price(raw: str) -> str:
        if not raw:
            return ""
        try:
            return f"€{float(raw.replace(',', '.')):.2f}"
        except Exception:
            return raw

    price_current  = _fmt_price(p_cur_raw)
    price_original = _fmt_price(p_old_raw)

    # Seletores de preço no escopo correto (article pai > information > .price)
    if not price_current:
        el = price_scope.select_one(".price, .finalprice, [class*='finalprice'], [class*='final-price'], [class*='current-price']")
        if el:
            price_current = el.get_text(strip=True).replace("\xa0", " ").strip()
    if not price_original:
        el = price_scope.select_one(".baseprice, .oldprice, [class*='oldprice'], [class*='old-price'], [class*='baseprice'], .rrp")
        if el:
            price_original = el.get_text(strip=True).replace("\xa0", " ").strip()

    # Fallback: extrai preços do texto do escopo se ainda vazio
    if not price_current:
        price_current, price_original = _parse_prices_from_text(price_scope.get_text(" ", strip=True))

    # Imagem — ignora placeholders de lazy load, usa CDN do IG com game_id
    _LAZY_PATTERNS = ("lazy.svg", "placeholder", "blank.gif", "loading", "data:image")
    image = ""
    img_el = item.select_one("img")
    if img_el:
        for attr in ("data-src", "data-lazy", "data-original", "data-ig-src", "src"):
            src = str(img_el.get(attr) or "").strip()
            if src and not any(p in src.lower() for p in _LAZY_PATTERNS):
                image = normalize_image(src, base)
                # Só reescreve dimensões em URLs do próprio IG — gaming-cdn.com
                # serve tamanhos específicos e não aceita qualquer dimensão
                if "instant-gaming.com/igr/" in image or "instant-gaming.com/images/" in image:
                    image = re.sub(r"/\d+x\d+/", "/460x215/", image)
                # Remove query string de versão (?v=...) que pode causar cache miss
                image = re.sub(r"\?v=\d+$", "", image)
                break

    # CDN do IG — /igr/{id}_460x215.jpg é o padrão real do site
    if not image and game_id:
        image = f"{base}/igr/{game_id}_460x215.jpg"

    # Steam: verifica no title do <a> que contém "(Steam)"
    title_attr = str(item.get("title", "") or item.get("aria-label", "")).lower()
    card_text = item.get_text(" ", strip=True).lower()
    steam = "steam" in title_attr or "steam" in card_text or "steam" in link.lower()

    # Dias restantes (weekly)
    days_remaining = ""
    if weekly:
        m = re.search(r"(\d+)\s*dias?\s*restantes?", card_text, re.I)
        if m:
            days_remaining = f"{m.group(1)} dia{'s' if int(m.group(1)) != 1 else ''} restante{'s' if int(m.group(1)) != 1 else ''}"

    return {
        "id": link,
        "nome": name,
        "link": link,
        "preco": price_current,
        "preco_atual": price_current,
        "preco_original": price_original,
        "loja": "instant_gaming",
        "discount": discount,
        "image": image,
        "steam": steam,
        "weekly": weekly,
        "days_remaining": days_remaining,
    }


async def fetch_instant_gaming(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """Busca top descontos do Instant Gaming via scraping HTML com data-* attributes."""
    import re as _re
    base = "https://www.instant-gaming.com"
    urls = [
        "https://www.instant-gaming.com/pt/pesquisar/?sort_by=discount_desc",
        "https://www.instant-gaming.com/pt/",
    ]

    for url in urls:
        html = await fetch_text(session, url, label="Instant Gaming")
        if not html:
            html = await fetch_via_proxy(session, url)
        if not html:
            continue

        # Extrai preços/imagens do JSON embutido (Next.js / Nuxt / inline JS)
        page_data = _ig_extract_page_data(html)
        if page_data:
            print(f"[SALES] [IG] 📦 JSON embutido: {len(page_data)} produto(s) com dados")

        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("a[href*='-comprar-']")
        if not items:
            continue

        results: List[Dict[str, Any]] = []
        for item in items:
            parsed = _ig_parse_card(item, base, weekly=False)
            if not parsed:
                continue
            # Enriquece com dados do JSON se disponível
            gid_m = _re.search(r"/(\d+)-comprar-", parsed.get("link", ""))
            if gid_m:
                gid = gid_m.group(1)
                jd = page_data.get(gid, {})
                if jd.get("price") and not parsed.get("preco_atual"):
                    parsed["preco_atual"] = f"€{jd['price']:.2f}"
                    parsed["preco"]       = parsed["preco_atual"]
                if jd.get("oldprice") and not parsed.get("preco_original"):
                    parsed["preco_original"] = f"€{jd['oldprice']:.2f}"
                if jd.get("image") and not parsed.get("image"):
                    img_url = str(jd["image"])
                    if img_url.startswith("//"):
                        img_url = f"https:{img_url}"
                    elif img_url.startswith("/"):
                        img_url = f"{base}{img_url}"
                    parsed["image"] = img_url
            results.append(parsed)

        if results:
            uniq = {r["link"]: r for r in results}
            com_preco = sum(1 for r in uniq.values() if r.get("preco_atual"))
            com_img   = sum(1 for r in uniq.values() if r.get("image"))
            print(f"[SALES] [IG] ✅ {len(uniq)} jogo(s) | preço: {com_preco} | imagem: {com_img}")
            for r in list(uniq.values())[:2]:
                print(f"[SALES] [IG] 🔍 '{r['nome']}' | preço={r.get('preco_atual','—')} | img={r.get('image') or '❌'}")
            return list(uniq.values())

    print("[SALES] [IG] ⚠️ Nenhum resultado após todas as tentativas.")
    return []


async def fetch_instant_gaming_weekly(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """Busca 'Ofertas da Semana' do Instant Gaming via scraping HTML."""
    import re
    base = "https://www.instant-gaming.com"
    html = await fetch_text(session, f"{base}/pt/", label="IG Weekly")
    if not html:
        html = await fetch_via_proxy(session, f"{base}/pt/")
    if not html:
        return []

    # Extrai preços/imagens do JSON embutido
    page_data = _ig_extract_page_data(html)
    if page_data:
        print(f"[SALES] [IG Weekly] 📦 JSON embutido: {len(page_data)} produto(s) com dados")

    soup = BeautifulSoup(html, "html.parser")

    section_container = None
    for heading in soup.find_all(["h2", "h3", "h4", "div", "section", "span"]):
        text = heading.get_text(strip=True)
        if re.search(r"ofertas da semana|deals of the week|offres de la semaine", text, re.I):
            for ancestor in [
                heading.parent,
                heading.parent.parent if heading.parent else None,
                heading.parent.parent.parent if heading.parent and heading.parent.parent else None,
            ]:
                if ancestor and ancestor.select("a[href*='-comprar-']"):
                    section_container = ancestor
                    break
            if section_container:
                break

    if not section_container:
        print("[SALES] ⚠️ [IG Weekly] Seção 'Ofertas da Semana' não encontrada.")
        return []

    items = section_container.select("a[href*='-comprar-']")
    print(f"[SALES] 🗓️ [IG Weekly] {len(items)} item(s) encontrado(s)")

    results: List[Dict[str, Any]] = []
    for item in items:
        parsed = _ig_parse_card(item, base, weekly=True)
        if not parsed:
            continue
        # Enriquece com dados do JSON se disponível
        gid_m = re.search(r"/(\d+)-comprar-", parsed.get("link", ""))
        if gid_m:
            gid = gid_m.group(1)
            jd = page_data.get(gid, {})
            if jd.get("price") and not parsed.get("preco_atual"):
                parsed["preco_atual"] = f"€{jd['price']:.2f}"
                parsed["preco"]       = parsed["preco_atual"]
            if jd.get("oldprice") and not parsed.get("preco_original"):
                parsed["preco_original"] = f"€{jd['oldprice']:.2f}"
            if jd.get("image") and not parsed.get("image"):
                img_url = str(jd["image"])
                if img_url.startswith("//"):
                    img_url = f"https:{img_url}"
                elif img_url.startswith("/"):
                    img_url = f"{base}{img_url}"
                parsed["image"] = img_url
        results.append(parsed)

    uniq = {r["link"]: r for r in results}
    print(f"[SALES] [IG Weekly] ✅ {len(uniq)} oferta(s) da semana obtida(s)")
    return list(uniq.values())


async def fetch_instant_gaming_trending(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """Busca top tendências (bestsellers) do Instant Gaming."""
    import re
    base = "https://www.instant-gaming.com"
    url = "https://www.instant-gaming.com/br/buscar/?sort_by=bestsellers_desc"
    html = await fetch_text(session, url, label="IG Trending")
    if not html:
        html = await fetch_via_proxy(session, url)
    if not html:
        return []

    page_data = _ig_extract_page_data(html)

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("a[href*='-comprar-']")
    if not items:
        print("[SALES] ⚠️ [IG Trending] Nenhum card encontrado.")
        return []

    results: List[Dict[str, Any]] = []
    for item in items:
        parsed = _ig_parse_card(item, base, weekly=False)
        if not parsed:
            continue
        parsed["trending"] = True
        gid_m = re.search(r"/(\d+)-comprar-", parsed.get("link", ""))
        if gid_m:
            gid = gid_m.group(1)
            jd = page_data.get(gid, {})
            if jd.get("price") and not parsed.get("preco_atual"):
                parsed["preco_atual"] = f"€{jd['price']:.2f}"
                parsed["preco"]       = parsed["preco_atual"]
            if jd.get("oldprice") and not parsed.get("preco_original"):
                parsed["preco_original"] = f"€{jd['oldprice']:.2f}"
            if jd.get("image") and not parsed.get("image"):
                img_url = str(jd["image"])
                if img_url.startswith("//"):
                    img_url = f"https:{img_url}"
                elif img_url.startswith("/"):
                    img_url = f"{base}{img_url}"
                parsed["image"] = img_url
        results.append(parsed)

    uniq = {r["link"]: r for r in results}
    print(f"[SALES] [IG Trending] ✅ {len(uniq)} tendência(s) obtida(s)")
    return list(uniq.values())


class PromoView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Garantir oferta", style=discord.ButtonStyle.link, url=url, emoji="🛒"))
        self.add_item(discord.ui.Button(label="Ver mais", style=discord.ButtonStyle.link, url="https://www.instant-gaming.com/?igr=arkland", emoji="🔗"))

class Sales(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = config.CANAL_PROMO_ID
        self.cache = load_cache()
        self._rates: Dict[str, float] = {"USD": 0.0, "EUR": 0.0, "GBP": 0.0}
        self._rates_ts: float = 0.0
        print(f"[SALES] 🔧 Cog inicializada. Canal de promoções: {self.channel_id}")
        self.send_daily_promos.start()  # type: ignore
        self.startup_check.start()  # type: ignore
        print("[SALES] 🚀 Tasks de startup e loop diário iniciadas.")

    async def cog_unload(self) -> None:
        for loop in (self.send_daily_promos, self.startup_check):
            try:
                loop.cancel()  # type: ignore
            except Exception:
                pass

    async def collect(self) -> List[Dict[str, Any]]:
        print("[SALES] 🔎 Coletando promoções do Instant Gaming...")
        out: List[Dict[str, Any]] = []
        timeout = aiohttp.ClientTimeout(total=35)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks: List[asyncio.Task[List[Dict[str, Any]]]] = [
                asyncio.create_task(fetch_instant_gaming(session)),
                asyncio.create_task(fetch_instant_gaming_weekly(session)),
                asyncio.create_task(fetch_instant_gaming_trending(session)),
            ]
            try:
                results: List[Union[List[Dict[str, Any]], BaseException]] = await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                results = []
        store_names = ["Instant Gaming", "IG Weekly Deals", "IG Trending"]
        for name, r in zip(store_names, results):
            if isinstance(r, list):
                print(f"[SALES]   • {name}: {len(r)} oferta(s) encontrada(s)")
                out.extend(r)
            else:
                print(f"[SALES]   • {name}: ❌ erro — {r}")
        print(f"[SALES] 📦 Total coletado: {len(out)} oferta(s)")
        return out

    async def send(self, promotions: List[Dict[str, Any]]) -> int:
        """Envia promoções filtradas e ordenadas."""
        try:
            from utils.cache import channel_cache
            channel = channel_cache.get(self.bot, self.channel_id) if channel_cache else self.bot.get_channel(self.channel_id)
        except ImportError:
            channel = self.bot.get_channel(self.channel_id)
        
        if not isinstance(channel, discord.TextChannel):
            print(f"[SALES] ❌ Canal {self.channel_id} não encontrado ou sem permissão.")
            return 0
        
        await self._ensure_rates()

        # Separa por categoria e monta ordem final:
        # 1. Todas as ofertas da semana (sem limite)
        # 2. Top 10 tendências
        weekly   = [x for x in promotions if x.get("weekly")]
        trending = [x for x in promotions if x.get("trending") and not x.get("weekly")]

        # Tendências: ordena por desconto e limita a 10
        trending.sort(key=lambda x: -int(x.get("discount", 0)))
        trending = trending[:10]

        filtered = weekly + trending

        if not filtered:
            # Fallback: melhores descontos disponíveis
            filtered = sorted(promotions, key=lambda x: -int(x.get("discount", 0)))[:20]
            print(f"[SALES] 📉 Fallback: {len(filtered)} oferta(s) por desconto")
        else:
            print(f"[SALES] ✅ {len(weekly)} semanal(is) + {len(trending)} tendência(s)")

        # Timestamp BR para o footer
        br_tz = pytz.timezone("America/Sao_Paulo")
        now_str = datetime.now(br_tz).strftime("%d/%m/%Y %H:%M")

        sent_count = 0
        for p in filtered:
            pid = p.get("id") or p.get("link") or (p.get("nome", "") + p.get("loja", ""))
            if not pid:
                continue
            if not is_new(self.cache, pid):
                continue

            nome       = p.get("nome", "Oferta")
            link       = p.get("link", "")
            preco_atual   = p.get("preco_atual", "")
            preco_original = p.get("preco_original", "")
            discount   = int(p.get("discount", 0))
            image_url  = p.get("image") or ""
            steam_flag = bool(p.get("steam"))
            is_weekly  = bool(p.get("weekly"))
            is_trending = bool(p.get("trending"))
            days_remaining = p.get("days_remaining", "")

            preco_atual_d    = await self._to_brl_str(preco_atual)
            preco_original_d = await self._to_brl_str(preco_original)

            # Cor: dourado=semana, azul=tendência, verde=padrão
            if is_weekly:
                color = discord.Color.from_rgb(255, 193, 7)
            elif is_trending:
                color = discord.Color.from_rgb(88, 101, 242)  # azul Discord
            else:
                color = discord.Color.from_rgb(0, 204, 102)

            # ── Descrição rica ──────────────────────────────────────────
            desc_lines: List[str] = []

            if discount:
                desc_lines.append(f"## 🔥 -{discount}% OFF")

            if preco_original_d and preco_atual_d:
                desc_lines.append(f"**`💸 De`**  ~~{preco_original_d}~~   **`✅ Por`**  **{preco_atual_d}**")
            elif preco_original_d:
                desc_lines.append(f"💸 Preço original: ~~{preco_original_d}~~")
            elif preco_atual_d:
                desc_lines.append(f"✅ Preço: **{preco_atual_d}**")

            desc_lines.append("")  # linha em branco

            tags: List[str] = []
            if steam_flag:
                tags.append("🎮 Steam")
            if is_weekly:
                tags.append("⭐ Oferta da Semana")
            if is_trending:
                tags.append("📈 Tendência")
            if days_remaining:
                tags.append(f"⏳ {days_remaining}")
            if tags:
                desc_lines.append("  ·  ".join(tags))

            desc_lines.append("")
            desc_lines.append("💙 *Comprando pelos botões abaixo você ajuda o servidor ARKLAND a continuar crescendo!*")

            description = "\n".join(desc_lines).strip()

            # ── Embed ───────────────────────────────────────────────────
            embed = discord.Embed(
                title=nome,
                description=description or None,
                color=color,
                url=link or None,
            )
            embed.set_author(name="🟢 Instant Gaming")
            embed.set_footer(text=f"instant-gaming.com  •  {now_str}")

            if image_url:
                embed.set_image(url=image_url)

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
        
        # Salva cache apenas uma vez ao final (otimização)
        if sent_count > 0:
            save_cache(self.cache)
            print(f"[SALES] ✅ {sent_count} promoção(ões) enviada(s) ao canal.")
        else:
            print("[SALES] ℹ️ Nenhuma promoção nova para enviar (já enviadas anteriormente ou filtradas).")
        
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

    @tasks.loop(count=1)
    async def startup_check(self) -> None:
        """Limpa o canal, reseta cache e envia promoções frescas ao iniciar."""
        try:
            print("[SALES] 🚀 Verificação de startup iniciada...")

            # Limpa o canal de promoções
            try:
                from utils.cache import channel_cache
                channel = channel_cache.get(self.bot, self.channel_id) if channel_cache else self.bot.get_channel(self.channel_id)
            except ImportError:
                channel = self.bot.get_channel(self.channel_id)

            if isinstance(channel, discord.TextChannel):
                try:
                    deleted = await channel.purge(limit=200)
                    print(f"[SALES] 🗑️ Canal limpo: {len(deleted)} mensagem(ns) removida(s)")
                except Exception as e:
                    print(f"[SALES] ⚠️ Não foi possível limpar o canal: {e}")

            # Reseta o cache para que todas as promos atuais sejam tratadas como novas
            self.cache = {"sent": []}
            save_cache(self.cache)
            print("[SALES] 🔄 Cache resetado.")

            promos = await self.collect()
            if promos:
                await self.send(promos)
            else:
                print("[SALES] ⚠️ Nenhuma promoção coletada no startup.")
        except Exception as e:
            print(f"[SALES] ❌ Erro no startup_check: {e}")

    @startup_check.before_loop
    async def before_startup(self) -> None:
        await self.bot.wait_until_ready()
        print("[SALES] ⏳ Bot pronto! Iniciando verificação de promoções...")

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
            print("[SALES] 🔄 Verificação diária de promoções iniciada...")
            promos = await self.collect()
            if promos:
                await self.send(promos)
            else:
                print("[SALES] ⚠️ Nenhuma promoção encontrada na verificação diária.")
        except Exception as e:
            print(f"[SALES] ❌ Erro na verificação diária: {e}")

    @send_daily_promos.before_loop
    async def before_daily(self) -> None:
        await self.bot.wait_until_ready()
        tz = pytz.timezone("America/Sao_Paulo")
        now = datetime.now(tz)
        # Primeira execução agendada para meia-noite do próximo dia
        next_run = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_until = (next_run - now).total_seconds()
        await asyncio.sleep(seconds_until)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Sales(bot))
