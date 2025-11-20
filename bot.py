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

if TOKEN is None:
    raise ValueError("[ERRO] TOKEN do bot não encontrado no .env!")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Canal de logs de cogs
COG_LOG_CHANNEL_ID = 1441025115088359425
STATUS_CHANNEL_ID = 1440918150957891656

# --- Função para carregar todos os cogs automaticamente ---
async def load_cogs():
    await bot.wait_until_ready()  # Garante que o bot está logado antes de buscar o canal
    canal_log = bot.get_channel(COG_LOG_CHANNEL_ID)

    if not os.path.exists("./cogs"):
        msg = "[AVISO] Pasta 'cogs' não encontrada."
        print(msg)
        if canal_log:
            await canal_log.send(msg)
        return

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                mensagem = f"[COG] Carregado: {filename}"
                print(mensagem)
                if canal_log:
                    await canal_log.send(mensagem)
            except Exception as e:
                erro_msg = f"[ERRO] Falha ao carregar {filename}: {e}"
                print(erro_msg)
                if canal_log:
                    await canal_log.send(erro_msg)

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
    canal_status = bot.get_channel(STATUS_CHANNEL_ID)
    if canal_status:
        await canal_status.send("😎 o pai tá on!")

# --- Função principal ---
async def main():
    await start_webserver()
    await load_cogs()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
