# -------------------- CONFIGURAÇÕES DO BOT --------------------

# --- Identificadores Essenciais ---
GUILD_ID = 1440802112601854159           # ID REAL DA SUA GUILDA/SERVIDOR!

# --- Canais --- 
CANAL_PAINEL_ID = 1440909767974453328               # Painel de tickets
CANAL_ARQUIVO_ID = 1441236730517655634              # Canal para tickets arquivados
CANAL_STATUS_ID = 1440828427761487934               # Canal de boas vindas (APENAS Membros, Lista)
TICKET_CATEGORY_ID = 1441644856429772962            # Categoria onde tickets serão criados
TICKET_ARCHIVE_CHANNEL_ID = 1441236730517655634     # Canal de arquivamento de tickets
CANAL_LOGS_ID = 1440828555201216582                 # Canal dedicado para Logs de Carregamento e Alertas!
TICKET_NOTIFY_CHANNEL_ID = 1440918150957891656      # Canal que deve receber notificação de abertura de tickets
AI_CHANNEL_ID = 1440828507931410543                 # Canal onde o bot responderá automaticamente (sem prefixo)

# --- Roles / Cargos ---
MOD_ROLE_IDS = [1440828410556321882, 1440828412599210135]  # Cargos que podem acessar painel administrativo
STAFF_ROLE_ID = [1440828410556321882, 1440828412599210135] # Cargo usado nos tickets para moderadores
MEMBER_ROLE_ID = 1440828415103074356 # Cargo que será aplicado automaticamente a novos membros assim que chegarem
QUARANTINE_ROLE_ID = 1441973275008831669  # Cargo que será usado para quarentena (deve ter permissão mínima)

# --- Configurações de Tickets ---
EXPIRACAO_TICKET_HORAS = 48   # Tempo máximo de inatividade para fechar automaticamente tickets
TICKET_ID_LENGTH = 5          # Tamanho do código de identificação do ticket

# --- Configurações do Sistema de XP --- 

XP_MIN = 15      # Quantidade MÍNIMA de XP ganha por mensagem
XP_MAX = 25      # Quantidade MÁXIMA de XP ganha por mensagem
XP_COOLDOWN = 60 # Cooldown (em segundos) entre ganhos de XP por usuário

# --- Configurações de Recompensas por Nível --- 
#  Mapeia NÍVEL : ID_DO_CARGO (Ex: Nível 5 ganha o Cargo 123)

LEVEL_REWARDS = {
    5: 1441984913770549298,  # Ex: "Membro Ativo"
    10: 1441985070738178048, # Ex: "Veterano"
    25: 1441985110315630643, # Ex: "Mestre do Chat"
    50: 1441985166435418254, # Ex: "Lenda do Servidor"

# --- Configurações de Log ---
LOG_SEPARATOR = "--------------------------------------------------------" 
