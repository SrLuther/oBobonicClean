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
# 4. FUNÇÃO PARA ENVIAR REGRAS
# --------------------
async def enviar_regras_se_necessario():
    """
    Envia as regras na sala 1473500120430673940 se ainda não existirem.
    Verifica apenas a primeira mensagem no histórico para economia de requisições.
    """
    try:
        RULES_CHANNEL_ID = 1473500120430673940
        canal_regras = bot.get_channel(RULES_CHANNEL_ID)
        
        if not isinstance(canal_regras, discord.TextChannel):
            print(f"⚠️ Canal de regras ({RULES_CHANNEL_ID}) não encontrado.")
            return
        
        # Procura por mensagens que contêm "REGRAS:" no conteúdo
        regras_enviada = False
        async for msg in canal_regras.history(limit=20):
            if msg.author.id == bot.user.id and "REGRAS:" in msg.content:
                regras_enviada = True
                break
        
        if regras_enviada:
            print("✅ Regras já enviadas, pulando...")
            return
        
        # Se não encontrou, envia as regras
        regras_completas = """
# 🦕 REGRAS ARKLAND BRASIL – PVE 10x 🦖
**ARK: Survival Evolved | Cluster Completo**

**✅ PVE PURO – Sem PVP, sem grief, cooperação total**  
**Discord:** https://discord.gg/7wPswZkb8z  
**Vigência:** 2026  
**Rates:** 10× | Mods: S+, Dino Storage, SpyGlass

══════════════════════════════════════════════════════════════

## 1. REGRAS BÁSICAS
• Idade mínima: 13 anos  
• Idioma: Português ou Inglês  
• **NUNCA** ataque players, tames ou bases (mesmo offline/soltos) → **BAN PERM**  
• Sem hacks, dupes, glitches, fly, clip → **BAN HWID**  
• Sem spam, flood, caps excessivo ou emotes repetidos → mute/kick  
• Ajude os novos! Cooperação é lei aqui

══════════════════════════════════════════════════════════════

## 2. BASES
• Máximo **3 bases principais** por mapa + secundárias pequenas (10×10)  
• Distância mínima: **200 m** entre tribos diferentes  
• **Proibido bloquear**:
  - Spawns (100 m livre ao redor)
  - Obelisks, beacons, drops, cavernas, boss arenas
  - Nodes iniciais de metal/cristal/obsidiana
• Pillar spam: máximo **50 estruturas vazias** por base  
• Decay: **7 dias**  
• Bases abandonadas (14 dias offline): anuncie no Discord e pode demolir

══════════════════════════════════════════════════════════════

## 3. DINOS & TAMING
• **Tames 100% protegidos** – nunca mate, roube, aggro ou abra inventário  
• Limite: **500 dinos por tribo por mapa**  
• Quilombos/kibble farms: ok, mas sem bloquear caminhos/spawns  
• Transfer cluster: **1 wyvern/rock drake/quetzal por semana** por tribo  
• Proibido deixar tames bloqueando cavernas, obelisks ou arenas

══════════════════════════════════════════════════════════════

## 4. RECURSOS & LOOT
• Sem loot steal (não mate dinos que outro está tameando)  
• Farm público: liberado, mas deixe rotas comuns acessíveis  
• Trades: use o canal #trades | **sem venda por dinheiro real**

══════════════════════════════════════════════════════════════

## 5. TRIBOS & ALIANÇAS
• Máximo **12 membros por tribo**  
• Alianças: até **3 tribos** (declare no Discord)  
• Mesclar ou kick: avise admins com 24h de antecedência  
• Raid interno: proibido – ao sair da tribo leva só itens pessoais

══════════════════════════════════════════════════════════════

## 6. COMPORTAMENTO
• Sem racismo, homofobia, sexismo, bullying, toxicidade ou NSFW  
• Sem propaganda sem permissão dos admins

══════════════════════════════════════════════════════════════

## 7. PUNIÇÕES (progressivas)
Leve (spam, caps) → mute 1h → mute 24h → ban 3 dias  
Média (bloqueio leve, grief) → ban 1 dia → 7 dias → 30 dias  
Grave (matar tame, pillar spam) → ban 7 dias → 30 dias → **PERM**  
Muito grave (PVP, hacks, dupe) → **BAN PERM** imediato  

Apelação → ticket com provas (vídeo/print) – resposta em até 48h

══════════════════════════════════════════════════════════════

## 8. WIPES & EVENTOS
• Wipe mensal: dia **1** de cada mês (aviso com 7 dias)  
• Eventos: toda **sexta às 20h BRT** (rates duplo, boss runs, giveaways)

══════════════════════════════════════════════════════════════

**Resumindo em 3 frases:**
1. Coopere, não atrapalhe ninguém.
2. Respeite os tames e bases dos outros.
3. Qualquer dúvida ou problema → abra ticket!

**Divirta-se no ARKLAND BRASIL!** 🦖✨
"""
        
        # Dividir em mensagens menores se necessário (limite Discord é 2000 caracteres)
        mensagens = []
        pedaco_atual = ""
        
        for linha in regras_completas.split('\n'):
            if len(pedaco_atual) + len(linha) + 1 > 1950:
                if pedaco_atual:
                    mensagens.append(pedaco_atual)
                pedaco_atual = linha
            else:
                pedaco_atual += '\n' + linha if pedaco_atual else linha
        
        if pedaco_atual:
            mensagens.append(pedaco_atual)
        
        # Enviar mensagens
        for msg in mensagens:
            try:
                await canal_regras.send(msg)
            except Exception as e:
                print(f"❌ Erro ao enviar parte das regras: {e}")
        
        print("✅ Regras enviadas com sucesso na sala de regras!")
        
    except Exception as e:
        print(f"❌ Erro ao enviar regras: {e}")
        import traceback
        traceback.print_exc()

# --------------------
# 4. FUNÇÃO PARA RECRIAR TODOS OS PAINEIS
# --------------------
async def recriar_todos_os_painels():
    """
    Recriar painels de lojas e tickets após restart para garantir Views funcionem
    """
    try:
        import asyncio
        await asyncio.sleep(3)  # Aguarda cogs serem carregados
        
        print("\n🔄 [REINICIO] Iniciando recriação de painels...")
        
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            print("⚠️ [REINICIO] Guild não encontrada, pulando recriação de painels")
            return
        
        # ========== RECRIAR PAINEL DE LOJAS ==========
        try:
            from cogs.lojas import ViewCriarLoja
            
            canal_lojas = guild.get_channel(1473763773805363414)  # PANEL_CHANNEL_ID de lojas
            if isinstance(canal_lojas, discord.TextChannel):
                # Deletar mensagens antigas com o botão de lojas
                async for msg in canal_lojas.history(limit=50):
                    if msg.author.id == bot.user.id and msg.components:
                        for component in msg.components:
                            if hasattr(component, 'children'):
                                for child in component.children:
                                    if hasattr(child, 'custom_id') and child.custom_id == "criar_loja_btn":
                                        try:
                                            await msg.unpin()
                                            await msg.delete()
                                            print("✅ [REINICIO] Painel antigo de lojas deletado")
                                        except:
                                            pass
                                        break
                
                # Recriar painel de lojas com nova View
                await asyncio.sleep(1)
                painel_lojas = await canal_lojas.send(
                    "🏪 **SISTEMA DE LOJAS PESSOAIS**\n\n"
                    "═══════════════════════════════════════\n\n"
                    "**Bem-vindo ao sistema de lojas!**\n\n"
                    "Clique no botão abaixo para criar sua própria loja "
                    "e começar a vender seus recursos, dinossauros e serviços.\n\n"
                    "**✨ Como Funciona:**\n"
                    "1️⃣ Clique em \"Criar Minha Loja\"\n"
                    "2️⃣ Defina um nome para sua loja\n"
                    "3️⃣ Um canal exclusivo será criado para você\n"
                    "4️⃣ Publique seus produtos!\n\n"
                    "**⚙️ Gerenciamento:**\n"
                    "• Use `!fecharloja` para encerrar sua loja\n"
                    "• Você é o único que pode postar em sua loja\n"
                    "• Lojas inativas podem ser reabertas\n\n"
                    "**💡 Dicas:**\n"
                    "• Descreva bem seus produtos\n"
                    "• Inclua preços e disponibilidade\n"
                    "• Seja claro na comunicação\n\n"
                    "═══════════════════════════════════════",
                    view=ViewCriarLoja(bot)
                )
                await painel_lojas.pin()
                print("✅ [REINICIO] Painel de lojas recriado com sucesso!")
        except Exception as e:
            print(f"⚠️ [REINICIO] Erro ao recriar painel de lojas: {e}")
        
        # ========== RECRIAR PAINEL DE TICKETS ==========
        try:
            from cogs.tickets.tickets_views import gerar_view_ticket
            from cogs.tickets.tickets_controls import TicketsController
            
            canal_tickets = guild.get_channel(CANAL_PAINEL_ID)  # CANAL_PAINEL_ID para tickets
            if isinstance(canal_tickets, discord.TextChannel):
                # Deletar mensagens antigas com o botão de tickets
                async for msg in canal_tickets.history(limit=50):
                    if msg.author.id == bot.user.id and msg.components:
                        for component in msg.components:
                            if hasattr(component, 'children'):
                                for child in component.children:
                                    if hasattr(child, 'custom_id') and child.custom_id == "abrir_ticket":
                                        try:
                                            await msg.unpin()
                                            await msg.delete()
                                            print("✅ [REINICIO] Painel antigo de tickets deletado")
                                        except:
                                            pass
                                        break
                
                # Recriar painel de tickets com nova View
                await asyncio.sleep(1)
                controller = bot.get_cog('TicketsController')
                if controller:
                    painel_tickets = await canal_tickets.send(
                        "🎟️ **SISTEMA DE TICKETS DE SUPORTE**\n\n"
                        "═══════════════════════════════════════\n\n"
                        "**Bem-vindo ao sistema de suporte!**\n\n"
                        "Clique no botão abaixo para abrir um ticket "
                        "e solicitar ajuda com dúvidas, problemas ou outros assuntos.\n\n"
                        "**✨ Categorias de Suporte:**\n"
                        "📋 Geral • 💰 Financeiro • 📦 Problemas com Kit\n"
                        "🐛 Bug • ⚠️ Denúncia • 💡 Sugestão • 😠 Reclamação • ❓ Outro\n\n"
                        "**✨ Como Funciona:**\n"
                        "1️⃣ Clique em \"Abrir Ticket\"\n"
                        "2️⃣ Escolha a categoria de suporte\n"
                        "3️⃣ Forneça um resumo do seu problema\n"
                        "4️⃣ Um canal privado será criado para você\n"
                        "5️⃣ Um membro da equipe irá ajudá-lo!\n\n"
                        "**⚠️ MATERIAL NECESSÁRIO:**\n"
                        "• **Tenha tudo em mão antes de abrir o ticket!**\n"
                        "• Provas, comprovantes ou evidências relevantes\n"
                        "• Fotos ou prints mostrando o problema\n"
                        "• Recibos ou confirmações de pagamento (se aplicável)\n"
                        "• Informações completas e precisas sobre o caso\n\n"
                        "**⚙️ Gerenciamento do Ticket:**\n"
                        "• Um responsável irá **Assumir** seu atendimento\n"
                        "• Responda rapidamente às questões da equipe\n"
                        "• Envie anexos e evidências conforme solicitado\n"
                        "• Quando resolvido, o ticket será **Fechado**\n"
                        "• Forneça feedback sobre o atendimento\n\n"
                        "**💡 Dicas Importantes:**\n"
                        "• Seja específico e detalhado na descrição\n"
                        "• Não abra múltiplos tickets para o mesmo assunto\n"
                        "• A equipe trabalha o mais rápido possível\n"
                        "• Tickets inativos são automaticamente encerrados\n\n"
                        "═══════════════════════════════════════",
                        view=gerar_view_ticket(controller)
                    )
                    await painel_tickets.pin()
                    print("✅ [REINICIO] Painel de tickets recriado com sucesso!")
        except Exception as e:
            print(f"⚠️ [REINICIO] Erro ao recriar painel de tickets: {e}")
        
        # ========== ENVIAR REGRAS SE NECESSÁRIO ==========
        await enviar_regras_se_necessario()
            
        print("✅ [REINICIO] Recriação de painels concluída!\n")
            
    except Exception as e:
        print(f"❌ [REINICIO] Erro geral ao recriar painels: {e}")
        import traceback
        traceback.print_exc()

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
