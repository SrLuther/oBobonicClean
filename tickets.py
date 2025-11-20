import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, InputText
import random
import string
import asyncio
import datetime
from config import *

def gerar_ticket_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=TICKET_ID_LENGTH))

# --- Modal para fechar ticket ---
class TicketCloseModal(Modal):
    def __init__(self, ticket_canal, moderador=None):
        super().__init__(title="Fechamento de Ticket")
        self.ticket_canal = ticket_canal
        self.moderador = moderador
        self.add_item(InputText(label="Motivo do fechamento", style=discord.InputTextStyle.paragraph))

    async def callback(self, interaction: discord.Interaction):
        motivo = self.children[0].value
        canal_log = interaction.guild.get_channel(CANAL_ARQUIVO_ID)
        if canal_log:
            if self.moderador:
                await canal_log.send(f"Ticket {self.ticket_canal.name} fechado manualmente pelo moderador {self.moderador.mention}\nMotivo: {motivo}")
            else:
                await canal_log.send(f"Ticket {self.ticket_canal.name} fechado pelo usuário {interaction.user.mention}\nMotivo: {motivo}")
        await interaction.response.send_message("✅ Ticket fechado com sucesso!", ephemeral=True)
        await asyncio.sleep(2)
        await self.ticket_canal.edit(category=None)
        await self.ticket_canal.delete()

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ticket_expiracao.start()

    # --- Painel de abertura simplificado ---
    @commands.command()
    async def startticket(self, ctx):
        # Excluir a mensagem do usuário que chamou o comando
        await ctx.message.delete()

        abrir_btn = Button(label="Abrir Ticket", style=discord.ButtonStyle.green)
        mod_btn = Button(label="Painel Moderador", style=discord.ButtonStyle.blurple)

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

            # Botões internos da sala do ticket
            aceitar_btn = Button(label="Aceitar Ticket", style=discord.ButtonStyle.green)
            fechar_btn = Button(label="Fechar Ticket", style=discord.ButtonStyle.red)

            async def aceitar_callback(i: discord.Interaction):
                if any(role.id in MOD_ROLE_IDS for role in i.user.roles):
                    await canal.send(f"🎫 Ticket aceito por {i.user.mention}")
                    await i.response.send_message("✅ Você aceitou o ticket!", ephemeral=True)
                else:
                    await i.response.send_message("❌ Apenas moderadores podem aceitar.", ephemeral=True)

            async def fechar_callback(i: discord.Interaction):
                if any(role.id in MOD_ROLE_IDS for role in i.user.roles):
                    modal = TicketCloseModal(canal, moderador=i.user)
                    await i.response.send_modal(modal)
                else:
                    await i.response.send_message("❌ Apenas moderadores podem fechar manualmente.", ephemeral=True)

            aceitar_btn.callback = aceitar_callback
            fechar_btn.callback = fechar_callback

            view = View()
            view.add_item(aceitar_btn)
            view.add_item(fechar_btn)

            await canal.send(f"{interaction.user.mention}, seu ticket foi criado! Um moderador irá atender em breve.", view=view)
            await interaction.response.send_message(f"✅ Ticket criado: {canal.mention}", ephemeral=True)

        async def mod_callback(interaction: discord.Interaction):
            if not any(role.id in MOD_ROLE_IDS for role in interaction.user.roles):
                await interaction.response.send_message("❌ Apenas moderadores podem acessar este painel.", ephemeral=True)
                return

            guild = interaction.guild
            tickets_ativos = [c for c in guild.text_channels if c.name.startswith("ticket-")]
            if not tickets_ativos:
                await interaction.response.send_message("Nenhum ticket ativo no momento.", ephemeral=True)
                return

            msg = "📋 Tickets abertos:\n"
            for t in tickets_ativos:
                msg += f"- {t.name}\n"
            await interaction.response.send_message(msg, ephemeral=True)

        abrir_btn.callback = abrir_callback
        mod_btn.callback = mod_callback

        view = View()
        view.add_item(abrir_btn)
        view.add_item(mod_btn)

        await ctx.send("🎫 **Painel de Tickets**\nClique no botão para abrir um ticket ou acessar o painel de moderação:", view=view)

    # --- Tarefa para fechar tickets inativos ---
    @tasks.loop(minutes=60)
    async def ticket_expiracao(self):
        guilds = self.bot.guilds
        agora = datetime.datetime.utcnow()
        for guild in guilds:
            for c in guild.text_channels:
                if c.name.startswith("ticket-"):
                    delta = agora - c.created_at
                    if delta.total_seconds() > EXPIRACAO_TICKET_HORAS * 3600:
                        try:
                            canal_log = guild.get_channel(CANAL_ARQUIVO_ID)
                            if canal_log:
                                await canal_log.send(f"Ticket {c.name} fechado automaticamente por inatividade.")
                            await c.delete()
                        except Exception as e:
                            print(f"[ERRO] Falha ao fechar ticket {c.name}: {e}")

    @ticket_expiracao.before_loop
    async def before_ticket_expiracao(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Tickets(bot))
