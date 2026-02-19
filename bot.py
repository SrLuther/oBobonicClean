# bot.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import time
import threading
import sys
from io import StringIO
import datetime
import config
import certifi

# --------------------
# 1. KEEP-ALIVE (FLASK)
# --------------------
def run_keep_alive():
    try:
        flask_module = __import__('flask')
    except Exception:
        return
    app = flask_module.Flask(__name__)

    @app.route('/')
    def home():
        return "Bot is running and healthy!"
    _ = home.__name__

    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --------------------
# 2. CONFIG E VARS
# --------------------
load_dotenv()

try:
    import os as _os
    _os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    _os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except Exception:
    pass

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
CANAL_PAINEL_ID = config.CANAL_PAINEL_ID  # ID da sala do painel persistente

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
print(f"DEBUG: CANAL_PAINEL_ID: {CANAL_PAINEL_ID}")
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

            if isinstance(canal_logs, discord.TextChannel):
                try:
                    await canal_logs.send(f"[{timestamp_formatado}] ✅ Cog **`{cog_name}.py`** carregado com sucesso.")
                except Exception:
                    pass

        except Exception as e:
            error_message = f"Erro: {type(e).__name__}: {e}"
            print(f"[ERRO] Falha ao carregar {cog_name}.py: {error_message}")
            all_cogs_loaded = False

            if isinstance(canal_logs, discord.TextChannel):
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
# 4. FUNÇÃO PARA RECRIAR TODOS OS PAINEIS
# --------------------
async def recriar_todos_os_painels():
    """
    Recriar painels de lojas e tickets após restart para garantir Views funcionem
    """
    try:
        import asyncio
        await asyncio.sleep(2)  # Aguarda cogs serem carregados
        
        # Recriar painel de tickets
        try:
            cog_tickets = bot.get_cog('TicketsController')
            if cog_tickets and hasattr(cog_tickets, 'recriar_painel_tickets'):
                await cog_tickets.recriar_painel_tickets()
                print("✅ Painels de tickets recriados via bot.py")
        except Exception as e:
            print(f"⚠️ Erro ao recriar painel de tickets: {e}")
        
        # Recriar painel de lojas
        try:
            cog_lojas = bot.get_cog('Lojas')
            if cog_lojas and hasattr(cog_lojas, 'atualizar_painel_lojas'):
                await cog_lojas.atualizar_painel_lojas()
                print("✅ Painels de lojas recriados via bot.py")
        except Exception as e:
            print(f"⚠️ Erro ao recriar painel de lojas: {e}")
            
    except Exception as e:
        print(f"❌ Erro geral ao recriar painels: {e}")

# --------------------
# 4. FUNÇÃO PARA CRIAR O PAINEL PERSISTENTE
# --------------------
async def criar_painel_ticket():
    """
    Cria um painel persistente na sala CANAL_PAINEL_ID com o botão
    para abrir ticket. Se já existir uma mensagem fixa, não cria outra.
    Otimizado: verifica apenas mensagens fixadas.
    """
    try:
        from utils.cache import channel_cache
        canal = channel_cache.get(bot, CANAL_PAINEL_ID) if channel_cache else bot.get_channel(CANAL_PAINEL_ID)
    except ImportError:
        canal = bot.get_channel(CANAL_PAINEL_ID)
    
    if not isinstance(canal, discord.TextChannel):
        print(f"❌ Canal do painel ({CANAL_PAINEL_ID}) não encontrado.")
        return

    # Checa apenas mensagens fixadas (mais eficiente)
    pinned_messages = [msg async for msg in canal.history(limit=50) if msg.pinned]
    if pinned_messages:
        print("✅ Painel já fixado encontrado, pulando criação.")
        return

    from cogs.tickets.tickets_views import gerar_view_ticket
    try:
        from cogs.tickets.tickets_controls import TicketsController
    except Exception:
        print("⚠️ Não foi possível importar TicketsController para validação de tipo.")
        return

    controller = bot.get_cog('TicketsController')
    if not isinstance(controller, TicketsController):
        print("⚠️ TicketsController não encontrado ou tipo inválido; painel não será criado por bot.py.")
        return
    view = gerar_view_ticket(controller)
    painel_msg = await canal.send(
        "🎫 **SISTEMA DE SUPORTE - ABRA SEU TICKET**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**📝 Como Abrir um Ticket:**\n"
        "1️⃣ Clique no botão **Abrir Ticket** abaixo\n"
        "2️⃣ Preencha a descrição do seu problema\n"
        "3️⃣ Um canal privado será criado automaticamente\n"
        "4️⃣ A equipe respondará em breve\n\n"
        "**📋 Dicas Importantes:**\n"
        "✅ **Seja específico:** Descreva o problema com detalhes\n"
        "✅ **Inclua contexto:** O que você estava fazendo quando o problema ocorreu?\n"
        "✅ **Dados úteis:** Screenshots, IDs, links (se aplicável)\n"
        "✅ **Paciência:** Nossa equipe está trabalhando para resolver sua solicitação\n\n"
        "**⚠️ Importante:**\n"
        "❌ Não compartilhe senhas ou dados sensíveis\n"
        "❌ Não mencione membros em tickets (pode bloquear o atendimento)\n"
        "❌ Um ticket por assunto (melhor organização)\n\n"
        "**⏱️ Tempo de Resposta:**\n"
        "⏳ O tempo de resposta varia de alguns minutos a até 24 horas\n"
        "⏳ Isso depende da disponibilidade atual da equipe\n"
        "⏳ Faremos o possível para responder o mais rápido possível!\n\n"
        "**📚 Categorias Comuns:**\n"
        "🐛 Bug Report | 💡 Sugestão | ❓ Dúvida\n"
        "🎮 Acesso | 💰 Pagamento | 📱 Técnico\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n",
        view=view
    )
    await painel_msg.pin()
    print(f"✅ Painel persistente criado e fixado em {canal.name} ({canal.id})")

# --------------------
# 5. EVENTO on_ready
# --------------------
@bot.event
async def on_ready():
    user = bot.user
    print(f"\n🚀 Bot Logado como {user} (ID: {user.id if user else 'desconhecido'})")

    # start capture já chamado no __main__
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

    # recriar todos os painels para garantir Views funcionem
    try:
        await recriar_todos_os_painels()
    except Exception as e:
        print(f"⚠️ ERRO ao recriar painels: {e}")

    # finaliza captura e envia log
    try:
        log_catcher.stop_capture()
        deploy_log_content = log_catcher.get_log()
    except Exception:
        deploy_log_content = "Erro ao recuperar log."

    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    if isinstance(canal_logs, discord.TextChannel):
        try:
            agora = datetime.datetime.now()
            data_formatada = agora.strftime("%d/%m/%Y %H:%M:%S")

            from io import BytesIO
            log_file = discord.File(
                fp=BytesIO(deploy_log_content.encode('utf-8')),
                filename="log_oBobonic.txt"
            )

            mensagem_deploy = (
                f"🤖 **oBobonic** iniciado ou reiniciado em `{data_formatada}`. "
                f"Veja o **log completo** no arquivo anexo:"
            )

            await canal_logs.send(mensagem_deploy, file=log_file)

        except Exception as e:
            log_catcher.start_capture()
            print(f"❌ ERRO CRÍTICO ao enviar log para o Discord: {e}")

    status_message = "✅ Bot pronto e rodando!" if cogs_loaded_successfully else "⚠️ Bot rodando (com falhas)!"
    print(status_message)

# --------------------
# 6. EXECUÇÃO PRINCIPAL
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
# Atualizado em: 2025-11-27
# ============================================================
