# bot.py
import os
import asyncio
from dotenv import load_dotenv
from datetime import datetime
from aiohttp import web
import discord
from discord.ext import commands

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # pode estar vazio se não quiser IA
PORT = int(os.getenv("PORT", "10000"))

intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=commands.DefaultHelpCommand())

COGS = [
    "cogs.moderation",
    "cogs.ia",
    "cogs.tickets",
    "cogs.xp",
    "cogs.admin",
    "cogs.autoresponse"
]

# Load cogs
@bot.event
async def on_ready():
    print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Bot conectado como {bot.user} ({bot.user.id})")

async def start_webserver():
    async def handle(request):
        return web.Response(text="oBobonic rodando!")

    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Webserver rodando na porta {PORT}")

async def main():
    # load cogs
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            print(f"Cog carregada: {cog}")
        except Exception as e:
            print(f"Erro ao carregar cog {cog}: {e}")

    # start webserver (para Render detectar porta)
    asyncio.create_task(start_webserver())

    # start bot
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrompido manualmente.")
