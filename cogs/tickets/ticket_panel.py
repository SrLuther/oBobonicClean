# cogs/tickets/ticket_panel.py
import discord
from .views.ticket_view import TicketView  # view principal do painel

# Nota: a lógica do comando ticketpanel é implementada no tickets_cog.py para evitar imports circulares.
# Este arquivo existe para centralizar views relacionadas ao painel quando necessário.
