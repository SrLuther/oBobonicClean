import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

# --- Carrega .env ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN is None:
    raise ValueError("[ERRO] TOKEN do bot não encontrado no .env! Verifique se o arquivo existe e está na mesma pasta do bot.py")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Função para carregar todos os cogs automaticamente ---
async def load_cogs():
    if not os.path.exists("./cogs"):
        print("[AVISO] Pasta 'cogs' não encontrada.")
        return

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"[COG] Carregado: {filename}")
            except Exception as e:
                print(f"[ERRO] Falha ao carregar {filename}: {e}")


# --- Evento on_ready ---
@bot.event
async def on_ready():
    print(f"🔥 Bot logado como {bot.user} | ID: {bot.user.id}")

    # Log de status
    from config import STATUS_CHANNEL_ID, LOG_CHANNEL_ID

    canal_status = bot.get_channel(STATUS_CHANNEL_ID)
    if canal_status:
        await canal_status.send("😎 o pai tá on!")

    canal_log = bot.get_channel(LOG_CHANNEL_ID)
    if canal_log:
        await canal_log.send("🧩 Todos os cogs carregados com sucesso!")


# --- Função principal ---
async def main():
    await load_cogs()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
