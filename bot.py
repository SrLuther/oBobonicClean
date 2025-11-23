# bot.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from typing import Optional
import time 
import threading 
from flask import Flask 

# --------------------
## 🛑 IMPLEMENTAÇÃO DO KEEP-ALIVE
# --------------------

def run_keep_alive():
    """Configura e inicia o servidor Flask em uma thread separada."""
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return "Bot is running and healthy!"

    port = int(os.environ.get("PORT", 8080))
    
    print(f"🌐 Iniciando servidor Keep-Alive na porta {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --------------------
## 🛑 CÓDIGO DO BOT
# --------------------

# 1. Carregar Variáveis de Ambiente e Configuração
load_dotenv()

# Função para ler IDs diretamente do ambiente (Railway/Local)
def get_env_id(key):
    value = os.getenv(key)
    try:
        return int(value) if value else 0
    except ValueError:
        print(f"❌ ERRO: {key} deve ser um número inteiro. Verifique suas variáveis de ambiente.")
        return 0

GUILD_ID = get_env_id("GUILD_ID")
CANAL_LOGS_ID = get_env_id("CANAL_LOGS_ID")
TICKET_CATEGORY_ID = get_env_id("TICKET_CATEGORY_ID")
TICKET_STAFF_ROLE_ID = get_env_id("TICKET_STAFF_ROLE_ID")

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ ERRO: DISCORD_TOKEN não encontrado. Verifique seu .env ou variáveis do Railway.")
    exit(1)

# 2. Configuração do Bot e Intenções
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None) 

# Lista de Cogs (Deixamos apenas os essenciais para o teste de estabilidade)
COGS = [
    # 'tickets',        
    'admin', 
    # 'ai',             
    # 'autoresponse',   
    'moderation', 
    # 'xp',             
    'comandos',
]

# 3. Bloco de Debug 
print("-" * 50)
print(f"DEBUG: GUILD_ID lido: {GUILD_ID} (Tipo: {type(GUILD_ID)})")
print(f"DEBUG: CANAL_LOGS_ID lido: {CANAL_LOGS_ID} (Tipo: {type(CANAL_LOGS_ID)})")
print("-" * 50)

# 4. Função de Carregamento de Cogs 
async def load_cogs(bot: commands.Bot):
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    print(f"DEBUG_LOG: Canal de Logs encontrado? {'Sim' if canal_logs else 'Não'}")
    print("\n--- Iniciando Carregamento de Cogs ---")
    
    unix_timestamp = int(time.time())
    timestamp_formatado = f"<t:{unix_timestamp}:F>"

    for cog_name in COGS:
        module_name = f"cogs.{cog_name}"
        try:
            await bot.load_extension(module_name)
            print(f"[COG] Carregado: {cog_name}.py")
            if canal_logs:
                try:
                    log_message = f"[{timestamp_formatado}] ✅ Cog **`{cog_name}.py`** carregado com sucesso."
                    await canal_logs.send(log_message)
                except discord.Forbidden:
                    print(f"⚠️ Aviso: Não consegui notificar o canal de logs. Permissões insuficientes.")
        except discord.ext.commands.ExtensionNotFound:
            error_message = f"Cog '{cog_name}' não encontrado."
            print(f"[ERRO] {error_message}")
            if canal_logs:
                log_message = f"[{timestamp_formatado}] ❌ Falha ao carregar cog: {error_message}"
                await canal_logs.send(log_message)
        except Exception as e:
            error_message = f"Cog '{cog_name}' levantou um erro: {type(e).__name__}: {e}"
            print(f"[ERRO] Falha ao carregar {cog_name}.py: {error_message}")
            if canal_logs:
                try:
                    log_message = f"[{timestamp_formatado}] ❌ Falha crítica ao carregar o cog `{cog_name}`. Detalhes: `{error_message}`"
                    await canal_logs.send(log_message)
                except Exception:
                    pass

# 5. Evento on_ready 
@bot.event
async def on_ready():
    print(f"\n🚀 Bot Logado como {bot.user} (ID: {bot.user.id})")
    
    # 1. Carregamento dos Cogs
    await load_cogs(bot)

    # 2. Sincronização de Comandos de Barra (REATIVADA PARA CONSUMIR TEMPO)
    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=GUILD_ID)
            await bot.tree.sync(guild=guild_obj)
        else:
            await bot.tree.sync()
            
        print("✅ Comandos de barra (slash) sincronizados com sucesso.")
        
    except Exception as e:
        error_message = f"Falha ao sincronizar comandos de barra: {type(e).__name__}: {e}"
        print(f"❌ ERRO de Sincronização: {error_message}")
        
        unix_timestamp = int(time.time())
        timestamp_formatado = f"<t:{unix_timestamp}:F>"
        
        canal_logs = bot.get_channel(CANAL_LOGS_ID)
        if canal_logs:
            try:
                log_message = f"[{timestamp_formatado}] ❌ Falha crítica na sincronização de comandos. Verifique o `GUILD_ID`. Detalhes: `{error_message}`"
                await canal_logs.send(log_message)
            except Exception:
                pass
                
    # Mensagem de Confirmação Final
    print("✅ Bot pronto e rodando!")

# 6. Execução do Bot
if __name__ == '__main__':
    try:
        print("Starting Container")
        
        # INICIA O KEEP-ALIVE EM UMA THREAD SEPARADA
        t = threading.Thread(target=run_keep_alive)
        t.start()
        
        # Inicia o Bot (loop principal)
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ ERRO FATAL ao iniciar o bot: {type(e).__name__}: {e}")
        exit(1)