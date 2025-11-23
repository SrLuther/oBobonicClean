# cogs/tickets.py
import discord
from discord.ext import commands, tasks
import asyncio
import time
import io # Necessário para o transcript

# Assumimos que TICKET_CATEGORY_ID, CANAL_LOGS_ID e TICKET_STAFF_ROLE_ID
# são importados ou definidos no config.py
try:
    from config import TICKET_CATEGORY_ID, CANAL_LOGS_ID, TICKET_STAFF_ROLE_ID
except ImportError:
    TICKET_CATEGORY_ID = 0
    CANAL_LOGS_ID = 0
    TICKET_STAFF_ROLE_ID = 0
    
# Dicionário simples para armazenar o último horário de atividade do ticket
ticket_activity = {}

class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    def cog_unload(self):
        self.check_inatividade.cancel()

    # 🛑 CORREÇÃO FINAL: Inicia o loop no on_ready, não no __init__
    @commands.Cog.listener()
    async def on_ready(self):
        # Garante que o loop comece apenas após o bot estar totalmente pronto.
        if not self.check_inatividade.is_running():
            print("[tickets] Tarefa de inatividade iniciada.")
            self.check_inatividade.start()

    # ------------------ Lógica de Inatividade (Robusta) ------------------
    
    @tasks.loop(hours=1)
    async def check_inatividade(self):
        try:
            await self.bot.wait_until_ready()
            
            INACTIVITY_LIMIT = 48 * 3600  # 48 horas em segundos
            current_time = time.time()
            
            # Tenta obter o ID do servidor do bot, assumindo que ele está em um só guild para este contexto
            guild_id = self.bot.GUILD_ID if hasattr(self.bot, 'GUILD_ID') else None
            guild = self.bot.get_guild(guild_id) 
            if not guild:
                return

            category = guild.get_channel(TICKET_CATEGORY_ID)
            if not category:
                return

            for channel in category.channels:
                # Se for um canal de ticket e estiver inativo
                if channel.id in ticket_activity:
                    last_activity = ticket_activity[channel.id]
                    
                    if (current_time - last_activity) > INACTIVITY_LIMIT:
                        
                        await channel.send(
                            "⚠️ **Aviso de Inatividade:** Este ticket está inativo há mais de 48 horas. "
                            "Ele será arquivado em breve se não houver resposta."
                        )
                        del ticket_activity[channel.id] # Prepara para o arquivamento no próximo ciclo
                    
        except Exception as e:
            # Captura a exceção e impede que derrube o bot
            print(f"[tickets] ❌ ERRO CRÍTICO na tarefa de inatividade: {e}. O bot continua rodando.")
            
    # ------------------ Listener de Mensagens para Rastrear Atividade ------------------
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        # Verifica se está em um canal de ticket (dentro da categoria)
        if message.channel.category_id == TICKET_CATEGORY_ID:
            ticket_activity[message.channel.id] = time.time()
            
    # ------------------ Funções Auxiliares ------------------

    async def create_transcript(self, channel: discord.TextChannel):
        """Cria um arquivo de transcript (histórico) das mensagens."""
        transcript = f"Transcript do Ticket: {channel.name}\nCriado em: {channel.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Inverte para que as mensagens mais antigas venham primeiro
        messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
        
        for msg in messages:
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            transcript += f"[{timestamp}] {msg.author.display_name}: {msg.content}\n"
            for attachment in msg.attachments:
                transcript += f"  (Anexo: {attachment.url})\n"
        
        # Cria um arquivo em memória
        file = discord.File(io.StringIO(transcript), filename=f"transcript-{channel.name}.txt")
        return file

    async def send_log(self, action: str, channel: discord.TextChannel, user: discord.Member):
        """Envia um log de ação de ticket para o canal de logs."""
        log_channel = self.bot.get_channel(CANAL_LOGS_ID)
        if log_channel:
            embed = discord.Embed(title="🎫 Log de Ticket", color=discord.Color.dark_green())
            embed.add_field(name="Ação", value=action, inline=True)
            embed.add_field(name="Ticket", value=f"#{channel.name}", inline=True)
            embed.add_field(name="Responsável", value=user.mention, inline=True)
            embed.set_footer(text=f"Ticket ID: {channel.id}")
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                print("❌ Falha ao enviar log. Verifique permissões do canal de logs.")

    # ------------------ Comandos de Ticket (Staff) ------------------

    @commands.command(name="ticketpanel")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx):
        """Envia a mensagem com o botão para abrir um novo ticket."""
        embed = discord.Embed(
            title="Suporte e Ajuda",
            description="Clique no botão abaixo para abrir um novo ticket de suporte. Nossa equipe irá te atender em breve!",
            color=discord.Color.blue()
        )
        
        # View com o botão
        view = TicketView(self.bot, TICKET_CATEGORY_ID, TICKET_STAFF_ROLE_ID)
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()
        await self.send_log("Painel de Tickets enviado", ctx.channel, ctx.author)

    @commands.command(name="fechar")
    async def close_ticket(self, ctx):
        """Remove permissão de envio do usuário no ticket atual."""
        if ctx.channel.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("Este comando só pode ser usado em um canal de ticket.")

        # Obtém o membro que abriu o ticket (assumindo que o nome do canal o contenha)
        try:
            user_id = int(ctx.channel.name.split('-')[-1])
            ticket_opener = ctx.guild.get_member(user_id)
        except ValueError:
            ticket_opener = None # Não foi possível identificar o usuário

        # Remove permissão de envio (fechamento suave)
        await ctx.channel.set_permissions(ticket_opener, send_messages=False)
        await ctx.channel.send(f"🔒 O ticket foi marcado como **FECHADO** por {ctx.author.mention}. "
                               "Nenhuma nova mensagem pode ser enviada, mas o histórico permanece.")
        
        await self.send_log("Ticket Fechado (Suave)", ctx.channel, ctx.author)

    @commands.command(name="reabrir")
    async def reopen_ticket(self, ctx):
        """Reabre um ticket fechado, restaurando permissão de envio."""
        if ctx.channel.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("Este comando só pode ser usado em um canal de ticket.")
        
        # Tenta obter o membro que abriu o ticket
        try:
            user_id = int(ctx.channel.name.split('-')[-1])
            ticket_opener = ctx.guild.get_member(user_id)
        except ValueError:
            return await ctx.send("Não foi possível reabrir o ticket: Usuário do ticket não identificado.")

        # Restaura permissão de envio
        await ctx.channel.set_permissions(ticket_opener, send_messages=True)
        await ctx.channel.send(f"🔓 O ticket foi **REABERTO** por {ctx.author.mention}.")

        await self.send_log("Ticket Reaberto", ctx.channel, ctx.author)

    @commands.command(name="transcript")
    async def transcript_ticket(self, ctx):
        """Gera o histórico de mensagens do ticket e envia para o canal de logs."""
        if ctx.channel.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("Este comando só pode ser usado em um canal de ticket.")

        await ctx.send("⏳ Gerando transcript...")
        file = await self.create_transcript(ctx.channel)
        
        log_channel = self.bot.get_channel(CANAL_LOGS_ID)
        if log_channel:
            await log_channel.send(f"📜 Transcript do ticket #{ctx.channel.name} gerado por {ctx.author.mention}", file=file)
            await ctx.send("✅ Transcript enviado para o canal de logs.")
        else:
            await ctx.send("⚠️ Não foi possível encontrar o canal de logs. O transcript não foi salvo.")

        await self.send_log("Transcript Gerado", ctx.channel, ctx.author)


    @commands.command(name="arquivar", aliases=["deletar", "delete"])
    @commands.has_any_role(TICKET_STAFF_ROLE_ID, "administrator") # Exemplo de verificação de role
    async def archive_ticket(self, ctx):
        """Gera o transcript e deleta o canal do ticket."""
        if ctx.channel.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("Este comando só pode ser usado em um canal de ticket.")

        await ctx.send("⚠️ **AVISO:** Este ticket será ARQUIVADO e o canal DELETADO em 5 segundos. Gere o transcript (`!transcript`) se necessário.")
        await asyncio.sleep(5)
        
        # Gera o transcript antes de deletar
        await self.transcript_ticket(ctx) 
        
        await self.send_log("Ticket Arquivado e Deletado", ctx.channel, ctx.author)
        await ctx.channel.delete()


# ------------------ VIEW (Componentes de Botão) ------------------

class TicketView(discord.ui.View):
    def __init__(self, bot, category_id, staff_role_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.category_id = category_id
        self.staff_role_id = staff_role_id
        
    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket_button")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        category = guild.get_channel(self.category_id)
        member = interaction.user
        
        # 1. Checa se o usuário já tem um ticket aberto na categoria
        for channel in category.channels:
            if f"-{member.id}" in channel.name:
                return await interaction.followup.send("Você já possui um ticket aberto.", ephemeral=True)

        # 2. Cria o canal
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.get_role(self.staff_role_id): discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        
        ticket_channel = await category.create_text_channel(
            name=f"ticket-{member.display_name.lower().replace(' ', '-')}-{member.id}",
            topic=f"Ticket de {member.display_name} | ID: {member.id}",
            overwrites=overwrites
        )

        # 3. Mensagem de Boas-vindas
        await ticket_channel.send(
            f"Bem-vindo {member.mention}! Um membro da equipe <@&{self.staff_role_id}> estará com você em breve. "
            f"Descreva seu problema ou pergunta aqui."
        )

        # 4. Envio de log
        cog = self.bot.get_cog("TicketsCog")
        if cog:
            await cog.send_log("Ticket Aberto", ticket_channel, member)
            
        await interaction.followup.send(f"Ticket aberto em {ticket_channel.mention}", ephemeral=True)


async def setup(bot):
    # Passamos o GUILD_ID para o bot, pois ele é necessário para o transcript/log
    if not hasattr(bot, 'GUILD_ID') and GUILD_ID:
        bot.GUILD_ID = GUILD_ID 
        
    await bot.add_cog(TicketsCog(bot))