# cogs/ai.py
import discord
from discord.ext import commands
from google import genai
from google.genai import types
import os
import textwrap
import json
import time

from config import GEMINI_API_KEY, AI_CHANNEL_ID

USAGE_FILE = 'gemini_usage.json'

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"❌ ERRO GEMINI: Falha ao inicializar o cliente Gemini. O Cog AI não funcionará. Erro: {e}")
    client = None

def load_usage_data():
    if not os.path.exists(USAGE_FILE):
        return {"total_tokens": 0, "users": {}}
    try:
        with open(USAGE_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"⚠️ Aviso: Arquivo {USAGE_FILE} corrompido. Iniciando novo rastreamento.")
        return {"total_tokens": 0, "users": {}}

def save_usage_data(data):
    try:
        with open(USAGE_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"❌ ERRO ao salvar dados de uso no JSON: {e}")

def record_usage(user_id, total_tokens):
    data = load_usage_data()
    user_id_str = str(user_id)
    data['total_tokens'] = data.get('total_tokens', 0) + total_tokens
    if user_id_str not in data['users']:
        data['users'][user_id_str] = {"tokens": 0, "last_used": 0}
    data['users'][user_id_str]['tokens'] += total_tokens
    data['users'][user_id_str]['last_used'] = int(time.time())
    save_usage_data(data)

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.chat_history = {}
        self.AI_CHANNEL_ID = AI_CHANNEL_ID

    def split_message(self, text, limit=1990):
        return textwrap.wrap(text, limit, replace_whitespace=False, drop_whitespace=False)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.startswith(self.bot.command_prefix):
            return
        if message.channel.id == self.AI_CHANNEL_ID or self.bot.user.mentioned_in(message):
            prompt = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            if prompt:
                await self.process_ai_request(message.channel, message.author, prompt)

    @commands.command(name="ia", aliases=['chat'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ai(self, ctx, *, prompt: str = None):
        if not prompt:
            await ctx.send("❌ Por favor, forneça um prompt. Ex: `!ia O que é a Teoria da Relatividade?`", delete_after=10)
            return
        await self.process_ai_request(ctx.channel, ctx.author, prompt)

    async def process_ai_request(self, channel, author, prompt):
        if not client:
            return await channel.send("❌ O serviço de IA (Gemini) não está configurado corretamente.", delete_after=10)
        if channel.id not in self.chat_history:
            self.chat_history[channel.id] = client.chats.create(model="gemini-2.5-flash")
        chat = self.chat_history[channel.id]
        async with channel.typing():
            try:
                response = chat.send_message(prompt)
                if response.usage_metadata:
                    total_tokens = response.usage_metadata.total_token_count
                    record_usage(author.id, total_tokens)
                    print(f"[{author.name}] Chat usage recorded: {total_tokens} tokens.")
                conteudo = response.text
                partes = self.split_message(conteudo)
                if not partes:
                    await channel.send("❌ A IA não retornou um conteúdo válido.")
                else:
                    await channel.send(f"🧠 **Resposta para {author.mention}:**\n{partes[0]}")
                    for parte in partes[1:]:
                        await channel.send(f"```{parte}```")
            except Exception as e:
                if channel.id in self.chat_history:
                    del self.chat_history[channel.id]
                print(f"Erro no serviço Gemini Chat: {e}")
                await channel.send(f"❌ Ocorreu um erro ao processar sua solicitação no Gemini: ```{e}```")

    @commands.command(name="imagem", aliases=['img', 'gerar'])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def imagem(self, ctx, *, prompt: str = None):
        if not client:
            return await ctx.send("❌ O serviço Gemini não está configurado. Verifique sua chave API.", delete_after=10)
        if not prompt:
            await ctx.send("❌ Por favor, forneça uma descrição para a imagem. Ex: `!imagem castelo flutuante estilo cyberpunk`", delete_after=10)
            return
        await ctx.send(f"🎨 **Gerando imagem...** Usando Imagen 3.0. Isso pode levar até 60 segundos. (Prompt: *{prompt}*)")
        async with ctx.channel.typing():
            try:
                result = client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=prompt,
                    config=dict(
                        number_of_images=1,
                        output_mime_type="image/jpeg",
                        aspect_ratio="1:1"
                    )
                )
                image_bytes = result.generated_images[0].image.image_bytes
                image_file = discord.File(
                    fp=image_bytes,
                    filename=f"imagem_{ctx.author.id}_{int(time.time())}.jpeg"
                )
                embed = discord.Embed(
                    title="🖼️ Imagem Gerada por Imagen (Gemini)",
                    description=f"**Prompt:** *{prompt}*",
                    color=discord.Color.blue()
                )
                embed.set_image(url=f"attachment://{image_file.filename}")
                embed.set_footer(text=f"Solicitado por: {ctx.author.display_name}")
                await ctx.send(embed=embed, file=image_file)
            except Exception as e:
                print(f"Erro inesperado no comando !imagem com Imagen: {e}")
                await ctx.send("❌ Ocorreu um erro ao tentar gerar a imagem. Verifique se a sua chave Gemini está habilitada para a API Imagen e se o prompt não viola as políticas.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            if ctx.command.name == 'ia':
                await ctx.send(f"⏳ Cooldown no chat. Tente em **{error.retry_after:.1f}s**.", delete_after=5)
            elif ctx.command.name == 'imagem':
                await ctx.send(f"⏳ Geração de imagem em cooldown. Tente em **{error.retry_after:.1f}s**.", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            return
        else:
            print(f"Erro inesperado no comando {ctx.command.name}: {error}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))

# ============================================================
# Atualizado em: 2025-11-23 22:41:53 (Horário de Brasília)
# ============================================================
