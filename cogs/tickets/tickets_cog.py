# cogs/tickets/tickets_cog.py
import discord
from discord.ext import commands, tasks
import time
import asyncio

import config
from .utils.time_utils import now_str
from .utils.transcript import build_transcript
from .ticket_panel import TicketView

# Mantém registro da última atividade de cada ticket
ticket_activity = {}

class TicketsCog(commands.Cog, name="TicketsCog"):
    def __init__(self, bot):
        self.bot = bot
        # iniciar tarefa de verificação de inatividade
        if not hasattr(self, "check_inatividade") or not self.check_inatividade.is_running():
            self.check_inatividade.start()

    def cog_unload(self):
        if hasattr(self, "check_inatividade") and self.check_inatividade.is_running():
            self.check_inatividade.cancel()

    # ------------------------
    # Verifica inatividade (rodando a cada hora)
    # ------------------------
    @tasks.loop(hours=1)
    async def check_inatividade(self):
        try:
            await self.bot.wait_until_ready()
            INACTIVITY_LIMIT = config.EXPIRACAO_TICKET_HORAS * 3600
            current_time = time.time()
            guild = self.bot.get_guild(config.GUILD_ID)
            if not guild:
                return
            category = guild.get_channel(config.TICKET_CATEGORY_ID)
            if not category:
                return
            for channel in category.channels:
                if channel.id in ticket_activity:
                    last_activity = ticket_activity[channel.id]
                    if (current_time - last_activity) > INACTIVITY_LIMIT:
                        try:
                            await channel.send(
                                f"⚠️ **Aviso de Inatividade:** Este ticket está inativo há mais de {config.EXPIRACAO_TICKET_HORAS} horas.\n"
                                "Ele será arquivado em breve se não houver resposta."
                            )
                        except Exception:
                            # ignore se canal não permitir enviar
                            pass
                        del ticket_activity[channel.id]
        except Exception as e:
            print(f"[tickets] ❌ ERRO CRÍTICO na tarefa de inatividade: {e}. O bot continua rodando.")

    # ------------------------
    # Atualiza atividade quando há mensagens no canal de tickets
    # ------------------------
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        # Alguns canais podem não ter category_id (DMs) - proteger
        try:
            if message.channel.category_id == config.TICKET_CATEGORY_ID:
                ticket_activity[message.channel.id] = time.time()
        except Exception:
            return

    # ------------------------
    # Criação de transcript (utiliza util.transcript.build_transcript)
    # ------------------------
    async def create_transcript(self, channel: discord.TextChannel, feedback: str = None, closed_by: str = None) -> discord.File:
        return await build_transcript(channel, feedback=feedback, closed_by=closed_by)

    # ------------------------
    # Logs (envia embed para canal de logs, se existir)
    # ------------------------
    async def send_log(self, action: str, channel: discord.TextChannel, user: discord.Member):
        log_channel = self.bot.get_channel(config.CANAL_LOGS_ID)
        if log_channel:
            embed = discord.Embed(title="🎫 Log de Ticket", color=discord.Color.dark_green())
            embed.add_field(name="Ação", value=action, inline=True)
            embed.add_field(name="Ticket", value=f"#{channel.name}", inline=True)
            embed.add_field(name="Responsável", value=user.mention, inline=True)
            embed.set_footer(text=f"{now_str()} | Ticket ID: {channel.id}")
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                print("❌ Falha ao enviar log. Verifique permissões do canal de logs.")

    # ------------------------
    # Comando painel principal
    # ------------------------
    @commands.command(name="ticketpanel")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx):
        embed = discord.Embed(
            title="🎫 Sistema de Suporte e Tickets",
            description=(
                "Bem-vindo ao sistema de tickets!\n\n"
                "✅ Para abrir um ticket, clique no botão **Abrir Ticket**.\n"
                "📌 No ticket, você poderá conversar com nossa equipe de suporte.\n"
                "📝 Quando finalizar, clique em **Fechar** para enviar seu feedback e gerar a transcrição.\n"
                "⚠️ O painel STAFF está disponível **apenas para moderadores** e permite ações adicionais.\n\n"
                f"⏰ Data/Hora: {now_str()}"
            ),
            color=discord.Color.blue()
        )
        view = TicketView(self.bot, config.TICKET_CATEGORY_ID, config.STAFF_ROLE_ID)
        await ctx.send(embed=embed, view=view)
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await self.send_log("Painel de Tickets enviado", ctx.channel, ctx.author)


async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
