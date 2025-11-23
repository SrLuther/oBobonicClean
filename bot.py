import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
# Garanta que todas as IDs e constantes estejam aqui
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
    
# 2. Inicialização do Bot
# Usamos Intents.all() para garantir que XP por Voz, Moderação e Boas-Vindas funcionem.
intents = discord.Intents.all() 

bot = commands.Bot(
    command_prefix='!', 
    intents=intents, 
    # 🛑 CORREÇÃO AQUI: Desabilita o comando de ajuda padrão para usar o de comandos.py
    help_command=None 
)

# 3. Lista de Cogs
COGS = [
    'tickets',      # Sistema de Tickets
    'admin',        # Comandos de Manutenção (reload, load, unload)
    'ai',           # Inteligência Artificial (Gemini)
    'autoresponse', # Boas-Vindas e Auto-Respostas
    'moderation',   # Moderação e Filtros
    'xp',           # Sistema de XP e Ranking
    'comandos',     # Menu de Ajuda (!ajuda)
]

# 4. Função de Carregamento Assíncrono dos Cogs
async def load_cogs():
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    
    # 🛑 NOVO: Bloco de segurança para o envio de logs de COGS
    try:
        if canal_logs:
            # LOGS RESTAURADOS: Envio de log inicial
            await canal_logs.send(LOG_SEPARATOR)
            await canal_logs.send(f"**⏳ Iniciando o carregamento dos módulos...**")
            
        for cog_name in COGS:
            module_name = f'cogs.{cog_name}'
            try:
                await bot.load_extension(module_name)
                log_time = get_detailed_log_time()
                descricao = f"📦 Cog {cog_name} carregado"
                
                print(f"[COG] Carregado: {cog_name}.py")
                if canal_logs:
                    # LOGS RESTAURADOS: Envio de log de sucesso
                    await canal_logs.send(f"`{log_time}` {descricao}")
                    
            except Exception as e:
                log_time = get_detailed_log_time()
                error_message = f"Extension 'cogs.{cog_name}' raised an error: {type(e).__name__}: {e}"
                
                print(f"[ERRO] Falha ao carregar {cog_name}.py: {error_message}")
                if canal_logs:
                    # LOGS RESTAURADOS: Envio de log de erro
                    await canal_logs.send(f"`{log_time}` ❌ **ALERTA DE ERRO:** Falha ao carregar **{cog_name}.py**: {error_message}")
        
        if canal_logs:
            # LOGS RESTAURADOS: Envio de separador final
            await canal_logs.send(LOG_SEPARATOR)
            
    except discord.Forbidden:
        print("⚠️ AVISO: Bot sem permissão para escrever no canal de logs durante o carregamento. Logs de COGS desabilitados.")
    except Exception as e:
        print(f"⚠️ AVISO: Erro inesperado no log de carregamento: {e}. Logs de COGS desabilitados.")
                
# --- Evento on_ready ---
@bot.event
async def on_ready():
    logging.info(f"🔥 Bot logado como {bot.user} | ID: {bot.user.id}")
    
    await load_cogs()
    
    # 🛑 NOVO: Sincronização dos Comandos de Barra (Slash Commands)
    try:
        # Sincroniza os comandos de barra, crucial para bots modernos.
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print("✅ Comandos de barra (slash) sincronizados com sucesso.")
    except Exception as e:
        # Se falhar, é um erro de API ou ID, mas não deve quebrar o loop principal.
        print(f"❌ ERRO FATAL: Falha ao sincronizar comandos de barra na Guilda ID {GUILD_ID}: {e}")
        
    # Prepara a data e hora para a mensagem FINAL
    status_time = get_status_time_format()
    
    # Busca o canal de LOGS para a mensagem final de status
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    
    # Mantemos o bloco try/except aqui para a mensagem final (Corrigido no passo anterior)
    if canal_logs: 
        try:
            # Envia a mensagem final de status para o canal de LOGS
            await canal_logs.send(f"✅ Todos os módulos carregados. **Bobonic está Online!** (Última Inicialização: {status_time})")
        except discord.Forbidden:
            print(f"⚠️ AVISO: Bot sem permissão para escrever no canal de logs {canal_logs.name} ({CANAL_LOGS_ID}). O bot continuará online.")
        except Exception as e:
            print(f"⚠️ AVISO: Erro desconhecido ao enviar log final: {e}. O bot continuará online.")

# 5. Início do Bot
# ------------------------------------
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        logging.error(f"Erro fatal ao iniciar o bot: {e}")
        print(f"Erro fatal ao iniciar o bot: {e}")