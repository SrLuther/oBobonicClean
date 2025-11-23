# bot.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from typing import Optional

# 1. Carregar Variáveis de Ambiente e Configuração
load_dotenv()

# 🛑 NOVO: Função para ler IDs diretamente do ambiente (Railway/Local)
def get_env_id(key):
    # Tenta pegar a variável e converter para int. Se falhar, retorna 0.
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

# O Token do Bot é lido do ambiente
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ ERRO: DISCORD_TOKEN não encontrado. Verifique seu .env ou variáveis do Railway.")
    exit(1)

# 2. Configuração do Bot e Intenções
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

# IMPORTANTE: Adicionamos help_command=None pois o comando 'bobo' do cogs/comandos.py substitui o help padrão.
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

# 3. Bloco de Debug (Pode ser removido após estabilização)
print("-" * 50)
print(f"DEBUG: GUILD_ID lido: {GUILD_ID} (Tipo: {type(GUILD_ID)})")
print(f"DEBUG: CANAL_LOGS_ID lido: {CANAL_LOGS_ID} (Tipo: {type(CANAL_LOGS_ID)})")
print("-" * 50)
# Fim do Bloco de Debug

# 4. Função de Carregamento de Cogs (Com notificação no Discord)
async def load_cogs(bot: commands.Bot):
    """Carrega todos os cogs com tratamento de erros robusto e logs."""
    
    # ⚠️ Esta chamada só funciona se a ID for válida e o bot tiver cacheado o canal.
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    
    # Diagnóstico
    print(f"DEBUG_LOG: Canal de Logs encontrado? {'Sim' if canal_logs else 'Não'}")
    
    print("\n--- Iniciando Carregamento de Cogs ---")
    
    for cog_name in COGS:
        module_name = f"cogs.{cog_name}"
        try:
            await bot.load_extension(module_name)
            print(f"[COG] Carregado: {cog_name}.py")
            
            # Notificação de sucesso no Discord
            if canal_logs:
                try:
                    await canal_logs.send(f"✅ Cog **`{cog_name}.py`** carregado com sucesso.")
                except discord.Forbidden:
                    # Este print indica falta de permissão.
                    print(f"⚠️ Aviso: Não consegui notificar o canal de logs. Permissões insuficientes.")
            
        except discord.ext.commands.ExtensionNotFound:
            error_message = f"Cog '{cog_name}' não encontrado."
            print(f"[ERRO] {error_message}")
            if canal_logs:
                await canal_logs.send(f"❌ Falha ao carregar cog: {error_message}")
                
        except Exception as e:
            error_message = f"Cog '{cog_name}' levantou um erro: {type(e).__name__}: {e}"
            print(f"[ERRO] Falha ao carregar {cog_name}.py: {error_message}")
            if canal_logs:
                try:
                    await canal_logs.send(f"❌ Falha crítica ao carregar o cog `{cog_name}`. Detalhes: `{error_message}`")
                except Exception:
                    pass

# 5. Evento on_ready (Robusto)
@bot.event
async def on_ready():
    print(f"\n🚀 Bot Logado como {bot.user} (ID: {bot.user.id})")
    
    # 1. Carregamento dos Cogs
    await load_cogs(bot)

    # 2. Sincronização de Comandos de Barra
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
        
        canal_logs = bot.get_channel(CANAL_LOGS_ID)
        if canal_logs:
            try:
                await canal_logs.send(f"❌ Falha crítica na sincronização de comandos. Verifique o `GUILD_ID`. Detalhes: `{error_message}`")
            except Exception:
                pass

# 6. Execução do Bot
if __name__ == '__main__':
    try:
        print("Starting Container")
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ ERRO FATAL ao iniciar o bot: {type(e).__name__}: {e}")
        exit(1)