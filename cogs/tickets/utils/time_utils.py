# cogs/tickets/utils/time_utils.py
from datetime import datetime
import pytz

tz = pytz.timezone("America/Sao_Paulo")

def now_str():
    """Retorna data/hora no timezone de São Paulo no formato YYYY-MM-DD HH:MM:SS"""
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
