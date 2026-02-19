import discord
from discord.ui import View, Modal, TextInput, Select
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .tickets_controls import TicketsController

CATEGORIAS_SUPORTE = {
    "geral": "📋 Geral",
    "financeiro": "💰 Financeiro",
    "kit": "📦 Problemas com Kit",
    "bug": "🐛 Bug",
    "denuncia": "⚠️ Denúncia",
    "sugestao": "💡 Sugestão",
    "reclamacao": "😠 Reclamação",
    "outro": "❓ Outro"
}

def gerar_view_ticket(controller: 'TicketsController') -> View:
    class SelecionarCategoriaModal(Modal):
        """Modal com aviso e campo de resumo"""
        def __init__(self, categoria: str):
            super().__init__(title="Abrir Ticket - Resumo")
            self.categoria = categoria
            
            self.resumo: Any = TextInput(
                label="Resumo do Problema/Solicitação",
                style=discord.TextStyle.paragraph,
                placeholder="Descreva brevemente o que você precisa...",
                required=True,
                max_length=500
            )
            self.add_item(self.resumo)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                await interaction.response.defer(ephemeral=True)
            except Exception as e:
                print(f"❌ Erro ao fazer defer: {e}")
                return
            
            try:
                categoria_nome = CATEGORIAS_SUPORTE.get(self.categoria, "Outro")
                descricao = f"**Categoria:** {categoria_nome}\n\n**Resumo:**\n{self.resumo.value}"
                await controller.criar_ticket(interaction, descricao)
            except Exception as e:
                print(f"❌ Erro ao criar ticket (background): {e}")
                try:
                    await interaction.followup.send(f"❌ Erro ao processar: {e}", ephemeral=True)
                except Exception:
                    pass

    class SelecionarCategoriaView(View):
        """View com Select para escolher categoria de suporte"""
        def __init__(self):
            super().__init__(timeout=300)

        @discord.ui.select(
            placeholder="Escolha o tipo de suporte...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Geral", value="geral", emoji="📋"),
                discord.SelectOption(label="Financeiro", value="financeiro", emoji="💰"),
                discord.SelectOption(label="Problemas com Kit", value="kit", emoji="📦"),
                discord.SelectOption(label="Bug", value="bug", emoji="🐛"),
                discord.SelectOption(label="Denúncia", value="denuncia", emoji="⚠️"),
                discord.SelectOption(label="Sugestão", value="sugestao", emoji="💡"),
                discord.SelectOption(label="Reclamação", value="reclamacao", emoji="😠"),
                discord.SelectOption(label="Outro", value="outro", emoji="❓"),
            ]
        )
        async def selecionar_categoria(self, interaction: discord.Interaction, select: Select):
            categoria = select.values[0]
            
            try:
                await interaction.response.send_modal(SelecionarCategoriaModal(categoria))
            except Exception as e:
                print(f"❌ Erro ao abrir modal de categoria: {type(e).__name__}: {e}")
                try:
                    await interaction.response.send_message(
                        f"❌ Erro ao processar: {type(e).__name__}",
                        ephemeral=True
                    )
                except Exception as e2:
                    print(f"❌ Erro ao enviar mensagem de erro: {e2}")

    class AbrirTicketButton(View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(
            label="Abrir Ticket",
            style=discord.ButtonStyle.green,
            custom_id="abrir_ticket",
            emoji="🎟️"
        )
        async def abrir_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
            try:
                await interaction.response.send_message(
                    "📋 **Selecione o tipo de suporte que você precisa:**\n\n"
                    "Escolha a categoria mais apropriada para sua solicitação.",
                    view=SelecionarCategoriaView(),
                    ephemeral=True
                )
            except discord.errors.InteractionResponded:
                pass
            except Exception as e:
                print(f"❌ Erro ao abrir seletor de categoria: {type(e).__name__}: {e}")
                try:
                    await interaction.response.send_message(
                        f"❌ Erro ao abrir ticket: {type(e).__name__}",
                        ephemeral=True
                    )
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
            usuario = interaction.user
            if not isinstance(usuario, discord.Member) and interaction.guild:
                usuario = interaction.guild.get_member(usuario.id)  # type: ignore[assignment]
            if not isinstance(usuario, discord.Member):
                try:
                    await interaction.response.send_message("❌ Erro ao identificar o membro.", ephemeral=True)
                except Exception:
                    pass
                return
            
            # Verificar se é administrador do servidor
            if not usuario.guild_permissions.administrator:
                try:
                    await interaction.response.send_message(
                        "⛔ **Acesso Negado!**\n\n"
                        "Apenas **administradores do servidor** podem assumir tickets.\n"
                        "Se você é parte da equipe de suporte, solicite permissão de administrador.",
                        ephemeral=True
                    )
                except Exception:
                    pass
                return
            
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
            await controller.assumir_ticket(canal, usuario, ticket_id)

    return TicketView()
