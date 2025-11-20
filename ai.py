# cogs/ia.py
import discord
from discord.ext import commands
import os
import openai
import asyncio
from datetime import datetime

OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
if OPENAI_KEY:
    openai.api_key = OPENAI_KEY

CONFIG_CHANNEL_NAME = "config"

def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

async def ask_openai(prompt, model="gpt-3.5-turbo", temperature=0.7, max_tokens=600):
    # Chamada síncrona executada em thread para não bloquear
    def call():
        return openai.ChatCompletion.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
    resp = await asyncio.to_thread(call)
    return resp.choices[0].message["content"].strip()

class IA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # comando !ia
    @commands.command(name="ia")
    async def ia_command(self, ctx, *, pergunta: str):
        if not OPENAI_KEY:
            await ctx.reply("IA não configurada (OPENAI_API_KEY ausente).")
            return
        msg = await ctx.reply("🤖 Processando sua pergunta com a IA... (pode demorar alguns segundos)")
        try:
            resposta = await ask_openai(pergunta)
            # se muito grande, envia em arquivo
            if len(resposta) > 1900:
                with open("resp_ia.txt", "w", encoding="utf-8") as f:
                    f.write(resposta)
                await ctx.send(file=discord.File("resp_ia.txt"))
                os.remove("resp_ia.txt")
            else:
                await ctx.reply(resposta)
            # log
            log_channel = discord.utils.get(ctx.guild.text_channels, name=CONFIG_CHANNEL_NAME)
            if log_channel:
                await log_channel.send(f"[{agora()}] 🤖 IA usada por {ctx.author} em {ctx.channel.mention}\nPergunta: {pergunta}\nResposta: {(resposta[:800] + '...') if len(resposta)>800 else resposta}")
        except Exception as e:
            await ctx.reply("Erro ao consultar a IA.")
            print("Erro IA:", e)

    # responde quando for mencionado
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if self.bot.user.mention in message.content:
            pergunta = message.content.replace(self.bot.user.mention, "").strip()
            if not pergunta:
                await message.channel.send(f"{message.author.mention} Sim? Pergunte algo após me mencionar.")
                return
            if not OPENAI_KEY:
                await message.channel.send("IA não configurada.")
                return
            try:
                await message.channel.trigger_typing()
                resposta = await ask_openai(pergunta)
                await message.reply(resposta)
                # log
                log_channel = discord.utils.get(message.guild.text_channels, name=CONFIG_CHANNEL_NAME)
                if log_channel:
                    await log_channel.send(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] 🤖 Mencionado por {message.author} em {message.channel.mention}\nPergunta: {pergunta}\nResposta: {(resposta[:600] + '...') if len(resposta)>600 else resposta}")
            except Exception as e:
                await message.channel.send("Erro ao consultar a IA.")
                print("Erro IA mention:", e)

async def setup(bot):
    await bot.add_cog(IA(bot))
