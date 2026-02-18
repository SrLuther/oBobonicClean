import discord
from discord.ui import View, Modal, TextInput
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .tickets_controls import TicketsController

def gerar_view_ticket(controller: 'TicketsController') -> View:
    class AbrirTicketModal(Modal):
        def __init__(self):
            super().__init__(title="Abrir Ticket")
            self.descricao: Any = TextInput(
                label="Descrição breve do problema",
                style=discord.TextStyle.paragraph,
                placeholder="Digite aqui...",
                required=True,
                max_length=500
            )
            self.add_item(self.descricao)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                # Responde imediatamente
                await interaction.response.defer(ephemeral=True)
            except Exception as e:
                print(f"❌ Erro ao fazer defer: {e}")
                return
            
            # Processa em background
            try:
                await controller.criar_ticket(interaction, self.descricao.value)
            except Exception as e:
                print(f"❌ Erro ao criar ticket (background): {e}")
                try:
                    await interaction.followup.send(f"❌ Erro ao processar: {e}", ephemeral=True)
                except Exception:
                    pass

    class AbrirTicketButton(View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, custom_id="abrir_ticket")
        async def abrir_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
            try:
                await interaction.response.send_modal(AbrirTicketModal())
            except discord.errors.InteractionResponded:
                pass
            except Exception as e:
                print(f"❌ Erro ao abrir modal de ticket: {type(e).__name__}: {e}")
                try:
                    await interaction.response.send_message(f"❌ Erro ao abrir ticket: {type(e).__name__}", ephemeral=True)
                except Exception as e2:
                    print(f"❌ Erro ao enviar mensagem de erro: {e2}")

    return AbrirTicketButton()

def gerar_ticket_view(controller: 'TicketsController', canal_ticket: discord.TextChannel, usuario: discord.Member, ticket_id: int | str) -> View:
    class TicketView(View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Fechar", style=discord.ButtonStyle.red)
        async def fechar_button(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
            try:
                await interaction.response.send_message("🔒 Fechando o ticket...", ephemeral=True)
            except Exception:
                pass
            canal = interaction.channel
            if not isinstance(canal, discord.TextChannel):
                if interaction.guild:
                    canal = interaction.guild.get_channel(interaction.channel_id)  # type: ignore[attr-defined]
                if not isinstance(canal, discord.TextChannel):
                    return
            usuario = interaction.user
            if not isinstance(usuario, discord.Member) and interaction.guild:
                usuario = interaction.guild.get_member(usuario.id)  # type: ignore[assignment]
            if not isinstance(usuario, discord.Member):
                return
            await controller.fechar_ticket(canal, usuario, ticket_id)

        @discord.ui.button(label="Assumir", style=discord.ButtonStyle.blurple)
        async def assumir_button(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
            try:
                await interaction.response.send_message("🛡️ Ticket assumido.", ephemeral=True)
            except Exception:
                pass
            canal = interaction.channel
            if not isinstance(canal, discord.TextChannel):
                if interaction.guild:
                    canal = interaction.guild.get_channel(interaction.channel_id)  # type: ignore[attr-defined]
                if not isinstance(canal, discord.TextChannel):
                    return
            usuario = interaction.user
            if not isinstance(usuario, discord.Member) and interaction.guild:
                usuario = interaction.guild.get_member(usuario.id)  # type: ignore[assignment]
            if not isinstance(usuario, discord.Member):
                return
            await controller.assumir_ticket(canal, usuario, ticket_id)

    return TicketView()
