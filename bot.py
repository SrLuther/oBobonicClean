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
import config 

# --------------------
## 1. IMPLEMENTAÇÃO DO KEEP-ALIVE (FLASK)
# --------------------

def run_keep_alive():
    """Configura e inicia o servidor Flask em uma thread separada."""
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return "Bot is running and healthy!"

    port = int(os.environ.get("PORT", 8080))
    # use_reloader=False é crucial para evitar que a aplicação rode duas vezes
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --------------------
## 2. CONFIGURAÇÃO E VARIÁVEIS
# --------------------

# Carregar Variáveis de Ambiente
load_dotenv()

# Classe para capturar o log do console
class LogBuffer:
    def __init__(self):
        self.buffer = StringIO()
        self.original_stdout = sys.stdout

    def start_capture(self):
        sys.stdout = self.buffer

    def stop_capture(self):
        sys.stdout = self.original_stdout

    def get_log(self):
        return self.buffer.getvalue()

log_catcher = LogBuffer() 

# Leitura de IDs do arquivo config
GUILD_ID = config.GUILD_ID
CANAL_LOGS_ID = config.CANAL_LOGS_ID
TICKET_CATEGORY_ID = config.TICKET_CATEGORY_ID
TICKET_STAFF_ROLE_ID = config.STAFF_ROLE_ID 
CANAL_PROMO_ID = config.CANAL_PROMO_ID
LOBBY_CHANNEL_ID = config.LOBBY_CHANNEL_ID 

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ ERRO: DISCORD_TOKEN não encontrado.")
    exit(1)

# Configuração do Bot
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None) 

# Lista de Cogs
COGS = config.COGS

# Debug de IDs
print("-" * 50)
print(f"DEBUG: GUILD_ID: {GUILD_ID}")
print(f"DEBUG: CANAL_LOGS_ID: {CANAL_LOGS_ID}")
print(f"DEBUG: CANAL_PROMO_ID: {CANAL_PROMO_ID}")
print(f"DEBUG: LOBBY_CHANNEL_ID: {LOBBY_CHANNEL_ID}") 
print("-" * 50)

# --------------------
## 3. FUNÇÕES AUXILIARES
# --------------------

async def load_cogs(bot: commands.Bot) -> bool:
    """Carrega todos os cogs e notifica no Discord."""
    
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    unix_timestamp = int(time.time())
    timestamp_formatado = f"<t:{unix_timestamp}:F>" 
    
    print("\n--- Iniciando Carregamento de Cogs ---")
    
    all_cogs_loaded = True 
    
    for cog_name in COGS:
        module_name = f"cogs.{cog_name}"
        kwargs = {}
        
        if cog_name == 'sales':
            kwargs['canal_promo_id'] = CANAL_PROMO_ID
        elif cog_name == 'voicemanager': 
            kwargs['lobby_channel_id'] = LOBBY_CHANNEL_ID 
            
        try:
            await bot.load_extension(module_name, **kwargs)
            print(f"[COG] Carregado: {cog_name}.py")
            
            # NOTIFICAÇÃO NO DISCORD (opcional, pode ser removida se for redundante com o log anexo)
            if canal_logs:
                await canal_logs.send(f"[{timestamp_formatado}] ✅ Cog **`{cog_name}.py`** carregado com sucesso.")
            
        except Exception as e:
            error_message = f"Erro: {type(e).__name__}: {e}"
            print(f"[ERRO] Falha ao carregar {cog_name}.py: {error_message}")
            all_cogs_loaded = False 
            
            # NOTIFICAÇÃO NO DISCORD
            if canal_logs:
                await canal_logs.send(f"[{timestamp_formatado}] ❌ Falha crítica ao carregar `{cog_name}`. Verifique o log anexo.")

    print("\n" + "="*60)
    print("🎩✨ Bobonicado conferiu o inventário arcano...")
    print(f"Status Final: {'SUCESSO' if all_cogs_loaded else 'FALHA'}")
    print("="*60 + "\n")
    
    return all_cogs_loaded

# --------------------
## 4. EVENTO ON_READY
# --------------------

@bot.event
async def on_ready():
    
    print(f"\n🚀 Bot Logado como {bot.user} (ID: {bot.user.id})")
    
    # 1. Carrega os Cogs (Os erros são impressos e CAPTURADOS AQUI)
    cogs_loaded_successfully = await load_cogs(bot) 

    # 2. Sincroniza Comandos
    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=GUILD_ID)
            await bot.tree.sync(guild=guild_obj)
        else:
            await bot.tree.sync()
        print("✅ Comandos de barra (slash) sincronizados.")
    except Exception as e:
        print(f"❌ ERRO Sincronização: {e}")
    
    # 3. Finaliza a captura de logs e obtém o conteúdo COMPLETO
    log_catcher.stop_capture()
    deploy_log_content = log_catcher.get_log()

    # 4. Envio do Arquivo de Log COMPLETO para o Discord
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    if canal_logs:
        try:
            agora = datetime.datetime.now()
            data_formatada = agora.strftime("%d/%m/%Y %H:%M:%S")

            log_file = discord.File(
                fp=StringIO(deploy_log_content), 
                filename=f"log_oBobonic.txt" 
            )
            
            mensagem_deploy = (
                f"🤖 **oBobonic** iniciado ou reiniciado em `{data_formatada}`. "
                f"Verifique o **log completo** no arquivo anexo abaixo:"
            )
            
            await canal_logs.send(mensagem_deploy, file=log_file)
            
        except Exception as e:
            # Re-inicia a captura para o erro não se perder
            log_catcher.start_capture()
            print(f"❌ ERRO CRÍTICO ao enviar log para o Discord: {e}")
            
    # 5. Mensagem Final no console
    status_message = "✅ Bot pronto e rodando!" if cogs_loaded_successfully else "⚠️ Bot rodando (com falhas)!"
    print(status_message) 

# --------------------
## 5. EXECUÇÃO PRINCIPAL
# --------------------

if __name__ == '__main__':
    try:
        log_catcher.start_capture()
        print("Starting Container")
        
        t = threading.Thread(target=run_keep_alive)
        t.start()
        print(f"🌐 Iniciando servidor Keep-Alive na porta {os.environ.get('PORT', 8080)}...")

        bot.run(TOKEN)
    except Exception as e:
        log_catcher.stop_capture()
        print(f"❌ ERRO FATAL: {e}")
        exit(1)

# Atualizado em: 23/11/2025 19:30 (Horário de Brasília)