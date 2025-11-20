# cogs/admin.py
import discord
from discord.ext import commands
import asyncio
from datetime import datetime

BOBONIC_ROLE = "Bobonicado"
MUTED_ROLE = "Muted"
CONFIG_CHANNEL = "config"

def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def has_bobonic_role(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        return any(r.name == BOBONIC_ROLE for r in ctx.author.roles)

    @commands.command()
    @commands.check(has_bobonic_role)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Sem motivo informado"):
        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member} expulso.")
            cfg = discord.utils.get(ctx.guild.text_channels, name=CONFIG_CHANNEL)
            if cfg:
                await cfg.send(f"[{agora()}] ⛔ Kick: {member} por {ctx.author}. Motivo: {reason}")
        except Exception as e:
            await ctx.send("Erro ao expulsar.")

    @commands.command()
    @commands.check(has_bobonic_role)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Sem motivo informado"):
        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member} banido.")
            cfg = discord.utils.get(ctx.guild.text_channels, name=CONFIG_CHANNEL)
            if cfg:
                await cfg.send(f"[{agora()}] ⛔ Ban: {member} por {ctx.author}. Motivo: {reason}")
        except Exception as e:
            await ctx.send("Erro ao banir.")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, minutes: int = 10):
        guild = ctx.guild
        muted = discord.utils.get(guild.roles, name=MUTED_ROLE)
        if not muted:
            muted = await guild.create_role(name=MUTED_ROLE)
            for ch in guild.channels:
                try:
                    await ch.set_permissions(muted, send_messages=False, speak=False, add_reactions=False)
                except:
                    pass
        try:
            await member.add_roles(muted)
            await ctx.send(f"{member.mention} mutado por {minutes} minutos.")
            cfg = discord.utils.get(ctx.guild.text_channels, name=CONFIG_CHANNEL)
            if cfg:
                await cfg.send(f"[{agora()}] 🔇 Mute: {member} por {minutes} minutos por {ctx.author}")
            await asyncio.sleep(minutes * 60)
            try:
                await member.remove_roles(muted)
                if cfg:
                    await cfg.send(f"[{agora()}] 🔈 Unmute automático: {member}")
            except:
                pass
        except Exception as e:
            await ctx.send("Erro ao mutar.")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = 10):
        try:
            deleted = await ctx.channel.purge(limit=amount)
            await ctx.send(f"🧹 {len(deleted)} mensagens deletadas.", delete_after=5)
            cfg = discord.utils.get(ctx.guild.text_channels, name=CONFIG_CHANNEL)
            if cfg:
                await cfg.send(f"[{agora()}] 🧹 Purge por {ctx.author} em {ctx.channel.mention}: {len(deleted)} mensagens")
        except Exception as e:
            await ctx.send("Erro ao limpar mensagens.")

async def setup(bot):
    await bot.add_cog(Admin(bot))
