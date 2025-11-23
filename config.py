import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env para ambiente de DEV local.
# O Railway/produção irá ignorar este arquivo e usar as variáveis configuradas no painel.
load_dotenv() 

# ------------------------------------------------------------------------------
# Funções Auxiliares
# ------------------------------------------------------------------------------
def get_int_env(var_name, default_value):
    """
    Lê a variável do ambiente e garante que ela seja um número inteiro.
    Se não estiver no ambiente, usa o default_value (seu ID real no código).
    """
    try:
        # Tenta ler do ambiente e converter para INT
        # str(default_value) é usado para garantir que os.getenv receba o valor default como string.
        return int(os.getenv(var_name, str(default_value)))
    except ValueError:
        # Retorna o valor padrão se a conversão falhar (embora improvável para IDs numéricos)
        return int(default_value)

# ------------------------------------------------------------------------------
# 🔑 CHAVES E SECRETS
# ------------------------------------------------------------------------------
# O bot.py lerá o DISCORD_TOKEN diretamente do ambiente.
# A chave GEMINI é lida aqui porque o módulo 'ai.py' a importa diretamente.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "chave_gemini_falsa_para_dev")


# -------------------- CONFIGURAÇÕES DO BOT --------------------

# --- Identificadores Essenciais ---
GUILD_ID = get_int_env("GUILD_ID", 1440802112601854159) # ID REAL DA SUA GUILDA/SERVIDOR!

# --- Canais --- 
CANAL_PAINEL_ID = get_int_env("CANAL_PAINEL_ID", 1440909767974453328) # Painel de tickets
CANAL_ARQUIVO_ID = get_int_env("CANAL_ARQUIVO_ID", 1441236730517655634) # Canal para tickets arquivados
CANAL_STATUS_ID = get_int_env("CANAL_STATUS_ID", 1440828427761487934) # Canal de boas vindas (APENAS Membros, Lista)
TICKET_CATEGORY_ID = get_int_env("TICKET_CATEGORY_ID", 1441644856429772962) # Categoria onde tickets serão criados
# CANAL_ARQUIVO_ID e TICKET_ARCHIVE_CHANNEL_ID parecem ser o mesmo. Mantendo ambos se forem importados separadamente.
TICKET_ARCHIVE_CHANNEL_ID = get_int_env("TICKET_ARCHIVE_CHANNEL_ID", 1441236730517655634) # Canal de arquivamento de tickets
CANAL_LOGS_ID = get_int_env("CANAL_LOGS_ID", 1440828555201216582) # Canal dedicado para Logs de Carregamento e Alertas!
TICKET_NOTIFY_CHANNEL_ID = get_int_env("TICKET_NOTIFY_CHANNEL_ID", 1440918150957891656) # Canal que deve receber notificação de abertura de tickets
AI_CHANNEL_ID = get_int_env("AI_CHANNEL_ID", 1440828507931410543) # Canal onde o bot responderá automaticamente (sem prefixo)

# --- Roles / Cargos ---
# Para listas, mantemos o array hardcoded, pois a leitura via os.getenv exigiria
# uma lógica complexa de parsing (split e conversão).
MOD_ROLE_IDS = [1440828410556321882, 1440828412599210135] # Cargos que podem acessar painel administrativo
STAFF_ROLE_ID = [1440828410556321882, 1440828412599210135] # Cargo usado nos tickets para moderadores
MEMBER_ROLE_ID = get_int_env("MEMBER_ROLE_ID", 1440828415103074356) # Cargo que será aplicado automaticamente a novos membros
QUARANTINE_ROLE_ID = get_int_env("QUARANTINE_ROLE_ID", 1441973275008831669) # Cargo que será usado para quarentena

# --- Configurações de Tickets ---
EXPIRACAO_TICKET_HORAS = get_int_env("EXPIRACAO_TICKET_HORAS", 48) # Tempo máximo de inatividade
TICKET_ID_LENGTH = get_int_env("TICKET_ID_LENGTH", 5) # Tamanho do código de identificação do ticket

# --- Configurações do Sistema de XP --- 
XP_MIN = get_int_env("XP_MIN", 15) # Quantidade MÍNIMA de XP ganha por mensagem
XP_MAX = get_int_env("XP_MAX", 25) # Quantidade MÁXIMA de XP ganha por mensagem
XP_COOLDOWN = get_int_env("XP_COOLDOWN", 60) # Cooldown (em segundos)

# --- Configurações de XP por Voz --- 
VOICE_XP_GAIN = get_int_env("VOICE_XP_GAIN", 50) # XP ganho a cada intervalo de tempo
VOICE_XP_INTERVAL_MIN = get_int_env("VOICE_XP_INTERVAL_MIN", 5) # Intervalo (em minutos)

# --- Configurações de Recompensas por Nível --- 
# Manter o dicionário hardcoded é o mais seguro para evitar erros de sintaxe no ambiente
LEVEL_REWARDS = {
    5: 1441984913770549298, 
    10: 1441985070738178048, 
    25: 1441985110315630643, 
    50: 1441985166435418254, 
}

# --- Configurações de Log ---
LOG_SEPARATOR = os.getenv("LOG_SEPARATOR", "--------------------------------------------------------")