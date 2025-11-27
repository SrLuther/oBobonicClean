import discord

# ======================================================
# EMBED INICIAL
# ======================================================
def gerar_embed_ticket(usuario, ticket_id):
    embed = discord.Embed(
        title=f"🎫 Ticket #{ticket_id}",
        description=f"Olá {usuario.mention}! A equipe irá te atender em breve.\n\n"
                    f"Use o botão abaixo para encerrar seu ticket quando desejar.",
        color=0x3498db
    )
    embed.set_footer(text="Sistema de Tickets oBobonic")
    return embed


# ======================================================
# VIEW DE BOTÕES
# ======================================================
def gerar_view_ticket():
    view = discord.ui.View(timeout=None)

    view.add_item(
        discord.ui.Button(
            label="Encerrar Ticket",
            style=discord.ButtonStyle.danger,
            custom_id="fechar_ticket"
        )
    )

    return view
