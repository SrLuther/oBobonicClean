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
📜 INTRODUÇÃO
Bem-vindo ao ARKLAND BRASIL no ARK: Survival Evolved!
Somos um servidor PVE EXCLUSIVO (Player vs Environment), focado em sobrevivência, tame, breeding e diversão em grupo.

🚫 NENHUM PVP permitido. Ataques a jogadores, bases ou tames alheios = BAN PERMANENTE IMEDIATO.
Todas as regras promovem cooperação e fair play. Ignorância NÃO é desculpa.
Idade mínima: 13 anos. Contas falsas ou alts para burlar = ban total.
Linguagem: Português ou Inglês no chat global/proximidade.
Reporte problemas via ticket no Discord com PROVAS OBRIGATÓRIAS (vídeo/screenshot/clips) em até 24h.
Admins são imparciais: Podem inspecionar bases, tribos e inventários por denúncias. Decisões finais.

Objetivo: Comunidade BR amigável, sem griefing, rates 10x para progressão rápida, cluster completo (TheIsland, Ragnarok, Aberration, etc.) e eventos semanais!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**1. REGRAS GERAIS**
1.1. PVE Puro: Proibido qualquer dano a jogadores, tames, estruturas ou itens de outros (mesmo offline/soltos).
1.2. Sem Hacks/Exploits: Cheats, dupes, fly hacks, clipz, bots, god mode ou mods não autorizados = ban HWID permanente.
1.3. Sem Spam/Flood: Caps lock excessivo, spam emotes/chat/voz = kick/mute imediato.
1.4. Logout Protegido: Tames/dinos offline não podem ser aggroados, mortos ou roubados.
1.5. Fair Play Incentivado: Ajude novos players! Doe itens iniciais, coopere em bosses.
1.6. Mods Obrigatórios: Structures Plus (S+), Dino Storage v2, Awesome SpyGlass+. Outros mods proibidos sem aprovação admin.

**2. CONSTRUÇÃO E BASES**
2.1. Limites por Tribo (Cluster Total):
• 3 bases principais por mapa.
• Bases secundárias/forrageiras: Máx. 10x10 foundations.
• Distância Mínima: 200m entre bases de tribos diferentes (medido por admin com fly).

2.2. Proibições de Bloqueio (Griefing):
• Spawns de Players: Raio 100m livre ao redor de TODOS spawns (inicial, beach, etc.).
• Obelisks/Beacons/Drops: Não bloqueie loot drops, supply beacons, explorer notes ou ARK Data.
• Cavernas/Boss Arenas/Artefatos: Acesso livre e direto obrigatório.
• Recursos Públicos: Não bloqueie nodes de metal/cristal/obsidian perto de spawns ou rotas comuns.

2.3. Pillar/Structure Spam: Proibido. Máx. 50 structures não-funcionais (pillars vazios, etc.) por base.
2.4. Decaimento: Structures decaem em 7 dias sem claim. Admins limpam bases abandonadas (14+ dias sem login da tribo).
2.5. Bases Abandonadas: Após 14 dias sem login, qualquer um pode demolir. Anuncie no #avisos do Discord 24h antes.
2.6. Construções em Dinos/Plataformas:
• Rampas OK. Torretas automáticas PROIBIDAS em saddles.
• Não blindar dinos 100% (exponha corpo para fair play).
• Plantas X PROIBIDAS em plataformas/saddles.

**3. CRIATURAS E TAMING**
3.1. Tames 100% Protegidos: NUNCA mate, roube, aggro, abra inventário ou Cryopod de tames alheios (soltos/offline).
3.2. Limite de Tames: 500 por tribo por mapa (Dino Storage conta). Não spam dinos low-tier para encher.
3.3. Quilombos/Kibble Farms: Permitidos em áreas públicas, mas não bloqueie spawns/paths.
3.4. Titans/Boss Dinos: Cooperação incentivada. Não mate tames durante fights.
3.5. Transferências Cluster: 1 Wyvern/Rock Drake/Quetzal por semana por tribo.
Proibido: Deixar tames em cavernas, obelisks, arenas ou missões bloqueando acesso.

**4. RECURSOS, LOOT E TRANSFERÊNCIAS**
4.1. Loot Steal Proibido: Não mate dinos em tame de outros ou roube drops intencionalmente (kill steal).
4.2. Farm Público: OK, mas libere rotas comuns (ex: metal nodes beach).
4.3. Obeliscos/ARK Data: Guarde itens (expiram em 1 semana). Não dupe.
4.4. Trades/Economia: Use #trades no Discord. Sem RMT (real money trading).

**5. TRIBOS, ALIANÇAS E COOPERAÇÃO**
5.1. Limites: Máx. 12 membros por tribo. Alianças: até 3 tribos (declare no #alianças Discord).
5.2. Mesclar/Kick: Notifique admins 24h antes. Líderes respondem por ações de membros.
5.3. Raid Interno: Proibido. Saída de tribo = leva só itens pessoais (sem tames/estruturas).
5.4. Contas Alt: Proibidas para burlar limites. Todas contas em mesma tribo.

**6. EVENTOS E BOSSES**
6.1. Eventos Semanais: Anunciados no Discord (rate duplo, boss runs grátis, giveaways).
6.2. Bosses: Todos podem participar. Coop OK, sem grief (bloquear arena = ban).
6.3. Super Breeds: Permitidos, mas registre no #breeds para verificação admin.

**7. COMPORTAMENTO E COMUNICAÇÃO**
7.1. Chat/Voz/Discord: Sem racismo, sexismo, homofobia, bullying, toxicidade, spam ou NSFW.
7.2. Publicidade: Proibida sem permissão admin.
7.3. Griefing Geral: Qualquer ação para atrapalhar (spam dinos, lag, bloqueio paths) = punição progressiva.

**8. PROIBIÇÕES ESPECIAIS (EXPLOITS E BUGS - Evolved Específicos)**
8.1. Glitches: Dupe (backpack, transfer), mesh building, under-map, tame stacking, C4 spam.
8.2. Crashes/Lag: Não cause intencionalmente (ex: 1000 tames soltando).
8.3. Nomes Ofensivos: Vulgar/racista = rename forçado + ban.
8.4. S+ Específicos: Sem auto-decay abuse ou engrams proibidos.

**9. ADMINISTRAÇÃO, PUNIÇÕES E APELAÇÕES**
9.1. Admins/Mods: Decisões finais. Inspecionam por denúncia (fly, unclaim temp).
9.2. Sistema de Punições Progressivo:
• Leve (spam chat): 1ª Vez - Mute 1h | 2ª Vez - Mute 24h | 3ª Vez - Temp Ban 3 dias
• Média (bloqueio leve, grief): 1ª Vez - Temp Ban 1 dia | 2ª Vez - Temp Ban 7 dias | 3ª Vez - Temp Ban 30 dias
• Grave (tame kill, pillar spam): 1ª Vez - Temp Ban 7 dias | 2ª Vez - Temp Ban 30 dias | 3ª Vez - Ban Perm
• Muito Grave (PVP, hacks): Ban Perm em todas as infrações

9.3. Apelações: Apenas via ticket Discord com provas. Resposta em 48h. Spam = rejeição automática.
9.4. Wipes: Anunciados 7 dias antes no Discord. Exceto emergentes (bugs/hacks).

**10. CONFIGURAÇÕES DO SERVIDOR (10x Rates - Evolved)**
• Taming: 10x
• Harvesting: 10x
• XP: 10x
• Breeding: 10x (maturation/egg)
• Cuddle Interval: 0.1x
• Mating Interval: 0.167x
• Baby Food: 0.5x
• Decay Structures: 7 dias
• Max Players: 50
• Mods: S+, Dino Storage, SpyGlass+
• Cluster Transfer: 1 flyer grande/semana.

⚠️ **Violações = AÇÃO IMEDIATA! Coopere para o melhor PVE BR no ARKLAND BRASIL!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Você concorda com as regras do servidor ao jogar aqui.
📞 Dúvidas? Abra um ticket no #tickets!
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
