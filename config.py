# -------------------- CONFIGURAÇÕES DO BOT --------------------

# --- Canais ---
CANAL_PAINEL_ID = 1440909767974453328           # Painel de tickets
CANAL_ARQUIVO_ID = 1441236730517655634          # Canal para tickets arquivados
CANAL_STATUS_ID = 1440828555201216582           # Canal de logs do bot (status, carregamento, comandos)
TICKET_CATEGORY_ID = 1441644856429772962        # Categoria onde tickets serão criados
TICKET_ARCHIVE_CHANNEL_ID = 1441236730517655634  # Canal de arquivamento de tickets

# --- Roles / Cargos ---
MOD_ROLE_IDS = [1440828410556321882, 1440828412599210135]  # Cargos que podem acessar painel administrativo
STAFF_ROLE_ID = [1440828410556321882, 1440828412599210135] # Cargo usado nos tickets para moderadores
MEMBER_ROLE_ID = 1440828415103074356 # Cargo que será aplicado automaticamente a novos membros assim que chegarem

# --- Configurações de Tickets ---
EXPIRACAO_TICKET_HORAS = 48   # Tempo máximo de inatividade para fechar automaticamente tickets
TICKET_ID_LENGTH = 5          # Tamanho do código de identificação do ticket