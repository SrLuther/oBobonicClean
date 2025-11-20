# cogs/tickets.py
import discord
from discord.ext import commands
import asyncio
from datetime import datetime

TICKET_CATEGORY = "🛎️ Tickets"
CONFIG_CHANNEL_NAME = "config"
MOD_ROLE_NAME = "Moderador"

def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ensure_category(self, guild):
        cat = discord.utils.get(guild.categories, name=TICKET_CATEGORY)
        if cat:
            return cat
        return await guild.create_category(TICKET_CATEGORY)

    @commands.command(name="ticket")
    async def ticket(self, ctx, action: str = None, *, assunto: str = None):
        """Uso:
        !ticket open <assunto>
        !ticket close
        """
        if action is None:
            await ctx.send("Use `!ticket open <assunto>` para abrir ou `!ticket close` para fechar.")
            return

        if action.lower() == "open":
            guild = ctx.guild
            author = ctx.author
            cat = await self.ensure_category(guild)
            # permissões
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                self.bot.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            # dá acesso para moderadores
            mod_role = discord.utils.get(guild.roles, name=MOD_ROLE_NAME)
            if mod_role:
                overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            channel_name = f"ticket-{author.name}-{author.discriminator}"
            ch = await guild.create_text_channel(channel_name, category=cat, overwrites=overwrites, topic=f"Ticket de {author} - {assunto or 'Sem assunto'}")
            await ch.send(f"{author.mention} seu ticket foi criado. Moderadores: por favor respondam. Assunto: {assunto or 'Sem assunto'}")
            cfg = discord.utils.get(guild.text_channels, name=CONFIG_CHANNEL_NAME)
            if cfg:
                await cfg.send(f"[{agora()}] 🎫 Ticket aberto: {author} -> {ch.mention} Assunto: {assunto or 'Sem assunto'}")
            await ctx.send(f"{author.mention} ticket criado em {ch.mention}")
            return

        if action.lower() == "close":
            channel = ctx.channel
            if channel.category and channel.category.name == TICKET_CATEGORY or any(r.name == MOD_ROLE_NAME for r in ctx.author.roles):
                await ctx.send("Fechando ticket em 5s...")
                await asyncio.sleep(5)
                cfg = discord.utils.get(ctx.guild.text_channels, name=CONFIG_CHANNEL_NAME)
                if cfg:
                    await cfg.send(f"[{agora()}] 🎟 Ticket fechado: {channel.name} por {ctx.author}")
                await channel.delete()
            else:
                await ctx.send("Somente dentro de um ticket ou por um moderador.")
            return

async def setup(bot):
    await bot.add_cog(Tickets(bot))
