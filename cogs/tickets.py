import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, InputText
import random
import string
import asyncio

# --- Configurações ---
TICKET_CHANNEL_ID = 1440909767974453328  # Sala de painel de tickets
TICKET_ARCHIVE_CHANNEL_ID = 1440913008795713689  # Sala de logs / tickets arquivados
MOD_ROLE_NAME = "Moderador"
TICKET_EXPIRATION_HOURS = 48

def gerar_ticket_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

# --- Modal de fechamento ---
class TicketCloseModal(Modal):
    def __init__(self, ticket_channel: discord.TextChannel):
        super().__init__(title="Fechamento de Ticket")
        self.ticket_channel = ticket_channel
        self.add_item(InputText(label="Motivo do fechamento", style=discord.InputTextStyle.paragraph))

    async def callback(self, interaction: discord.Interaction):
        motivo = self.children[0].value
        canal_log = interaction.guild.get_channel(TICKET_ARCHIVE_CHANNEL_ID)
        if canal_log:
            await canal_log.send(f"Ticket {self.ticket_channel.name} fechado por {interaction.user.mention}\nMotivo: {motivo}")
        await interaction.response.send_message("✅ Ticket fechado com sucesso!", ephemeral=True)
        await asyncio.sleep(2)
        await self.ticket_channel.delete()

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def enviar_painel(self):
        canal = self.bot.get_channel(TICKET_CHANNEL_ID)
        if not canal:
            return

        # Deleta mensagens antigas
        async for msg in canal.history(limit=None):
            await msg.delete()

        # Botões
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
                modal = TicketCloseModal(canal_ticket)
                await fechar_interaction.response.send_modal(modal)
            fechar_btn.callback = fechar_callback

            view = View()
            view.add_item(fechar_btn)
            await canal_ticket.send(f"{interaction.user.mention} seu ticket foi criado! Use o botão abaixo para fechar quando terminar.", view=view)
            await interaction.response.send_message(f"Ticket criado em {canal_ticket.mention}", ephemeral=True)

        async def admin_callback(interaction: discord.Interaction):
            role = discord.utils.get(interaction.user.roles, name=MOD_ROLE_NAME)
            if not role:
                await interaction.response.send_message("❌ Você não tem permissão para acessar o painel admin.", ephemeral=True)
                return

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
                    await i.response.send_message(f"Ticket {canal.name} aceito por {i.user.mention}", ephemeral=True)

                async def arquivar_callback(i, canal=t):
                    await i.response.send_message(f"Ticket {canal.name} arquivado. Feedback opcional.", ephemeral=True)

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

        await canal.send(
            "🎫 Painel de Tickets - Clique no botão para abrir um ticket ou acessar o painel administrativo:",
            view=view
        )

    # --- Comando manual ---
    @commands.command()
    async def painelticket(self, ctx):
        await ctx.message.delete()
        await self.enviar_painel()

    # --- Exclui mensagens de membros na sala de tickets ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == TICKET_CHANNEL_ID and not message.author.bot:
            await message.delete()

    # --- Envia painel ao iniciar ---
    @commands.Cog.listener()
    async def on_ready(self):
        await self.enviar_painel()

async def setup(bot):
    await bot.add_cog(Tickets(bot))
