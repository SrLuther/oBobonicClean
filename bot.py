import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from aiohttp import web

# --- Carrega .env ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", 10000))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Função para enviar log de cog para o Discord ---
async def log_cog_carregado(cog_name):
    canal_log = bot.get_channel(1441025115088359425)  # Canal de logs
    if canal_log:
        await canal_log.send(f"[COG LOG] Cog carregado: {cog_name}")

# --- Função para carregar todos os cogs automaticamente ---
async def load_cogs():
    if not os.path.exists("./cogs"):
        print("[AVISO] Pasta 'cogs' não encontrada.")
        return

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            cog_name = filename[:-3]
            try:
                await bot.load_extension(f"cogs.{cog_name}")
                print(f"[COG] Carregado: {filename}")
                await log_cog_carregado(cog_name)  # Envia log para Discord
            except Exception as e:
                print(f"[ERRO] Falha ao carregar {filename}: {e}")

# --- Keep-alive para Render ---
async def start_webserver():
    async def handler(request):
        return web.Response(text="Bot rodando normalmente.")

    app = web.Application()
    app.router.add_get("/", handler)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    print(f"[WEB] Servidor iniciado na porta {PORT}")

# --- Evento on_ready ---
@bot.event
async def on_ready():
    print(f"🔥 Bot logado como {bot.user} | ID: {bot.user.id}")

    # Mensagem de status na sala específica
    canal_status = bot.get_channel(1440918150957891656)
    if canal_status:
        await canal_status.send("😎 o pai tá on!")

# --- Função principal ---
async def main():
    await load_cogs()
    await start_webserver()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
