# cogs/xp.py
import discord
from discord.ext import commands, tasks
import json
import os
import time

XP_FILE = "xp.json"
COOLDOWN_SECONDS = 60  # tempo mínimo entre ganho de xp por usuário

def load_xp():
    if not os.path.exists(XP_FILE):
        with open(XP_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(XP_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_xp(data):
    with open(XP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def level_from_xp(xp):
    # curva simples: level = floor(sqrt(xp/100)) + 1  (exemplo)
    level = 1
    while xp >= level * 100:
        xp -= level * 100
        level += 1
    return level

class XPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_xp()
        self._last_gain = {}  # user_id -> timestamp

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        uid = str(message.author.id)
        now = time.time()
        last = self._last_gain.get(uid, 0)
        if now - last < COOLDOWN_SECONDS:
            return
        self._last_gain[uid] = now
        user = self.data.get(uid, {"xp": 0, "level": 1})
        user["xp"] = user.get("xp", 0) + 10  # 10 xp por mensagem
        # nivelamento simples
        # enquanto xp >= level*100 -> level up
        while user["xp"] >= user["level"] * 100:
            user["xp"] -= user["level"] * 100
            user["level"] += 1
            try:
                await message.channel.send(f"🎉 {message.author.mention} subiu para o nível {user['level']}!")
            except:
                pass
        self.data[uid] = user
        save_xp(self.data)

    @commands.command(name="xp")
    async def xp_cmd(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        uid = str(member.id)
        user = self.data.get(uid, {"xp": 0, "level": 1})
        await ctx.send(f"{member.mention} — Nível: {user.get('level',1)} • XP: {user.get('xp',0)}")

async def setup(bot):
    await bot.add_cog(XPSystem(bot))
