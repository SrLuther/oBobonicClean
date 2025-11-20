import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from aiohttp import web

# Carrega .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Carregar todos os cogs automaticamente
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"[COG] Carregado: {filename}")
            except Exception as e:
                print(f"[ERRO] Falha ao carregar {filename}: {e}")

# Servidor Keep-Alive para Render
async def start_webserver():
    async def handler(request):
        return web.Response(text="Bot rodando normalmente.")

    app = web.Application()
    app.router.add_get("/", handler)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
    await site.start()

@bot.event
async def on_ready():
    print(f"🔥 Bot logado como {bot.user} | ID: {bot.user.id}")

async def main():
    await load_cogs()
    await start_webserver()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
