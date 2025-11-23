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
## 1. INICIALIZAÇÃO DE VARIÁVEIS E KEEP-ALIVE
# --------------------

# Carregar Variáveis de Ambiente e Configuração
load_dotenv()

# Leitura de IDs e Token
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

# --------------------
## FIM DA 1. INICIALIZAÇÃO DE VARIÁVEIS E KEEP-ALIVE
# --------------------

# --------------------
## 2. IMPLEMENTAÇÃO DO KEEP-ALIVE (FLASK)
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
## FIM DA 2. IMPLEMENTAÇÃO DO KEEP-ALIVE (FLASK)
# --------------------

# --------------------
## 3. CLASSE DE CAPTURA DE LOGS
# --------------------

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
        # Retorna o conteúdo e limpa o buffer para futuras capturas, se necessário
        return self.buffer.getvalue()

log_catcher = LogBuffer() 

# --------------------
## FIM DA 3. CLASSE DE CAPTURA DE LOGS
# --------------------

# --------------------
## 4. CONFIGURAÇÃO BASE DO BOT
# --------------------

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

# Bot sem o comando de help padrão e com as intenções necessárias
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None) 

# Lista de Cogs (Lida diretamente do config)
COGS = config.COGS

# Bloco de Debug para confirmar se os IDs foram lidos
print("-" * 50)
print(f"DEBUG: GUILD_ID lido: {GUILD_ID} (Tipo: {type(GUILD_ID)})")
print(f"DEBUG: CANAL_LOGS_ID lido: {CANAL_LOGS_ID} (Tipo: {type(CANAL_LOGS_ID)})")
print(f"DEBUG: CANAL_PROMO_ID lido: {CANAL_PROMO_ID} (Tipo: {type(CANAL_PROMO_ID)})")
print(f"DEBUG: LOBBY_CHANNEL_ID lido: {LOBBY_CHANNEL_ID} (Tipo: {type(LOBBY_CHANNEL_ID)})") 
print("-" * 50)

# --------------------
## FIM DA 4. CONFIGURAÇÃO BASE DO BOT
# --------------------


# --------------------
## 5. FUNÇÃO DE CARREGAMENTO DE COGS
# --------------------

async def load_cogs(bot: commands.Bot) -> bool:
    """Carrega todos os cogs com tratamento de erros robusto e logs no Discord."""
    
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    unix_timestamp = int(time.time())
    timestamp_formatado = f"<t:{unix_timestamp}:F>" 
    
    print("\n--- Iniciando Carregamento de Cogs ---")
    
    all_cogs_loaded = True 
    
    for cog_name in COGS:
        module_name = f"cogs.{cog_name}"
        kwargs = {}
        
        # Mapeamento dos argumentos que causam o TypeError se não forem **kwargs
        if cog_name == 'sales':
            kwargs['canal_promo_id'] = CANAL_PROMO_ID
        elif cog_name == 'voicemanager': 
            kwargs['lobby_channel_id'] = LOBBY_CHANNEL_ID 
            
        try:
            # Carrega o cog, passando os argumentos como **kwargs
            await bot.load_extension(module_name, **kwargs)
            print(f"[COG] Carregado: {cog_name}.py")
            
            if canal_logs:
                # O log de sucesso é enviada para o canal de logs
                await canal_logs.send(
                    f"[{timestamp_formatado}] ✅ Cog **`{cog_name}.py`** carregado com sucesso."
                )
            
        except Exception as e:
            error_message = f"Erro: {type(e).__name__}: {e}"
            print(f"[ERRO] Falha ao carregar {cog_name}.py: {error_message}")
            all_cogs_loaded = False 
            
            # O log de falha crítica é enviada para o canal de logs
            if canal_logs:
                await canal_logs.send(
                    f"[{timestamp_formatado}] ❌ Falha crítica ao carregar `{cog_name}`. Verifique o **log anexo** para detalhes."
                )

    # Mensagem final do Bobonicado no console
    print("\n" + "="*60)
    print("🎩✨  Bobonicado conferiu o inventário arcano…")
    print(f"Carregamento de cogs finalizado. Status: {'SUCESSO' if all_cogs_loaded else 'FALHA'}")
    print("="*60 + "\n")
    
    return all_cogs_loaded

# --------------------
## FIM DA 5. FUNÇÃO DE CARREGAMENTO DE COGS
# --------------------


# --------------------
## 6. EVENTO ON_READY (LOGICA DE BOOT)
# --------------------

@bot.event
async def on_ready():
    # 1. Parar a captura de logs e obter o conteúdo
    log_catcher.stop_capture()
    deploy_log_content = log_catcher.get_log()
    
    # Mensagens importantes de console (aparecerão no log)
    print(f"\n🚀 Bot Logado como {bot.user} (ID: {bot.user.id})")
    # ✅ LINHA DE DEBUG para forçar o deploy
    print("✅ ATENÇÃO: Último re-deploy forçado para correção dos Cogs.") 
    
    # 2. Envio do Log do Deploy para o Discord como arquivo
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    if canal_logs:
        try:
            agora = datetime.datetime.now()
            data_formatada = agora.strftime("%d/%m/%Y %H:%M:%S")

            # Cria o arquivo de log para anexar
            log_file = discord.File(
                fp=StringIO(deploy_log_content), 
                filename=f"log_oBobonic.txt" 
            )
            
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
            
    # 3. Executa o carregamento dos cogs e CAPTURA O STATUS
    cogs_loaded_successfully = await load_cogs(bot) 

    # 4. Sincronização de comandos
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
    
    # 5. Mensagem final dinâmica
    status_message = "✅ Bot pronto e rodando!" if cogs_loaded_successfully else "⚠️ Bot rodando (com falhas)!"
    print(status_message) 

# --------------------
## FIM DA 6. EVENTO ON_READY (LOGICA DE BOOT)
# --------------------


# --------------------
## 7. EXECUÇÃO PRINCIPAL
# --------------------

if __name__ == '__main__':
    try:
        # Inicia a captura de logs antes de tudo
        log_catcher.start_capture()
        print("Starting Container")
        
        # Inicia o servidor Keep-Alive em uma thread separada
        t = threading.Thread(target=run_keep_alive)
        t.start()
        print(f"🌐 Iniciando servidor Keep-Alive na porta {os.environ.get('PORT', 8080)}...")

        # Inicia o bot do Discord