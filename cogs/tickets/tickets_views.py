import discord
from discord.ui import View, Button, Modal, TextInput

def gerar_view_ticket(controller):
    class AbrirTicketModal(Modal):
        def __init__(self):
            super().__init__(title="Abrir Ticket")
            self.descricao = TextInput(
                label="Descrição breve do problema",
                style=discord.TextStyle.paragraph,
                placeholder="Digite aqui...",
                required=True,
                max_length=500
            )
            self.add_item(self.descricao)

        async def on_submit(self, interaction: discord.Interaction):
            await controller.criar_ticket(interaction, self.descricao.value)

    class AbrirTicketButton(View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, custom_id="abrir_ticket")
        async def abrir_ticket_button(self, interaction: discord.Interaction, button: Button):
            try:
                await interaction.response.send_modal(AbrirTicketModal())
            except Exception:
                try:
                    await interaction.response.send_message("❌ Não foi possível abrir o modal de ticket.", ephemeral=True)
                except Exception:
                    pass

    return AbrirTicketButton()

def gerar_ticket_view(controller, canal_ticket, usuario, ticket_id):
    class TicketView(View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Fechar", style=discord.ButtonStyle.red)
        async def fechar_button(self, interaction: discord.Interaction, button: Button):
            await controller.fechar_ticket(interaction.channel, interaction.user, ticket_id)

        @discord.ui.button(label="Assumir", style=discord.ButtonStyle.blurple)
        async def assumir_button(self, interaction: discord.Interaction, button: Button):
            await controller.assumir_ticket(interaction.channel, interaction.user, ticket_id)

    return TicketView()
