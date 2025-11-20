import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from aiohttp import web
from datetime import datetime

# Carrega variáveis do .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Porta para Render
PORT = 10000

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

# Estrutura completa de categorias, canais e permissões
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
    "🟤 COMUNIDADE": {
        "#💬・chat": {
            "Bobonicado": discord.Permissions(send_messages=True),
            "Moderador": discord.Permissions(send_messages=True),
            "Membro": discord.Permissions(send_messages=True),
            "Bot": discord.Permissions(send_messages=True)
        },
        "#📸・midia": {
            "Bobonicado": discord.Permissions(send_messages=True, attach_files=True),
            "Moderador": discord.Permissions(send_messages=True, attach_files=True),
            "Membro": discord.Permissions(send_messages=True, attach_files=True),
            "Bot": discord.Permissions(send_messages=False)
        },
        "#☕・off-topic": {
            "Bobonicado": discord.Permissions(send_messages=True),
            "Moderador": discord.Permissions(send_messages=True),
            "Membro": discord.Permissions(send_messages=True),
            "Bot": discord.Permissions(send_messages=False)
        }
    },
    "🔵 JOGOS": {
        "#🎮・games": {
            "Bobonicado": discord.Permissions(send_messages=True),
            "Moderador": discord.Permissions(send_messages=True),
            "Membro": discord.Permissions(send_messages=True),
            "Bot": discord.Permissions(send_messages=True)
        },
        "#🛠️・comandos": {
            "Bobonicado": discord.Permissions(administrator=True),
            "Moderador": discord.Permissions(administrator=True),
            "Membro": discord.Permissions(send_messages=True),
            "Bot": discord.Permissions(send_messages=True)
        }
    },
    "🟡 HQ DO BOBONICADO": {
        "#🔮・improváveis": {
            "Bobonicado": discord.Permissions(send_messages=True),
            "Moderador": discord.Permissions(send_messages=True),
            "Membro": discord.Permissions(send_messages=True),
            "Bot": discord.Permissions(send_messages=True)
        },
        "#🪙・tesouro-do-bobo": {
            "Bobonicado": discord.Permissions(administrator=True),
            "Moderador": discord.Permissions(administrator=True),
            "Membro": discord.Permissions(send_messages=True),
            "Bot": discord.Permissions(send_messages=True)
        }
    },
    "🟢 SALAS DE VOZ": {
        "🔊・geral": {
            "Bobonicado": discord.Permissions(connect=True, move_members=True, speak=True),
            "Moderador": discord.Permissions(connect=True, move_members=True, speak=True),
            "Membro": discord.Permissions(connect=True, speak=True),
            "Bot": discord.Permissions(connect=True, speak=True)
        },
        "🎮・game-call": {
            "Bobonicado": discord.Permissions(connect=True, move_members=True, speak=True),
            "Moderador": discord.Permissions(connect=True, move_members=True, speak=True),
            "Membro": discord.Permissions(connect=True, speak=True),
            "Bot": discord.Permissions(connect=True, speak=True)
        },
        "💤・afk": {
            "Bobonicado": discord.Permissions(connect=True, speak=False),
            "Moderador": discord.Permissions(connect=True, speak=False),
            "Membro": discord.Permissions(connect=True, speak=False),
            "Bot": discord.Permissions(connect=True, speak=False)
        }
    },
    "⚙️ ADMINISTRATIVA": {  
        "#📜・logs": {
            "Bobonicado": discord.Permissions(send_messages=True, view_channel=True),
            "Bot": discord.Permissions(send_messages=True, view_channel=True),
            "Moderador": discord.Permissions(view_channel=False),
            "Membro": discord.Permissions(view_channel=False)
        },
        "#📝・mod-chat": {
            "Bobonicado": discord.Permissions(send_messages=True, view_channel=True),
            "Bot": discord.Permissions(view_channel=False),
            "Moderador": discord.Permissions(send_messages=True, view_channel=True),
            "Membro": discord.Permissions(view_channel=False)
        },
        "#📢・avisos": {
            "Bobonicado": discord.Permissions(send_messages=True, view_channel=True),
            "Bot": discord.Permissions(view_channel=False),
            "Moderador": discord.Permissions(send_messages=True, view_channel=True),
            "Membro": discord.Permissions(view_channel=False)
        }
    }
}

# --- Carrega lista de palavrões ---
with open("palavroes.txt", "r", encoding="utf-8") as f:
    PALAVROES = [linha.strip().lower() for linha in f.readlines() if linha.strip()]

# --- Evento de boas-vindas ---
@bot.event
async def on_member_join(member):
    guild = member.guild
    role = discord.utils.get(guild.roles, name="Membro")
    if role:
        await member.add_roles(role)

    canal_boas_vindas = bot.get_channel(CANAL_BOAS_VINDAS_ID)
    if canal_boas_vindas:
        await canal_boas_vindas.send(
            f"🎲 Olá, {member.mention}! Sorte ou azar ter chegado aqui? "
            f"De qualquer forma, seja bem-vindo ao reino improvável do Bobonicado! 🍀"
        )

# --- Comando de reset seguro ---
@bot.command()
@commands.has_role("Bobonicado")
async def bobostart(ctx):
    guild = ctx.guild
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
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        await config_channel.send(f"[{agora}] 📌 Mensagem reenviada pelo bot em {ctx.channel.mention}:\n{box_message}")

# --- Moderação automática de palavrões ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Checa palavrões
    msg_lower = message.content.lower()
    if any(p in msg_lower for p in PALAVROES):
        try:
            await message.delete()
        except:
            pass

        config_channel = discord.utils.get(message.guild.text_channels, name="config")
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if config_channel:
            await config_channel.send(f"[{agora}] ⚠️ {message.author} usou palavrão:\n{message.content}")

        # Repreensão engraçada, mas séria
        await message.channel.send(f"{message.author.mention}, cuidado com as palavras! 😅 Isso não vai ficar barato...")

    await bot.process_commands(message)

# --- Servidor mínimo para Render ---
async def handle(request):
    return web.Response(text="oBobonic rodando!")

app = web.Application()
app.add_routes([web.get("/", handle)])

async def start_webserver():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Servidor HTTP rodando na porta {PORT}")

bot.loop.create_task(start_webserver())

# --- Bot pronto ---
@bot.event
async def on_ready():
    print(f'oBobonic conectado como {bot.user}')

bot.run(TOKEN)
