# bot.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from typing import Optional

# 1. Carregar Variáveis de Ambiente e Configuração
load_dotenv()

# Tenta importar variáveis críticas do config.py. Se não existir, usa 0.
try:
    from config import GUILD_ID, CANAL_LOGS_ID, TICKET_CATEGORY_ID
except ImportError:
    print("⚠️ config.py não encontrado. Usando IDs padrão (0).")
    GUILD_ID = 0
    CANAL_LOGS_ID = 0
    TICKET_CATEGORY_ID = 0

# O Token do Bot é lido do ambiente (Railway ou .env)
TOKEN = os.getenv("DISCORD_TOKEN")

# Se o token não for encontrado, o programa deve sair.
if not TOKEN:
    print("❌ ERRO: DISCORD_TOKEN não encontrado. Verifique seu .env ou variáveis do Railway.")
    exit(1)

# 2. Configuração do Bot e Intenções
# Adicione intents de mensagem e presença se precisar delas
intents = discord.Intents.default()
intents.members = True # Necessário para XP, moderação, etc.
intents.message_content = True # Necessário para XP, autoresponse, etc.

bot = commands.Bot(command_prefix="!", intents=intents)

# Lista de Cogs
# COGS deve listar seus cogs na ordem de carregamento
COGS = [
    'tickets', 
    'admin', 
    # 'ai',   # <--- Deixamos este cog COMENTADO até confirmarmos a estabilidade total
    'autoresponse', 
    'moderation', 
    'xp', 
    'comandos',
]

# 3. Bloco de Debug para Variáveis Críticas (Para diagnosticar falhas de ID)
print("-" * 50)
print(f"DEBUG: GUILD_ID lido: {GUILD_ID} (Tipo: {type(GUILD_ID)})")
print(f"DEBUG: CANAL_LOGS_ID lido: {CANAL_LOGS_ID} (Tipo: {type(CANAL_LOGS_ID)})")
print("-" * 50)
# Fim do Bloco de Debug

# 4. Função de Carregamento de Cogs (Robusta)
async def load_cogs(bot: commands.Bot):
    """Carrega todos os cogs com tratamento de erros robusto e logs."""
    
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    
    print("\n--- Iniciando Carregamento de Cogs ---")
    
    for cog_name in COGS:
        module_name = f"cogs.{cog_name}"
        try:
            await bot.load_extension(module_name)
            print(f"[COG] Carregado: {cog_name}.py")
            
        except discord.ext.commands.ExtensionNotFound:
            error_message = f"Cog '{cog_name}' não encontrado."
            print(f"[ERRO] {error_message}")
            if canal_logs:
                await canal_logs.send(f"❌ Falha ao carregar cog: {error_message}")
                
        except Exception as e:
            # Captura falhas de setup (erros síncronos dentro da função setup)
            error_message = f"Cog '{cog_name}' levantou um erro: {type(e).__name__}: {e}"
            
            print(f"[ERRO] Falha ao carregar {cog_name}.py: {error_message}")
            if canal_logs:
                # Tenta enviar o erro para o canal de logs. Captura Forbidden caso o ID do canal esteja errado/permissão.
                try:
                    await canal_logs.send(f"❌ Falha crítica ao carregar o cog `{cog_name}`. Detalhes: `{error_message}`")
                except discord.Forbidden:
                    print(f"⚠️ Aviso: Não foi possível enviar o log de erro para o canal {CANAL_LOGS_ID}. Verifique as permissões.")
                except Exception:
                    pass # Ignora qualquer outra falha no próprio log de erro

# 5. Evento on_ready (Robusto)
@bot.event
async def on_ready():
    print(f"\n🚀 Bot Logado como {bot.user} (ID: {bot.user.id})")
    
    # 1. Carregamento dos Cogs
    await load_cogs(bot)

    # 2. Sincronização de Comandos de Barra
    try:
        if GUILD_ID:
            # Tenta sincronizar comandos para o guild específico (mais rápido)
            guild_obj = discord.Object(id=GUILD_ID)
            await bot.tree.sync(guild=guild_obj)
        else:
            # Sincronização global (se GUILD_ID for 0 ou None, pode demorar até 1 hora)
            await bot.tree.sync()
            
        print("✅ Comandos de barra (slash) sincronizados com sucesso.")
        
    except Exception as e:
        # Captura erros de sincronização (ex: GUILD_ID inválido)
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
        # Inicia o bot com o Token
        bot.run(TOKEN)
    except Exception as e:
        # Captura falhas de conexão ou inicialização (e.g., Token inválido)
        print(f"❌ ERRO FATAL ao iniciar o bot: {type(e).__name__}: {e}")
        exit(1)