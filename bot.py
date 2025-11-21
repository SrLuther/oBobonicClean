import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from config import CANAL_STATUS_ID

# --- Carrega .env ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("Token do bot não encontrado no .env")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Mapas de descrição para logs ---
COG_DESCRICOES = {
    "admin": "⚙️ Sistema administrativo carregado",
    "ai": "🤖 Sistema de AI carregado",
    "autoresponse": "💬 Sistema de respostas automáticas carregado",
    "moderation": "🛡️ Sistema de moderação carregado",
    "xp": "⭐ Sistema de XP carregado",
    "tickets": "🎫 Sistema de tickets carregado",
    "comandos": "🧰 Sistema de comandos carregado"
}

# --- Função para carregar todos os cogs ---
async def load_cogs():
    canal_status = bot.get_channel(CANAL_STATUS_ID)

    # Ordem de carregamento para garantir dependências
    cogs_order = ["tickets", "comandos", "admin", "ai", "autoresponse", "moderation", "xp"]

    for cog_name in cogs_order:
        try:
            await bot.load_extension(f"cogs.{cog_name}")
            print(f"[COG] Carregado: {cog_name}.py")
            if canal_status:
                descricao = COG_DESCRICOES.get(cog_name, f"📦 Cog {cog_name} carregado")
                await canal_status.send(descricao)
        except Exception as e:
            print(f"[ERRO] Falha ao carregar {cog_name}.py: {e}")
            if canal_status:
                await canal_status.send(f"❌ Falha ao carregar {cog_name}.py: {e}")

# --- Evento on_ready ---
@bot.event
async def on_ready():
    print(f"🔥 Bot logado como {bot.user} | ID: {bot.user.id}")
    await load_cogs()
    canal_status = bot.get_channel(CANAL_STATUS_ID)
    if canal_status:
        await canal_status.send("✅ Todos os cogs carregados!")

# --- Função principal ---
async def main():
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
