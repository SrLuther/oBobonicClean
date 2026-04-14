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
LEADERBOARD_CHANNEL_ID = get_int_env("LEADERBOARD_CHANNEL_ID", 1493443885542674595)

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

# Intervalo de monitoramento RCON (em segundos)
RCON_MONITOR_INTERVAL_SECONDS = get_int_env("RCON_MONITOR_INTERVAL_SECONDS", 30)

# Habilita/desabilita o monitoramento RCON
RCON_MONITOR_ENABLED = os.getenv("RCON_MONITOR_ENABLED", "true").lower() in ("true", "1", "yes")

# Habilita/desabilita o sistema de auto-recovery
RCON_AUTO_RECOVERY_ENABLED = os.getenv("RCON_AUTO_RECOVERY_ENABLED", "true").lower() in ("true", "1", "yes")

# Carrega mapas dinamicamente a partir das variáveis:
#   ARK_MAP1_NAME, ARK_MAP1_PORT, ARK_MAP1_HOST (opc.), ARK_MAP1_PASSWORD (opc.)
#   ARK_MAP2_NAME, ARK_MAP2_PORT, ...
ARK_MAPS: dict[str, dict] = {}
_i = 1
_consecutive_misses = 0
while _consecutive_misses < 3:  # Para após 3 números consecutivos sem entrada
    _name = os.getenv(f"ARK_MAP{_i}_NAME")
    _port = os.getenv(f"ARK_MAP{_i}_PORT")
    if not _name or not _port:
        _i += 1
        _consecutive_misses += 1
        continue
    _consecutive_misses = 0
    ARK_MAPS[_name.lower()] = {
        "name": _name,
        "host": os.getenv(f"ARK_MAP{_i}_HOST", ARK_DEFAULT_HOST),
        "port": int(_port),
        "password": os.getenv(f"ARK_MAP{_i}_PASSWORD", ARK_DEFAULT_PASSWORD),
        # Nome do serviço systemd que controla este mapa (opcional)
        # Exemplo: "ark-theisland.service" ou "ark@theisland.service"
        "service": os.getenv(f"ARK_MAP{_i}_SERVICE", ""),
        "max_players": int(os.getenv(f"ARK_MAP{_i}_MAX_PLAYERS", "50")),
    }
    _i += 1

# ======================================================================
# 6. SISTEMA DE INDICAÇÕES (REFERRALS)
# ======================================================================
REFERRALS_GENERATE_ID_CHANNEL_ID = get_int_env("REFERRALS_GENERATE_ID_CHANNEL_ID", 1490764410845790331)
REFERRALS_FORM_CHANNEL_ID = get_int_env("REFERRALS_FORM_CHANNEL_ID", 1490764475442139248)
REFERRALS_PENDING_CHANNEL_ID = get_int_env("REFERRALS_PENDING_CHANNEL_ID", 1490764547936489564)
REFERRALS_APPROVED_CHANNEL_ID = get_int_env("REFERRALS_APPROVED_CHANNEL_ID", 1490764608342851594)
REFERRALS_LOGS_CHANNEL_ID = get_int_env("REFERRALS_LOGS_CHANNEL_ID", 1490764665167548457)
REFERRALS_RANKING_CHANNEL_ID = get_int_env("REFERRALS_RANKING_CHANNEL_ID", 1490764720518594611)
REFERRALS_ADMIN_ROLE_IDS = [1440828412599210135]  # Cargos que podem gerenciar referências

# ======================================================================
# 7. TWITCH MONITOR
# ======================================================================
TWITCH_CHANNEL_REQUEST = get_int_env("TWITCH_CHANNEL_REQUEST", 1490765000000000000)
TWITCH_CHANNEL_APPROVAL = get_int_env("TWITCH_CHANNEL_APPROVAL", 1490765100000000000)
TWITCH_CHANNEL_NOTIF = get_int_env("TWITCH_CHANNEL_NOTIF", 1490765200000000000)
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "")
TWITCH_ACCESS_TOKEN = os.getenv("TWITCH_ACCESS_TOKEN", "")

# ======================================================================
# 8. LISTA DE COGS
# ======================================================================
COGS = [
    'rcon_monitor',  # Monitoramento RCON automático e painéis
    'ark',       # Integração RCON com servidores ARK: Survival Evolved
    'events',    # Sistema de broadcasts automáticos
    'tickets',   # Só o pacote tickets
    'lojas',     # Sistema de lojas pessoais
    'twitch_monitor', # Monitor de streamers Twitch
    'dinosaur_valuer',  # ✅ Sistema de avaliação de dinossauros (Vanilla only)
    # 'nickname_updater',  # ❌ DESABILITADO: módulo nicknameUpdater removido
    'vip',       # Painel VIP com link para a loja
    'admin', 
    'autoresponse', 
    'moderation', 
    'xp', 
    'comandos',
    'rules',     # Sistema de gerenciamento de regras
    'sales',
    'referrals',  # Sistema de indicações e ranking de referências
    'voicemanager',
    'autoloop',  # Sistema de mensagens automáticas a cada 6 horas
    'changelog', # Sistema de changelog versionado do servidor
]

# ============================================================
# Fim do config.py
# ============================================================
