import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, InputText
from config import TICKET_CHANNEL_ID, LOG_CHANNEL_ID, MOD_ROLE_ID, EXPIRACAO_TICKET_HORAS
import random
import string
import asyncio

def gerar_ticket_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

# --- Modal para fechar ticket pelo membro ---
class TicketCloseModal(Modal):
    def __init__(self):
        super().__init__(title="Fechamento de Ticket")
        self.add_item(InputText(label="Motivo do fechamento", style=discord.InputTextStyle.paragraph))

    async def callback(self, interaction: discord.Interaction):
        motivo = self.children[0].value
        canal = interaction.channel
        canal_log = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if canal_log:
            await canal_log.send(f"Ticket {canal.name} fechado por {interaction.user.mention}\nMotivo: {motivo}")
        await interaction.response.send_message(f"✅ Ticket fechado com sucesso!", ephemeral=True)
        await asyncio.sleep(2)
        await canal.delete()

# --- Modal para ações de moderação ---
class TicketAdminModal(Modal):
    def __init__(self, acao: str, ticket_canal: discord.TextChannel):
        super().__init__(title=f"{acao} Ticket")
        self.acao = acao
        self.ticket_canal = ticket_canal
        self.add_item(InputText(label="Feedback do moderador", style=discord.InputTextStyle.paragraph))

    async def callback(self, interaction: discord.Interaction):
        feedback = self.children[0].value
        canal_log = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if canal_log:
            await canal_log.send(f"Ticket {self.ticket_canal.name} {self.acao.lower()} por {interaction.user.mention}\nFeedback: {feedback}")
        await interaction.response.send_message(f"✅ Ticket {self.acao.lower()} com sucesso!", ephemeral=True)
        if self.acao == "Arquivar":
            await self.ticket_canal.edit(category=None)  # Remove de categoria ativa

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Envia painel automaticamente ---
    async def enviar_painel(self):
        canal = self.bot.get_channel(TICKET_CHANNEL_ID)
        if canal:
            # Deleta mensagens antigas
            async for msg in canal.history(limit=None):
                await msg.delete()

            abrir_btn = Button(label="Abrir Ticket", style=discord.ButtonStyle.green)
            admin_btn = Button(label="Painel Admin", style=discord.ButtonStyle.blurple)

            async def abrir_callback(interaction: discord.Interaction):
                ticket_id = gerar_ticket_id()
                guild = interaction.guild
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
                }
                canal_ticket = await guild.create_text_channel(
                    name=f"ticket-{interaction.user.name}-{ticket_id}",
                    overwrites=overwrites
                )

                fechar_btn = Button(label="Fechar Ticket", style=discord.ButtonStyle.red)
                async def fechar_callback(fechar_interaction: discord.Interaction):
                    modal = TicketCloseModal()
                    await fechar_interaction.response.send_modal(modal)
                fechar_btn.callback = fechar_callback

                view_ticket = View()
                view_ticket.add_item(fechar_btn)
                await canal_ticket.send(f"{interaction.user.mention} seu ticket foi criado! Use o botão abaixo para fechar quando terminar.", view=view_ticket)
                await interaction.response.send_message(f"Ticket criado em {canal_ticket.mention}", ephemeral=True)

            async def admin_callback(interaction: discord.Interaction):
                # Permite apenas moderadores
                if MOD_ROLE_ID not in [r.id for r in interaction.user.roles]:
                    await interaction.response.send_message("❌ Você não tem permissão para acessar o painel administrativo.", ephemeral=True)
                    return

                guild = interaction.guild
                tickets_ativos = [c for c in guild.text_channels if c.name.startswith("ticket-")]
                if not tickets_ativos:
                    await interaction.response.send_message("Nenhum ticket ativo no momento.", ephemeral=True)
                    return

                view_admin = View()
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
                    view_admin.add_item(aceitar_btn)
                    view_admin.add_item(arquivar_btn)

                await interaction.response.send_message("📋 Painel Administrativo de Tickets", view=view_admin, ephemeral=True)

            abrir_btn.callback = abrir_callback
            admin_btn.callback = admin_callback

            view = View()
            view.add_item(abrir_btn)
            view.add_item(admin_btn)

            await canal.send("🎫 Painel de Tickets - Clique no botão para abrir um ticket ou acessar o painel administrativo:", view=view)

    # --- Comando manual para enviar painel ---
    @commands.command()
    async def startticket(self, ctx):
        await ctx.message.delete()
        await self.enviar_painel()

    # --- Limpeza de mensagens de membros na sala do painel ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == TICKET_CHANNEL_ID and not message.author.bot:
            await message.delete()

async def setup(bot):
    cog = Tickets(bot)
    await bot.add_cog(cog)
    # Envia painel automático quando o bot inicia
    await cog.enviar_painel()
