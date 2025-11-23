# bot.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
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

    # O Railway fornece a variável PORT automaticamente
    port = int(os.environ.get("PORT", 8080))
    
    print(f"🌐 Iniciando servidor Keep-Alive na porta {port}...")
    # use_reloader=False é crucial quando rodando em threads
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
# CANAL_PROMO_ID é lido do ambiente
CANAL_PROMO_ID = get_env_id("CANAL_PROMO_ID") 

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ ERRO: DISCORD_TOKEN não encontrado. Verifique seu .env ou variáveis do Railway.")
    exit(1)

# 2. Configuração do Bot e Intenções
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None) 

# Lista de Cogs (Hardcoded, conforme a sua estrutura)
COGS = [
    'tickets', 
    'admin', 
    # 'ai',             
    # 'autoresponse',   
    'moderation', 
    'xp', 
    'comandos',
    'sales', # ✅ Garantindo que 'sales' está incluído
]

# 3. Bloco de Debug 
print("-" * 50)
print(f"DEBUG: GUILD_ID lido: {GUILD_ID} (Tipo: {type(GUILD_ID)})")
print(f"DEBUG: CANAL_LOGS_ID lido: {CANAL_LOGS_ID} (Tipo: {type(CANAL_LOGS_ID)})")
print(f"DEBUG: CANAL_PROMO_ID lido: {CANAL_PROMO_ID} (Tipo: {type(CANAL_PROMO_ID)})")
print("-" * 50)

# 4. Função de Carregamento de Cogs 
async def load_cogs(bot: commands.Bot):
    """Carrega todos os cogs com tratamento de erros robusto e logs."""
    
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    print(f"DEBUG_LOG: Canal de Logs encontrado? {'Sim' if canal_logs else 'Não'}")
    
    print("\n--- Iniciando Carregamento de Cogs ---")
    
    unix_timestamp = int(time.time())
    timestamp_formatado = f"<t:{unix_timestamp}:F>" 

    # ==== Carregar Cogs ====
    for cog_name in COGS:
        module_name = f"cogs.{cog_name}"
        kwargs = {}
        
        # Se for o cog 'sales', adiciona o ID do canal de promoções
        if cog_name == 'sales':
            kwargs['canal_promo_id'] = CANAL_PROMO_ID # ✅ Passando o ID lido acima
            
        try:
            await bot.load_extension(module_name, **kwargs) 
            print(f"[COG] Carregado: {cog_name}.py")
            
            if canal_logs:
                try:
                    await canal_logs.send(
                        f"[{timestamp_formatado}] ✅ Cog **`{cog_name}.py`** carregado com sucesso."
                    )
                except discord.Forbidden:
                    print("⚠️ Aviso: Sem permissão para enviar mensagem no canal de logs.")
            
        except discord.ext.commands.ExtensionNotFound:
            error_message = f"Cog '{cog_name}' não encontrado."
            print(f"[ERRO] {error_message}")
            if canal_logs:
                await canal_logs.send(
                    f"[{timestamp_formatado}] ❌ Falha ao carregar cog: {error_message}"
                )
                
        except Exception as e:
            error_message = f"Erro: {type(e).__name__}: {e}"
            print(f"[ERRO] Falha ao carregar {cog_name}.py: {error_message}")
            if canal_logs:
                try:
                    await canal_logs.send(
                        f"[{timestamp_formatado}] ❌ Falha crítica ao carregar `{cog_name}`. Detalhes: `{error_message}`"
                    )
                except:
                    pass

    # ==== SEPARADOR BOBO NIC ADO (depois de carregar tudo) ====
    print("\n" + "="*60)
    print("🎩✨  Bobonicado conferiu o inventário arcano…")
    print("Se o impossível carregou, provavelmente foi coisa dele. 😎")
    print("Todos os cogs foram carregados com sucesso! 🚀")
    print("="*60 + "\n")

    if canal_logs:
        try:
            await canal_logs.send(
                "🎩✨ **Bobonicado conferiu o inventário arcano...**\n"
                "Se até o impossível carregou, então foi coisa dele mesmo. 😎\n"
                "🚀 **Todos os cogs foram carregados com sucesso!**"
            )
        except:
            pass


# 5. Evento on_ready 
@bot.event
async def on_ready():
    print(f"\n🚀 Bot Logado como {bot.user} (ID: {bot.user.id})")
    
    await load_cogs(bot)

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
        
        unix_timestamp = int(time.time())
        timestamp_formatado = f"<t:{unix_timestamp}:F>"
        
        canal_logs = bot.get_channel(CANAL_LOGS_ID)
        if canal_logs:
            try:
                await canal_logs.send(
                    f"[{timestamp_formatado}] ❌ Falha crítica ao sincronizar comandos. Detalhes: `{error_message}`"
                )
            except:
                pass
                
    print("✅ Bot pronto e rodando!")

# 6. Execução do Bot 
if __name__ == '__main__':
    try:
        print("Starting Container")
        
        # 🟢 INICIA O KEEP-ALIVE EM UMA THREAD SEPARADA ANTES DO BOT.RUN()
        t = threading.Thread(target=run_keep_alive)
        t.start()
        
        # Inicia o Bot (loop principal)
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ ERRO FATAL ao iniciar o bot: {type(e).__name__}: {e}")
        exit(1)