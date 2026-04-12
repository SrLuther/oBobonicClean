# ============================================================
# config.py
# Atualizado em: 2025-11-27 17:05:00 (Horário de Brasília)
# ============================================================

import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env para ambiente de DEV local.
load_dotenv() 

# ======================================================================
# 1. FUNÇÕES AUXILIARES
# ======================================================================
def get_int_env(var_name, default_value):
    """Lê a variável do ambiente e garante que ela seja um número inteiro (ID)."""
    try:
        value = os.getenv(var_name)
        return int(value) if value else int(default_value)
    except ValueError:
        return int(default_value)

# ======================================================================
# 2. CHAVES E SECRETS
# ======================================================================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "token_falso_para_dev")

# ======================================================================
# 3. CONFIGURAÇÕES DO BOT (IDs e Constantes)
# ======================================================================

# --- Servidor ---
GUILD_ID = get_int_env("GUILD_ID", 1440802112601854159)

# --- Canais de mensagens e logs ---
CANAL_PAINEL_ID = get_int_env("CANAL_PAINEL_ID", 1440909767974453328)
CANAL_ARQUIVO_ID = get_int_env("CANAL_ARQUIVO_ID", 1441236730517655634) 
CANAL_STATUS_ID = get_int_env("CANAL_STATUS_ID", 1440828427761487934)
CANAL_LOGS_ID = get_int_env("CANAL_LOGS_ID", 1440828555201216582)
AI_CHANNEL_ID = get_int_env("AI_CHANNEL_ID", 1440828507931410543)
CANAL_PROMO_ID = get_int_env("CANAL_PROMO_ID", 1442151789188350113) 
LOBBY_CHANNEL_ID = get_int_env("LOBBY_CHANNEL_ID", 1440828526478491648)
CANAL_CHANGELOG_ID = get_int_env("CANAL_CHANGELOG_ID", 1477571362636955681)

# --- Tickets ---
TICKET_CATEGORY_ID = get_int_env("TICKET_CATEGORY_ID", 1441644856429772962)
TICKET_ARCHIVE_CHANNEL_ID = get_int_env("TICKET_ARCHIVE_CHANNEL_ID", 1441236730517655634)
TICKET_NOTIFY_CHANNEL_ID = get_int_env("TICKET_NOTIFY_CHANNEL_ID", 1440918150957891656)
EXPIRACAO_TICKET_HORAS = get_int_env("EXPIRACAO_TICKET_HORAS", 48)
TICKET_ID_LENGTH = get_int_env("TICKET_ID_LENGTH", 5)

# --- XP ---
XP_MIN = get_int_env("XP_MIN", 15)
XP_MAX = get_int_env("XP_MAX", 25)
XP_COOLDOWN = get_int_env("XP_COOLDOWN", 60)

# --- XP por voz ---
VOICE_XP_GAIN = get_int_env("VOICE_XP_GAIN", 50)
VOICE_XP_INTERVAL_MIN = get_int_env("VOICE_XP_INTERVAL_MIN", 5)

# --- Recompensas por nível ---
LEVEL_REWARDS = {
    5: 1441984913770549298, 
    10: 1441985070738178048, 
    25: 1441985110315630643, 
    50: 1441985166435418254,
}

# --- Cargos / Roles ---
MEMBER_ROLE_ID = get_int_env("MEMBER_ROLE_ID", 1440828415103074356)
QUARANTINE_ROLE_ID = get_int_env("QUARANTINE_ROLE_ID", 1441973275008831669)

MOD_ROLE_IDS = [1440828410556321882, 1440828412599210135]  # Cargos Moderadores/Admin
STAFF_ROLE_ID = 1440828412599210135  # Único que pode usar botão STAFF no ticket

# --- Canais de leaderboard ---
LEADERBOARD_CHANNEL_ID = get_int_env("LEADERBOARD_CHANNEL_ID", 123456789012345678)

# --- Logs ---
LOG_SEPARATOR = os.getenv("LOG_SEPARATOR", "--------------------------------------------------------")

# ======================================================================
# 5. ARK: SURVIVAL EVOLVED — RCON
# ======================================================================
# Senha e host padrão para todos os mapas (pode ser sobrescrito por mapa)
ARK_DEFAULT_HOST = os.getenv("ARK_HOST", "127.0.0.1")
ARK_DEFAULT_PASSWORD = os.getenv("ARK_RCON_PASSWORD", "")

# Canal exclusivo onde os comandos ARK RCON podem ser usados
ARK_CANAL_RCON_ID = get_int_env("ARK_CANAL_RCON_ID", 1479003271623610428)

# Canal de painéis automáticos (status dos servidores em tempo real)
RCON_DASHBOARDS_CHANNEL_ID = get_int_env("RCON_DASHBOARDS_CHANNEL_ID", 1489699180619239628)

# Carrega mapas dinamicamente a partir das variáveis:
#   ARK_MAP1_NAME, ARK_MAP1_PORT, ARK_MAP1_HOST (opc.), ARK_MAP1_PASSWORD (opc.)
#   ARK_MAP2_NAME, ARK_MAP2_PORT, ...
ARK_MAPS: dict[str, dict] = {}
_i = 1
while True:
    _name = os.getenv(f"ARK_MAP{_i}_NAME")
    _port = os.getenv(f"ARK_MAP{_i}_PORT")
    if not _name or not _port:
        break
    ARK_MAPS[_name.lower()] = {
        "name": _name,
        "host": os.getenv(f"ARK_MAP{_i}_HOST", ARK_DEFAULT_HOST),
        "port": int(_port),
        "password": os.getenv(f"ARK_MAP{_i}_PASSWORD", ARK_DEFAULT_PASSWORD),
        # Nome do serviço systemd que controla este mapa (opcional)
        # Exemplo: "ark-theisland.service" ou "ark@theisland.service"
        "service": os.getenv(f"ARK_MAP{_i}_SERVICE", ""),
    }
    _i += 1

# ======================================================================
# 6. LISTA DE COGS (AJUSTADO PARA TICKETS DIVIDIDOS)
# ======================================================================
COGS = [
    'ark',       # Integração RCON com servidores ARK: Survival Evolved
    'tickets',   # Só o pacote tickets
    'lojas',     # Sistema de lojas pessoais
    # 'dinosaur_valuer',  # ❌ DESABILITADO: módulo dino_calculator removido
    # 'nickname_updater',  # ❌ DESABILITADO: módulo nicknameUpdater removido
    'vip',       # Painel VIP com link para a loja
    'admin', 
    'autoresponse', 
    'moderation', 
    'xp', 
    'comandos',
    'rules',     # Sistema de gerenciamento de regras
    'sales',
    'voicemanager',
    'autoloop',  # Sistema de mensagens automáticas a cada 6 horas
    'music',     # Player de música via YouTube
    'changelog', # Sistema de changelog versionado do servidor
]

# ============================================================
# Fim do config.py
# ============================================================
