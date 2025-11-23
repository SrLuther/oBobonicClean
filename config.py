import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env para ambiente de DEV local.
load_dotenv() 

# ==============================================================================
# 1. FUNÇÕES AUXILIARES
# ==============================================================================
def get_int_env(var_name, default_value):
    """Lê a variável do ambiente e garante que ela seja um número inteiro (ID)."""
    try:
        # Tenta ler do ambiente, usando o default se não encontrar.
        value = os.getenv(var_name)
        # Verifica se o valor lido do ambiente existe. Se sim, usa-o. Se não, usa o default.
        return int(value) if value else int(default_value)
    except ValueError:
        return int(default_value)

# ==============================================================================
# 2. CHAVES E SECRETS (Lidos do Ambiente)
# ==============================================================================
# Lidos EXCLUSIVAMENTE do ambiente (DISCORD_TOKEN e GEMINI_API_KEY)
# A chave GEMINI é lida aqui porque o módulo 'ai.py' a importa.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "chave_gemini_falsa_para_dev")

# ==============================================================================
# 3. CONFIGURAÇÕES DO BOT (IDs e Constantes)
# ==============================================================================

# --- Identificadores Essenciais ---
GUILD_ID = get_int_env("GUILD_ID", 1440802112601854159) # ID do Servidor Principal.

# --- Canais de Mensagens e Logs --- 
CANAL_PAINEL_ID = get_int_env("CANAL_PAINEL_ID", 1440909767974453328) 
CANAL_ARQUIVO_ID = get_int_env("CANAL_ARQUIVO_ID", 1441236730517655634) 
CANAL_STATUS_ID = get_int_env("CANAL_STATUS_ID", 1440828427761487934) 
CANAL_LOGS_ID = get_int_env("CANAL_LOGS_ID", 1440828555201216582) 
AI_CHANNEL_ID = get_int_env("AI_CHANNEL_ID", 1440828507931410543) 
CANAL_PROMO_ID = get_int_env("CANAL_PROMO_ID", 1442151789188350113) # ID de Promoções
LOBBY_CHANNEL_ID = get_int_env("LOBBY_CHANNEL_ID", 1440828526478491648) # 👈 ID do Canal Join-to-Create

# --- Canais e Configurações de Tickets ---
TICKET_CATEGORY_ID = get_int_env("TICKET_CATEGORY_ID", 1441644856429772962) 
TICKET_ARCHIVE_CHANNEL_ID = get_int_env("TICKET_ARCHIVE_CHANNEL_ID", 1441236730517655634) 
TICKET_NOTIFY_CHANNEL_ID = get_int_env("TICKET_NOTIFY_CHANNEL_ID", 1440918150957891656) 
EXPIRACAO_TICKET_HORAS = get_int_env("EXPIRACAO_TICKET_HORAS", 48) 
TICKET_ID_LENGTH = get_int_env("TICKET_ID_LENGTH", 5) 

# --- Canais de XP ---
LEADERBOARD_CHANNEL_ID = get_int_env("LEADERBOARD_CHANNEL_ID", 123456789012345678) 

# --- Roles / Cargos ---
MEMBER_ROLE_ID = get_int_env("MEMBER_ROLE_ID", 1440828415103074356) 
QUARANTINE_ROLE_ID = get_int_env("QUARANTINE_ROLE_ID", 1441973275008831669) 

# --- Arrays e Dicionários (Não lemos do ambiente para simplificar o código) ---
MOD_ROLE_IDS = [1440828410556321882, 1440828412599210135] # Cargos Moderadores/Admin
STAFF_ROLE_ID = [1440828410556321882, 1440828412599210135] # Cargo usado nos tickets

# --- Configurações de XP --- 
XP_MIN = get_int_env("XP_MIN", 15) 
XP_MAX = get_int_env("XP_MAX", 25) 
XP_COOLDOWN = get_int_env("XP_COOLDOWN", 60) 

# --- Configurações de XP por Voz --- 
VOICE_XP_GAIN = get_int_env("VOICE_XP_GAIN", 50) 
VOICE_XP_INTERVAL_MIN = get_int_env("VOICE_XP_INTERVAL_MIN", 5) 

# --- Configurações de Recompensas por Nível (Hardcoded) --- 
LEVEL_REWARDS = {
    5: 1441984913770549298, 
    10: 1441985070738178048, 
    25: 1441985110315630643, 
    50: 1441985166435418254, 
}

# --- Configurações de Log ---
LOG_SEPARATOR = os.getenv("LOG_SEPARATOR", "--------------------------------------------------------")

# ==============================================================================
# 4. LISTA DE COGS (Para o bot.py saber o que carregar)
# ==============================================================================

COGS = [
    'tickets', 
    'admin', 
    'ai',
    'autoresponse', 
    'moderation', 
    'xp', 
    'comandos',
    'sales',
    'voicemanager',
]