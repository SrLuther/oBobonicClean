import discord
from discord.ext import commands

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ticket(self, ctx):
        guild = ctx.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            ctx.author: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        canal = await guild.create_text_channel(
            name=f"ticket-{ctx.author.name}",
            overwrites=overwrites
        )

        await canal.send(f"{ctx.author.mention} seu ticket foi criado!")

async def setup(bot):
    await bot.add_cog(Tickets(bot))
