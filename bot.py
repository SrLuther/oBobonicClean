import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from config import CANAL_STATUS_ID, GUILD_ID, CANAL_LOGS_ID, LOG_SEPARATOR
import logging 
from datetime import datetime

# --- Função Auxiliar para Logs Detalhados ---
def get_detailed_log_time():
    """Retorna data e hora detalhadas para logs de carregamento: [dd/mm/aaaa HH:MM:SS]"""
    now = datetime.now()
    return now.strftime("[%d/%m/%Y %H:%M:%S]")

# --- Função Auxiliar para Status Final ---
def get_status_time_format():
    """Retorna data e hora no formato dd/mm/aaaa HH:MM para a mensagem de status final."""
    now = datetime.now()
    return now.strftime("%d/%m/%Y %H:%M") 

# --- 1. Configuração de Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
    filename='bot_logs.log', 
    encoding='utf-8'
)
logging.getLogger('discord').setLevel(logging.WARNING)
# ----------------------------------------------------

# --- Carrega .env ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("Token do bot não encontrado no .env")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Mapas de descrição ---
COG_DESCRICOES = {
    "admin": "⚙️ Sistema administrativo carregado",
    "ai": "🤖 Sistema de AI carregado",
    "autoresponse": "💬 Sistema de respostas automáticas carregado",
    "moderation": "🛡️ Sistema de moderação carregado",
    "xp": "⭐ Sistema de XP carregado",
    "tickets": "🎫 Sistema de tickets carregado",
    "comandos": "🧰 Sistema de comandos carregado"
}

# --- Função para carregar todos os cogs (Logs enviados para CANAL_LOGS_ID) ---
async def load_cogs():
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    
    if canal_logs:
        await canal_logs.send(LOG_SEPARATOR)
        await canal_logs.send(f"**⏰ Iniciando Carregamento de Cogs ({len(COG_DESCRICOES)} total)...**")

    cogs_order = ["tickets", "comandos", "admin", "ai", "autoresponse", "moderation", "xp"]

    for cog_name in cogs_order:
        try:
            await bot.load_extension(f"cogs.{cog_name}")
            
            log_time = get_detailed_log_time()
            descricao = COG_DESCRICOES.get(cog_name, f"📦 Cog {cog_name} carregado")
            
            print(f"[COG] Carregado: {cog_name}.py")
            if canal_logs:
                await canal_logs.send(f"`{log_time}` {descricao}")
                
        except Exception as e:
            log_time = get_detailed_log_time()
            
            print(f"[ERRO] Falha ao carregar {cog_name}.py: {e}")
            if canal_logs:
                await canal_logs.send(f"`{log_time}` ❌ **ALERTA DE ERRO:** Falha ao carregar **{cog_name}.py**: {e}")
    
    if canal_logs:
        await canal_logs.send(LOG_SEPARATOR)
                
# --- Evento on_ready ---
@bot.event
async def on_ready():
    logging.info(f"🔥 Bot logado como {bot.user} | ID: {bot.user.id}")
    
    await load_cogs()
    
    # Prepara a data e hora para a mensagem FINAL
    status_time = get_status_time_format()
    
    # Busca o canal de LOGS para a mensagem final de status
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    
    if canal_logs:
        # Envia a mensagem final de status para o canal de LOGS
        await canal_logs.send(f"✅ Todos os cogs carregados em **{status_time}**")
    else:
        # Se nem o canal de logs existir, registra um aviso interno
        logging.warning(f"Canal de logs (ID: {CANAL_LOGS_ID}) não encontrado para enviar confirmação final.")

# --- Função principal ---
async def main():
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
