# ============================================================
# cogs/tickets/tickets_views.py
# Embeds e botões do sistema de tickets
# ============================================================

import discord

# ===================== EMBEDS =====================

def gerar_embed_painel():
    embed = discord.Embed(
        title="🎫 Abrir Ticket",
        description="Para abrir um ticket, clique no botão abaixo e forneça uma breve descrição do assunto.\n"
                    "Nossa equipe irá te atender em breve.",
        color=0x3498db
    )
    embed.set_footer(text="oBobonic - Sistema de Tickets")
    return embed

def gerar_embed_ticket(usuario, ticket_id, assunto):
    embed = discord.Embed(
        title=f"🎫 Ticket #{ticket_id}",
        description=f"Olá {usuario.mention}!\n**Assunto:** {assunto}\n\n"
                    f"Use os botões abaixo conforme necessário.",
        color=0x3498db
    )
    embed.set_footer(text="Sistema de Tickets oBobonic")
    return embed

# ===================== VIEWS =====================

def gerar_view_painel():
    view = discord.ui.View(timeout=None)
    view.add_item(
        discord.ui.Button(
            label="Abrir Ticket",
            style=discord.ButtonStyle.primary,
            custom_id="abrir_ticket"
        )
    )
    return view

def gerar_view_ticket_ativo():
    view = discord.ui.View(timeout=None)
    view.add_item(
        discord.ui.Button(
            label="Fechar Ticket",
            style=discord.ButtonStyle.danger,
            custom_id="fechar_ticket"
        )
    )
    view.add_item(
        discord.ui.Button(
            label="Assumir Ticket",
            style=discord.ButtonStyle.success,
            custom_id="assumir_ticket"
        )
    )
    return view
