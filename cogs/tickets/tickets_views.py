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
            self.add_item(Button(label="Abrir Ticket", style=discord.ButtonStyle.green, custom_id="abrir_ticket"))

        @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, custom_id="abrir_ticket")
        async def abrir_ticket_button(self, button: Button, interaction: discord.Interaction):
            await interaction.response.send_modal(AbrirTicketModal())

    return AbrirTicketButton()

def gerar_ticket_view(controller, canal_ticket, usuario, ticket_id):
    class TicketView(View):
        def __init__(self):
            super().__init__(timeout=None)
            self.add_item(Button(label="Fechar", style=discord.ButtonStyle.red, custom_id=f"fechar_{ticket_id}"))
            self.add_item(Button(label="Assumir", style=discord.ButtonStyle.blurple, custom_id=f"assumir_{ticket_id}"))

        @discord.ui.button(label="Fechar", style=discord.ButtonStyle.red)
        async def fechar_button(self, button: Button, interaction: discord.Interaction):
            await controller.fechar_ticket(interaction.channel, interaction.user, ticket_id)

        @discord.ui.button(label="Assumir", style=discord.ButtonStyle.blurple)
        async def assumir_button(self, button: Button, interaction: discord.Interaction):
            await controller.assumir_ticket(interaction.channel, interaction.user, ticket_id)

    return TicketView()
