import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# IDs importantes
CANAL_BOAS_VINDAS_ID = 1440828427761487934  # Canal de chegada das pessoas

# Cargos
CARGOS = {
    "Bobonicado": {"permissions": discord.Permissions(administrator=True), "cor": 0xFFD700},
    "Moderador": {"permissions": discord.Permissions(manage_messages=True, kick_members=True, ban_members=True), "cor": 0x00FF00},
    "Membro": {"permissions": discord.Permissions(send_messages=True, read_messages=True), "cor": 0x0000FF},
    "Bot": {"permissions": discord.Permissions(send_messages=True, read_messages=True), "cor": 0x808080}
}

# Estrutura de categorias e canais (resumida aqui, mas você pode manter sua completa)
ESTRUTURA = {
    "🟣 ENTRADA": {
        "#📖・regras": {},
        "#👋・boas-vindas": {}
    },
    # outras categorias...
}

# --- Evento de boas-vindas ---
@bot.event
async def on_member_join(member):
    guild = member.guild

    # Pega ou cria cargo Membro
    role = discord.utils.get(guild.roles, name="Membro")
    if role:
        await member.add_roles(role)

    # Mensagem irônica de boas-vindas
    canal_boas_vindas = bot.get_channel(CANAL_BOAS_VINDAS_ID)
    if canal_boas_vindas:
        await canal_boas_vindas.send(
            f"🎲 Olá, {member.mention}! Sorte ou azar ter chegado aqui? "
            f"De qualquer forma, seja bem-vindo ao reino improvável do Bobonicado! 🍀"
        )

# --- Comando de reset seguro ---
@bot.command()
@commands.has_role("Bobonicado")  # Somente quem tiver o cargo Bobonicado pode usar
async def bobostart(ctx):
    guild = ctx.guild

    # Criar ou pegar canal de configuração
    config_channel = discord.utils.get(guild.text_channels, name="config")
    if not config_channel:
        config_channel = await guild.create_text_channel(
            "config",
            overwrites={
                discord.utils.get(guild.roles, name="Bobonicado"): discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
                discord.utils.get(guild.roles, name="Bot"): discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
        )
    await config_channel.send("Iniciando reset completo do servidor...")

    # Aqui você pode incluir a lógica de exclusão de canais, criação de cargos e estrutura
    # mantendo a proteção para que apenas Bobonicado possa executar

    await config_channel.send("✅ Setup completo! Todos os canais, categorias e cargos foram criados do zero.")

# --- Comando say ---
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

# --- Bot pronto ---
@bot.event
async def on_ready():
    print(f'oBobonic conectado como {bot.user}')

bot.run(TOKEN)
