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
## 🛑 IMPLEMENTAÇÃO DO KEEP-ALIVE
# --------------------
# ... (NÃO HÁ ALTERAÇÕES AQUI)
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


# 2. Leitura de IDs e Token
# ... (NÃO HÁ ALTERAÇÕES AQUI)
GUILD_ID = config.GUILD_ID
CANAL_LOGS_ID = config.CANAL_LOGS_ID
TICKET_CATEGORY_ID = config.TICKET_CATEGORY_ID
TICKET_STAFF_ROLE_ID = config.STAFF_ROLE_ID 
CANAL_PROMO_ID = config.CANAL_PROMO_ID
LOBBY_CHANNEL_ID = config.LOBBY_CHANNEL_ID 

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
# ... (NÃO HÁ ALTERAÇÕES AQUI)
print("-" * 50)
print(f"DEBUG: GUILD_ID lido: {GUILD_ID} (Tipo: {type(GUILD_ID)})")
print(f"DEBUG: CANAL_LOGS_ID lido: {CANAL_LOGS_ID} (Tipo: {type(CANAL_LOGS_ID)})")
print(f"DEBUG: CANAL_PROMO_ID lido: {CANAL_PROMO_ID} (Tipo: {type(CANAL_PROMO_ID)})")
print(f"DEBUG: LOBBY_CHANNEL_ID lido: {LOBBY_CHANNEL_ID} (Tipo: {type(LOBBY_CHANNEL_ID)})") 
print("-" * 50)

# 5. Função de Carregamento de Cogs 
async def load_cogs(bot: commands.Bot):
    """Carrega todos os cogs com tratamento de erros robusto e logs no Discord."""
    
    # O canal_logs é obtido aqui para enviar logs individuais
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    unix_timestamp = int(time.time())
    timestamp_formatado = f"<t:{unix_timestamp}:F>" 
    
    print("\n--- Iniciando Carregamento de Cogs ---")
    
    # Variável para rastrear se todos os cogs carregaram
    all_cogs_loaded = True 
    
    for cog_name in COGS:
        module_name = f"cogs.{cog_name}"
        kwargs = {}
        
        # Passando IDs específicos para Cogs
        if cog_name == 'sales':
            kwargs['canal_promo_id'] = CANAL_PROMO_ID
        elif cog_name == 'voicemanager': 
            kwargs['lobby_channel_id'] = LOBBY_CHANNEL_ID 
            
        try:
            await bot.load_extension(module_name, **kwargs)
            print(f"[COG] Carregado: {cog_name}.py")
            
            # ✅ ENVIAR MENSAGEM DE SUCESSO DE VOLTA AO DISCORD
            if canal_logs:
                await canal_logs.send(
                    f"[{timestamp_formatado}] ✅ Cog **`{cog_name}.py`** carregado com sucesso."
                )
            
        except Exception as e:
            error_message = f"Erro: {type(e).__name__}: {e}"
            print(f"[ERRO] Falha ao carregar {cog_name}.py: {error_message}")
            all_cogs_loaded = False # Marca falha
            
            # ❌ ENVIAR MENSAGEM DE FALHA DE VOLTA AO DISCORD
            if canal_logs:
                await canal_logs.send(
                    f"[{timestamp_formatado}] ❌ Falha crítica ao carregar `{cog_name}`. Verifique o **log anexo** para detalhes."
                )

    # ==== SEPARADOR BOBO NIC ADO (depois de carregar tudo) ====
    print("\n" + "="*60)
    print("🎩✨  Bobonicado conferiu o inventário arcano…")
    
    # Envio da mensagem final (após o loop)
    if canal_logs:
        status_emoji = "🚀" if all_cogs_loaded else "⚠️"
        await canal_logs.send(
            f"🎩✨ **Bobonicado conferiu o inventário arcano...**\n"
            f"Se até o impossível carregou, então foi coisa dele mesmo. 😎\n"
            f"{status_emoji} **Carregamento de Cogs finalizado.**"
        )
    
    print("Se o impossível carregou, provavelmente foi coisa dele. 😎")
    print(f"Carregamento de cogs finalizado. Status: {'SUCESSO' if all_cogs_loaded else 'FALHA'}")
    print("="*60 + "\n")


# 6. Evento on_ready 
@bot.event
async def on_ready():
    # 1. Parar a captura de logs
    log_catcher.stop_capture()
    deploy_log_content = log_catcher.get_log()
    
    print(f"\n🚀 Bot Logado como {bot.user} (ID: {bot.user.id})")
    
    # 2. Envio do Log do Deploy para o Discord como arquivo (PRIORIDADE)
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    if canal_logs:
        try:
            agora = datetime.datetime.now()
            data_formatada = agora.strftime("%d/%m/%Y %H:%M:%S")

            log_file = discord.File(
                fp=StringIO(deploy_log_content), 
                filename=f"log_oBobonic.txt" 
            )
            
            # Mensagem principal com o anexo
            mensagem_deploy = (
                f"🤖 **oBobonic** iniciado ou reiniciado em `{data_formatada}`. "
                f"Verifique o log completo no arquivo anexo abaixo:"
            )
            
            await canal_logs.send(
                mensagem_deploy,
                file=log_file
            )

        except Exception as e:
            print(f"❌ ERRO ao enviar arquivo de log para o Discord: {e}")
            
    # 3. Executa o carregamento dos cogs, que AGORA envia as mensagens de status
    await load_cogs(bot) 

    # 4. Sincronização de comandos
    # ... (Bloco de sincronização de comandos)
    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=GUILD_ID)
            await bot.tree.sync(guild=guild_obj)
        else:
            await bot.tree.sync()
            
        print("✅ Comandos de barra (slash) sincronizados com sucesso.")
        
    except Exception as e:
        error_message = f"Sincronização falhou: {type(e).__name__}: {e}"
        print(f"❌ ERRO: {error_message}")
            
    print("✅ Bot pronto e rodando!") 

# 7. Execução do Bot 
# ... (NÃO HÁ ALTERAÇÕES AQUI)
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
        print(f"❌ ERRO FATAL ao iniciar o bot: {type(e).__name__}: {e}")
        exit(1)