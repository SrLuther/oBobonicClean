import asyncio
import aiohttp
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from cogs.sales import fetch_gmg_promos

async def main():
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        promos = await fetch_gmg_promos(session)
        print("total coletado:", len(promos))
        promos = [p for p in promos if int(p.get("discount", 0)) >= 50]
        print("após filtro >=50%:", len(promos))
        promos.sort(key=lambda x: int(x.get("discount", 0)), reverse=True)
        for p in promos[:20]:
            print("{}% | {} | {} | img={}".format(
                p.get("discount"),
                (p.get("nome") or "")[:80],
                p.get("link"),
                bool(p.get("image"))
            ))

if __name__ == "__main__":
    asyncio.run(main())
