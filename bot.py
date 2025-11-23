# bot.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import time 
import threading 
from flask import Flask 
import sys
from io import StringIO
import datetime 
import config # ✅ NOVO: Importa o arquivo de configuração para obter IDs e COGS

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
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --------------------
## 🛑 CÓDIGO DO BOT
# --------------------

# 1. Carregar Variáveis de Ambiente e Configuração
load_dotenv()

# --- CLASSE PARA CAPTURAR O LOG ---
class LogBuffer:
    """Captura todo o output (print) do console para posterior envio ao Discord."""
    # ✅ CORREÇÃO DE INDENTAÇÃO: O construtor __init__ está corretamente indentado
    def __init__(self): 
        self.buffer = StringIO()
        self.original_stdout = sys.stdout

    def start_capture(self):
        sys.stdout = self.buffer

    def stop_capture(self):
        sys.stdout = self.original_stdout

    def get_log(self):
        return self.buffer.getvalue()

log_catcher = LogBuffer() # ✅ Linha 27, agora sem erro de indentação


# 2. Leitura de IDs e Token
# Agora lemos diretamente do módulo config
GUILD_ID = config.GUILD_ID
CANAL_LOGS_ID = config.CANAL_LOGS_ID
TICKET_CATEGORY_ID = config.TICKET_CATEGORY_ID
TICKET_STAFF_ROLE_ID = config.STAFF_ROLE_ID # Usando STAFF_ROLE_ID do config
CANAL_PROMO_ID = config.CANAL_PROMO_ID
LOBBY_CHANNEL_ID = config.LOBBY_CHANNEL_ID # ✅ NOVO ID lido do config

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ ERRO: DISCORD_TOKEN não encontrado. Verifique seu .env ou variáveis do Railway.")
    exit(1)

# 3. Configuração do Bot e Intenções
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None) 

# Lista de Cogs (Lida diretamente do config)
COGS = config.COGS

# 4. Bloco de Debug 
print("-" * 50)
print(f"DEBUG: GUILD_ID lido: {GUILD_ID} (Tipo: {type(GUILD_ID)})")
print(f"DEBUG: CANAL_LOGS_ID lido: {CANAL_LOGS_ID} (Tipo: {type(CANAL_LOGS_ID)})")
print(f"DEBUG: CANAL_PROMO_ID lido: {CANAL_PROMO_ID} (Tipo: {type(CANAL_PROMO_ID)})")
print(f"DEBUG: LOBBY_CHANNEL_ID lido: {LOBBY_CHANNEL_ID} (Tipo: {type(LOBBY_CHANNEL_ID)})") # ✅ Novo debug
print("-" * 50)

# 5. Função de Carregamento de Cogs 
async def load_cogs(bot: commands.Bot):
    """Carrega todos os cogs com tratamento de erros robusto e logs."""
    
    print("\n--- Iniciando Carregamento de Cogs ---")
    
    for cog_name in COGS:
        module_name = f"cogs.{cog_name}"
        kwargs = {}
        
        # Passando IDs específicos para Cogs
        if cog_name == 'sales':
            kwargs['canal_promo_id'] = CANAL_PROMO_ID
        elif cog_name == 'voicemanager': # ✅ Passa o LOBBY_CHANNEL_ID
            kwargs['lobby_channel_id'] = LOBBY_CHANNEL_ID 
            
        try:
            await bot.load_extension(module_name, **kwargs)
            print(f"[COG] Carregado: {cog_name}.py")
            
        except Exception as e:
            error_message = f"Erro: {type(e).__name__}: {e}"
            print(f"[ERRO] Falha ao carregar {cog_name}.py: {error_message}")

    # ... (Restante do bloco de log de sucesso) ...
    print("\n" + "="*60)
    print("🎩✨  Bobonicado conferiu o inventário arcano…")
    print("Se o impossível carregou, provavelmente foi coisa dele. 😎")
    print("Todos os cogs foram carregados com sucesso! 🚀")
    print("="*60 + "\n")


# 6. Evento on_ready 
@bot.event
async def on_ready():
    # ... (Restante do on_ready) ...

    # 3. Envio do Log do Deploy para o Discord como arquivo
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    if canal_logs:
        # ... (Lógica de envio de log via arquivo) ...
            
    print("✅ Bot pronto e rodando!")

# 7. Execução do Bot 
if __name__ == '__main__':
    # ... (Bloco de execução com Keep-Alive) ...
    try:
        log_catcher.start_capture()
        print("Starting Container")
        
        t = threading.Thread(target=run_keep_alive)
        t.start()
        print(f"🌐 Iniciando servidor Keep-Alive na porta {os.environ.get('PORT', 8080)}...")

        bot.run(TOKEN)
    except Exception as e:
        log_catcher.stop_capture()
        print(f"❌ ERRO FATAL ao iniciar o bot: {type(e).__name__}: {e}")
        exit(1)