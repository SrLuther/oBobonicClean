# config.py
# Configurações principais do bot e tickets

# --- Canais ---
# Canal onde o painel de tickets será exibido
CANAL_PAINEL_ID = 1440909767974453328  

# Canal onde tickets fechados serão arquivados
CANAL_ARQUIVO_ID = 1440913008795713689  

# Canal para enviar mensagens de status do bot (ex: "o pai tá on!")
CANAL_STATUS_ID = 1440918150957891656  

# --- Roles / Cargos ---
# IDs dos cargos que podem acessar o painel administrativo e aceitar/fechar tickets
MOD_ROLE_IDS = [1440828410556321882, 1440828412599210135]

# --- Configurações de Tickets ---
# Tempo máximo de inatividade para fechar automaticamente o ticket (em horas)
EXPIRACAO_TICKET_HORAS = 48  

# Tamanho do código de identificação do ticket
TICKET_ID_LENGTH = 5
