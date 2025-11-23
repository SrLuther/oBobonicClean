# bot.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from typing import Optional
import time 

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

# Lista de Cogs
COGS = [
    'tickets', 
    'admin', 
    'ai',             
    'autoresponse',   
    'moderation', 
    'xp', 
    'comandos',
]

# 3. Bloco de Debug 
print("-" * 50)
print(f"DEBUG: GUILD_ID lido: {GUILD_ID} (Tipo: {type(GUILD_ID)})")
print(f"DEBUG: CANAL_LOGS_ID lido: {CANAL_LOGS_ID} (Tipo: {type(CANAL_LOGS_ID)})")
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
        try:
            await bot.load_extension(module_name)
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
    print("🎩✨  Bobonicado conferiu o inventário arcano…")
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
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ ERRO FATAL ao iniciar o bot: {type(e).__name__}: {e}")
        exit(1)
