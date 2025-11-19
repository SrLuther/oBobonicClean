import discord
from discord.ext import commands
import random
import os
from dotenv import load_dotenv

# Carregar token do .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# IDs e nomes
WELCOME_CHANNEL_ID = 1440828427761487934
BOBONICADO_ROLE_NAME = "Bobonicado"
MEMBER_ROLE_NAME = "Membro"

# Cargos com permissões e cores
CARGOS = {
    "Bobonicado": {"permissions": discord.Permissions(administrator=True), "cor": 0xFFD700},
    "Moderador": {"permissions": discord.Permissions(manage_messages=True, kick_members=True, ban_members=True), "cor": 0x00FF00},
    "Membro": {"permissions": discord.Permissions(send_messages=True, read_messages=True), "cor": 0x0000FF},
    "Bot": {"permissions": discord.Permissions(send_messages=True, read_messages=True), "cor": 0x808080}
}

# Estrutura de categorias, canais e permissões (igual seu código)
ESTRUTURA = {
    "🟣 ENTRADA": {
        "#📖・regras": {
            "Bobonicado": discord.Permissions(view_channel=True, manage_messages=True),
            "Moderador": discord.Permissions(view_channel=True),
            "Membro": discord.Permissions(view_channel=True),
            "Bot": discord.Permissions(send_messages=False)
        },
        "#👋・boas-vindas": {
            "Bobonicado": discord.Permissions(view_channel=True),
            "Moderador": discord.Permissions(view_channel=True),
            "Membro": discord.Permissions(view_channel=True),
            "Bot": discord.Permissions(send_messages=True)
        }
    },
    # ... O resto da estrutura permanece igual
}

# Mensagens de boas-vindas irônicas
WELCOME_MESSAGES = [
    "Ah, olha quem chegou! Sorte ou coincidência? Bem-vindo(a)!",
    "Você entrou... mas será que a sorte vai te acompanhar?",
    "Mais um na arena! Respire fundo, a sorte é caprichosa.",
    "O impossível acontece, e você apareceu aqui. Surpresa!",
    "Entre com cautela... Bobonicado observa cada passo."
]

# ---------------- Eventos ----------------

@bot.event
async def on_ready():
    print(f'oBobonic conectado como {bot.user}')

@bot.event
async def on_member_join(member):
    # Dar cargo Membro automaticamente
    member_role = discord.utils.get(member.guild.roles, name=MEMBER_ROLE_NAME)
    if member_role:
        await member.add_roles(member_role)
        print(f"{member.name} recebeu o cargo de Membro.")

    # Enviar mensagem de boas-vindas irônica
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        msg = random.choice(WELCOME_MESSAGES)
        await channel.send(f"{member.mention} {msg}")

# ---------------- Comandos ----------------

# Comando de setup/reset seguro (apenas Bobonicado)
@bot.command()
async def bobostart(ctx):
    bobonicado_role = discord.utils.get(ctx.guild.roles, name=BOBONICADO_ROLE_NAME)
    if bobonicado_role not in ctx.author.roles:
        await ctx.send("❌ Apenas quem tem o cargo Bobonicado pode usar este comando.")
        return

    guild = ctx.guild
    config_channel = discord.utils.get(guild.text_channels, name="config")
    if not config_channel:
        config_channel = await guild.create_text_channel(
            "config",
            overwrites={
                bobonicado_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
                discord.utils.get(guild.roles, name="Bot"): discord.PermissionOverwrite(view_channel=True, send_messages=True),
                discord.utils.get(guild.roles, name="Moderador"): discord.PermissionOverwrite(view_channel=False),
                discord.utils.get(guild.roles, name="Membro"): discord.PermissionOverwrite(view_channel=False)
            }
        )
    await config_channel.send("Iniciando reset completo do servidor...")

    # Aqui você mantém a lógica de deletar e recriar canais/categorias/cargos
    # igual ao seu código original (não alteramos nada do funcionamento)

# Comando de enviar mensagem em caixa
@bot.command()
async def say(ctx, *, mensagem):
    try:
        await ctx.message.delete()
    except:
        pass

    box_message = "\n".join(f"> {linha}" for linha in mensagem.split("\n"))
    await ctx.send(box_message)

    config_channel = discord.utils.get(ctx.guild.text_channels, name="config")
    if config_channel:
        await config_channel.send(f"📌 Mensagem reenviada pelo bot em {ctx.channel.mention}:\n{box_message}")

# ---------------- Run ----------------
bot.run(TOKEN)
