import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, InputText
import random
import string
import asyncio
from datetime import datetime, timedelta

# --- Configurações ---
CANAL_LOGS_ID = 1440913008795713689  # Canal para registrar tickets fechados/ações
EXPIRACAO_TICKET_HORAS = 48  # Tempo para deletar tickets inativos

def gerar_ticket_id():
    """Gera um ID aleatório de 5 caracteres para o ticket"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

# --- Modal para fechamento de ticket pelo membro ---
class TicketCloseModal(Modal):
    def __init__(self, ticket_canal: discord.TextChannel):
        super().__init__(title="Fechamento de Ticket")
        self.ticket_canal = ticket_canal
        self.add_item(InputText(label="Motivo do fechamento", style=discord.InputTextStyle.paragraph))

    async def callback(self, interaction: discord.Interaction):
        motivo = self.children[0].value
        canal_log = interaction.guild.get_channel(CANAL_LOGS_ID)
        if canal_log:
            await canal_log.send(f"📌 Ticket **{self.ticket_canal.name}** fechado por {interaction.user.mention}\nMotivo: {motivo}")
        await interaction.response.send_message("✅ Ticket fechado com sucesso!", ephemeral=True)
        await asyncio.sleep(2)
        await self.ticket_canal.delete()

# --- Modal para ação administrativa ---
class TicketAdminModal(Modal):
    def __init__(self, acao: str, ticket_canal: discord.TextChannel):
        super().__init__(title=f"{acao} Ticket")
        self.acao = acao
        self.ticket_canal = ticket_canal
        self.add_item(InputText(label="Feedback do moderador", style=discord.InputTextStyle.paragraph))

    async def callback(self, interaction: discord.Interaction):
        feedback = self.children[0].value
        canal_log = interaction.guild.get_channel(CANAL_LOGS_ID)
        if canal_log:
            await canal_log.send(f"📌 Ticket **{self.ticket_canal.name}** {self.acao.lower()} por {interaction.user.mention}\nFeedback: {feedback}")
        await interaction.response.send_message(f"✅ Ticket {self.acao.lower()} com sucesso!", ephemeral=True)
        if self.acao == "Arquivar":
            await self.ticket_canal.edit(category=None)  # opcional: remover de categoria ativa

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_inactive.start()  # inicia tarefa de limpeza

    # --- Comando para painel interativo ---
    @commands.command()
    async def painelticket(self, ctx):
        """Envia painel interativo para abrir ticket"""
        abrir_btn = Button(label="Abrir Ticket", style=discord.ButtonStyle.green)
        admin_btn = Button(label="Painel Admin", style=discord.ButtonStyle.blurple)

        async def abrir_callback(interaction: discord.Interaction):
            ticket_id = gerar_ticket_id()
            guild = interaction.guild
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            canal = await guild.create_text_channel(
                name=f"ticket-{interaction.user.name}-{ticket_id}",
                overwrites=overwrites
            )

            # Botão de fechamento
            fechar_btn = Button(label="Fechar Ticket", style=discord.ButtonStyle.red)
            async def fechar_callback(fechar_interaction: discord.Interaction):
                modal = TicketCloseModal(canal)
                await fechar_interaction.response.send_modal(modal)
            fechar_btn.callback = fechar_callback

            view = View()
            view.add_item(fechar_btn)
            await canal.send(f"{interaction.user.mention} seu ticket foi criado! Use o botão abaixo para fechar quando terminar.", view=view)
            await interaction.response.send_message(f"Ticket criado em {canal.mention}", ephemeral=True)

        async def admin_callback(interaction: discord.Interaction):
            guild = interaction.guild
            tickets_ativos = [c for c in guild.text_channels if c.name.startswith("ticket-")]
            if not tickets_ativos:
                await interaction.response.send_message("Nenhum ticket ativo no momento.", ephemeral=True)
                return

            view = View()
            for t in tickets_ativos:
                aceitar_btn = Button(label=f"Aceitar {t.name}", style=discord.ButtonStyle.green)
                arquivar_btn = Button(label=f"Arquivar {t.name}", style=discord.ButtonStyle.gray)

                async def aceitar_callback(i, canal=t):
                    modal = TicketAdminModal("Aceitar", canal)
                    await i.response.send_modal(modal)

                async def arquivar_callback(i, canal=t):
                    modal = TicketAdminModal("Arquivar", canal)
                    await i.response.send_modal(modal)

                aceitar_btn.callback = aceitar_callback
                arquivar_btn.callback = arquivar_callback
                view.add_item(aceitar_btn)
                view.add_item(arquivar_btn)

            await interaction.response.send_message("📋 Painel Administrativo de Tickets", view=view, ephemeral=True)

        abrir_btn.callback = abrir_callback
        admin_btn.callback = admin_callback

        view = View()
        view.add_item(abrir_btn)
        view.add_item(admin_btn)
        await ctx.send("🎫 Painel de Tickets - Clique no botão para abrir um ticket ou acessar o painel administrativo:", view=view)

    # --- Tarefa para deletar tickets inativos ---
    @tasks.loop(hours=1)
    async def check_inactive(self):
        for guild in self.bot.guilds:
            for canal in guild.text_channels:
                if canal.name.startswith("ticket-"):
                    delta = datetime.utcnow() - canal.created_at
                    if delta > timedelta(hours=EXPIRACAO_TICKET_HORAS):
                        try:
                            await canal.delete()
                        except:
                            pass

async def setup(bot):
    await bot.add_cog(Tickets(bot))
