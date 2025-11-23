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
# 1. KEEP-ALIVE (FLASK)
# --------------------
def run_keep_alive():
    app = Flask(__name__)

    @app.route('/')
    def home():
        return "Bot is running and healthy!"

    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --------------------
# 2. CONFIG E VARS
# --------------------
load_dotenv()

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

# IDs / Config
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

# Intents & bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

COGS = config.COGS

# Debug
print("-" * 50)
print(f"DEBUG: GUILD_ID: {GUILD_ID}")
print(f"DEBUG: CANAL_LOGS_ID: {CANAL_LOGS_ID}")
print(f"DEBUG: CANAL_PROMO_ID: {CANAL_PROMO_ID}")
print(f"DEBUG: LOBBY_CHANNEL_ID: {LOBBY_CHANNEL_ID}")
print("-" * 50)

# --------------------
# 3. FUNÇÃO DE CARREGAMENTO (MODO OFICIAL)
# --------------------
async def load_cogs(bot: commands.Bot) -> bool:
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    unix_timestamp = int(time.time())
    timestamp_formatado = f"<t:{unix_timestamp}:F>"

    print("\n--- Iniciando Carregamento de Cogs ---")

    all_cogs_loaded = True

    for cog_name in COGS:
        module_name = f"cogs.{cog_name}"
        try:
            # MODO OFICIAL: sem kwargs
            await bot.load_extension(module_name)
            print(f"[COG] Carregado: {cog_name}.py")

            if canal_logs:
                try:
                    await canal_logs.send(f"[{timestamp_formatado}] ✅ Cog **`{cog_name}.py`** carregado com sucesso.")
                except Exception:
                    # Não falha o carregamento por causa de problema ao notificar canal
                    pass

        except Exception as e:
            error_message = f"Erro: {type(e).__name__}: {e}"
            print(f"[ERRO] Falha ao carregar {cog_name}.py: {error_message}")
            all_cogs_loaded = False

            if canal_logs:
                try:
                    await canal_logs.send(f"[{timestamp_formatado}] ❌ Falha crítica ao carregar `{cog_name}`. Verifique o log anexo.")
                except Exception:
                    pass

    print("\n" + "=" * 60)
    print("🎩✨ Bobonicado conferiu o inventário arcano...")
    print(f"Status Final: {'SUCESSO' if all_cogs_loaded else 'FALHA'}")
    print("=" * 60 + "\n")

    return all_cogs_loaded

# --------------------
# 4. EVENTO on_ready
# --------------------
@bot.event
async def on_ready():
    print(f"\n🚀 Bot Logado como {bot.user} (ID: {bot.user.id})")

    # start capture is already called in __main__
    cogs_loaded_successfully = await load_cogs(bot)

    # sincroniza comandos
    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=GUILD_ID)
            await bot.tree.sync(guild=guild_obj)
        else:
            await bot.tree.sync()
        print("✅ Comandos de barra (slash) sincronizados.")
    except Exception as e:
        print(f"❌ ERRO Sincronização: {e}")

    # finaliza captura e envia log
    try:
        log_catcher.stop_capture()
        deploy_log_content = log_catcher.get_log()
    except Exception:
        deploy_log_content = "Erro ao recuperar log."

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
                f"Veja o **log completo** no arquivo anexo:"
            )

            await canal_logs.send(mensagem_deploy, file=log_file)

        except Exception as e:
            # caso falhe ao enviar, reativa captura para não perder erros posteriores
            log_catcher.start_capture()
            print(f"❌ ERRO CRÍTICO ao enviar log para o Discord: {e}")

    status_message = "✅ Bot pronto e rodando!" if cogs_loaded_successfully else "⚠️ Bot rodando (com falhas)!"
    print(status_message)

# --------------------
# 5. EXECUÇÃO PRINCIPAL
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
        try:
            log_catcher.stop_capture()
        except Exception:
            pass
        print(f"❌ ERRO FATAL: {e}")
        exit(1)

# ============================================================
# Atualizado em: 2025-11-23 22:41:53 (Horário de Brasília)
# ============================================================
