from discord.ext import commands
import json
import os

class XPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file = "xp.json"

        if not os.path.exists(self.file):
            with open(self.file, "w") as f:
                json.dump({}, f)

    def add_xp(self, user_id, amount):
        with open(self.file, "r") as f:
            data = json.load(f)

        data[str(user_id)] = data.get(str(user_id), 0) + amount

        with open(self.file, "w") as f:
            json.dump(data, f)

        return data[str(user_id)]

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        xp = self.add_xp(message.author.id, 5)

        if xp % 100 == 0:  # A cada 100 xp
            await message.channel.send(f"🎉 {message.author.mention} upou de nível!")

async def setup(bot):
    await bot.add_cog(XPSystem(bot))
