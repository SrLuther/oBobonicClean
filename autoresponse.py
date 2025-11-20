# cogs/autoresponse.py
import os
import discord
from discord.ext import commands
import openai
import asyncio

OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
openai.api_key = OPENAI_KEY

CHANNELS_ENV = os.getenv("AUTO_AI_CHANNELS", "")  # ex: "chat-bot,ia-room" (nomes separados por vírgula)
AUTO_CHANNELS = [c.strip().lower() for c in CHANNELS_ENV.split(",") if c.strip()]

async def ask_openai(prompt, model="gpt-3.5-turbo", temperature=0.7, max_tokens=400):
    def call():
        return openai.ChatCompletion.create(model=model, messages=[{"role":"user","content":prompt}], temperature=temperature, max_tokens=max_tokens)
    resp = await asyncio.to_thread(call)
    return resp.choices[0].message["content"].strip()

class AutoResponse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not AUTO_CHANNELS:
            return
        channel_name = message.channel.name.lower()
        if channel_name in AUTO_CHANNELS:
            if not OPENAI_KEY:
                await message.channel.send("IA não configurada.")
                return
            prompt = message.content
            try:
                await message.channel.trigger_typing()
                resposta = await ask_openai(prompt)
                await message.reply(resposta, mention_author=False)
            except Exception as e:
                print("Erro autoresponse:", e)

async def setup(bot):
    await bot.add_cog(AutoResponse(bot))
