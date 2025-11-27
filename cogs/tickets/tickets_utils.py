# ============================================================
# cogs/tickets/tickets_utils.py
# Funções utilitárias do sistema de tickets
# ============================================================

import os
import datetime
import config

TICKET_LOGS_DIR = "tickets_logs"
TICKET_SEQ_FILE = "ticket_sequence.txt"

if not os.path.exists(TICKET_LOGS_DIR):
    os.makedirs(TICKET_LOGS_DIR)

def gerar_ticket_id():
    """Gera ID numérico sequencial persistente."""
    if not os.path.exists(TICKET_SEQ_FILE):
        with open(TICKET_SEQ_FILE, 'w') as f:
            f.write("0")

    with open(TICKET_SEQ_FILE, 'r') as f:
        last_id = int(f.read().strip())

    new_id = last_id + 1

    with open(TICKET_SEQ_FILE, 'w') as f:
        f.write(str(new_id))

    return f"{new_id:03d}"  # pad com zeros

def salvar_log_ticket(ticket_id, conteudo):
    filename = os.path.join(TICKET_LOGS_DIR, f"ticket_{ticket_id}.txt")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    return filename

def is_mod(member):
    """Checa se membro é moderador"""
    return any(role.id in config.MOD_ROLE_IDS for role in member.roles)

def format_timestamp():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
