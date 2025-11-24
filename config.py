import os
from dotenv import load_dotenv
from datetime import datetime
import pytz

# ============================================================
# Atualizado em: 2025-11-23 23:15 (Horário de Brasília)
# ============================================================

load_dotenv()

def get_int_env(var_name, default_value):
    try:
        value = os.getenv(var_name)
        return int(value) if value else int(default_value)
    except ValueError:
        return int(default_value)

# --- IDs do Servidor e Canais ---
GUILD_ID = get_int_env("GUILD_ID", 1440802112601854159)

# --- Tickets ---
TICKET_CATEGORY_ID = get_int_env("TICKET_CATEGORY_ID", 1441644856429772962)
TICKET_ARCHIVE_CHANNEL_ID = get_int_env("TICKET_ARCHIVE_CHANNEL_ID", 1441236730517655634)
TICKET_NOTIFY_CHANNEL_ID = get_int_env("TICKET_NOTIFY_CHANNEL_ID", 1440918150957891656)
TICKET_ID_LENGTH = get_int_env("TICKET_ID_LENGTH", 5)
EXPIRACAO_TICKET_HORAS = get_int_env("EXPIRACAO_TICKET_HORAS", 48)

# --- Canal de logs ---
CANAL_LOGS_ID = get_int_env("CANAL_LOGS_ID", 1440828555201216582)

# --- Roles ---
MEMBER_ROLE_ID = get_int_env("MEMBER_ROLE_ID", 1440828415103074356)
STAFF_ROLE_ID = get_int_env("STAFF_ROLE_ID", 1440828412599210135)  # Apenas esse cargo pode usar botão STAFF

# --- Lista de Cogs ---
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
