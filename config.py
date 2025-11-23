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
        return int(os.getenv(var_name, str(default_value)))
    except ValueError:
        return int(default_value)

# ==============================================================================
# 2. CHAVES E SECRETS (Lidos do Ambiente)
# ==============================================================================
# O bot.py lerá o DISCORD_TOKEN diretamente do ambiente.
# A chave GEMINI é lida aqui porque o módulo 'ai.py' a importa.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "chave_gemini_falsa_para_dev")

# ==============================================================================
# 3. CONFIGURAÇÕES DO BOT (IDs e Constantes)
# ==============================================================================

# --- Identificadores Essenciais ---
GUILD_ID = get_int_env("GUILD_ID", 1440802112601854159) # ID do Servidor Principal.

# --- Canais de Mensagens e Logs --- 
CANAL_PAINEL_ID = get_int_env("CANAL_PAINEL_ID", 1440909767974453328) # Canal onde fica o Painel de Tickets.
CANAL_ARQUIVO_ID = get_int_env("CANAL_ARQUIVO_ID", 1441236730517655634) # Canal para transcripts de tickets arquivados.
CANAL_STATUS_ID = get_int_env("CANAL_STATUS_ID", 1440828427761487934) # Canal de Boas-Vindas/Status do Bot.
CANAL_LOGS_ID = get_int_env("CANAL_LOGS_ID", 1440828555201216582) # Canal para Logs de Carregamento e Alertas de Moderação.
AI_CHANNEL_ID = get_int_env("AI_CHANNEL_ID", 1440828507931410543) # Canal onde a IA responde automaticamente.

# --- Canais e Configurações de Tickets ---
TICKET_CATEGORY_ID = get_int_env("TICKET_CATEGORY_ID", 1441644856429772962) # Categoria onde os tickets são criados.
TICKET_ARCHIVE_CHANNEL_ID = get_int_env("TICKET_ARCHIVE_CHANNEL_ID", 1441236730517655634) # Canal de arquivamento de tickets (cópia de CANAL_ARQUIVO_ID).
TICKET_NOTIFY_CHANNEL_ID = get_int_env("TICKET_NOTIFY_CHANNEL_ID", 1440918150957891656) # Canal para notificação de abertura de tickets.
EXPIRACAO_TICKET_HORAS = get_int_env("EXPIRACAO_TICKET_HORAS", 48) # Tempo (em horas) para fechar tickets inativos.
TICKET_ID_LENGTH = get_int_env("TICKET_ID_LENGTH", 5) # Tamanho do código de identificação do ticket.

# --- Canais de XP ---
LEADERBOARD_CHANNEL_ID = get_int_env("LEADERBOARD_CHANNEL_ID", 123456789012345678) # 🛑 ID do Canal onde o ranking de XP é postado (corrigido para o erro).

# --- Roles / Cargos ---
MEMBER_ROLE_ID = get_int_env("MEMBER_ROLE_ID", 1440828415103074356) # Cargo aplicado a novos membros.
QUARANTINE_ROLE_ID = get_int_env("QUARANTINE_ROLE_ID", 1441973275008831669) # Cargo usado para quarentena (punição).

# --- Arrays e Dicionários (Não lemos do ambiente para simplificar o código) ---
MOD_ROLE_IDS = [1440828410556321882, 1440828412599210135] # Cargos que podem acessar o painel administrativo.
STAFF_ROLE_ID = [1440828410556321882, 1440828412599210135] # Cargo usado nos tickets (moderadores).

# --- Configurações de XP --- 
XP_MIN = get_int_env("XP_MIN", 15) # XP MÍNIMO ganho por mensagem.
XP_MAX = get_int_env("XP_MAX", 25) # XP MÁXIMO ganho por mensagem.
XP_COOLDOWN = get_int_env("XP_COOLDOWN", 60) # Cooldown (segundos) entre ganhos de XP.

# --- Configurações de XP por Voz --- 
VOICE_XP_GAIN = get_int_env("VOICE_XP_GAIN", 50) # XP ganho a cada intervalo.
VOICE_XP_INTERVAL_MIN = get_int_env("VOICE_XP_INTERVAL_MIN", 5) # Intervalo (minutos) para conceder XP por voz.

# --- Configurações de Recompensas por Nível (Hardcoded) --- 
LEVEL_REWARDS = {
    5: 1441984913770549298, 
    10: 1441985070738178048, 
    25: 1441985110315630643, 
    50: 1441985166435418254, 
}

# --- Configurações de Log ---
LOG_SEPARATOR = os.getenv("LOG_SEPARATOR", "--------------------------------------------------------")