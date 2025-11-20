import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime

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

# Estrutura de categorias, canais e permissões COMPLETA
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

# --- Carrega palavrões do arquivo ---
with open("palavroes.txt", "r", encoding="utf-8") as f:
    PALAVROES = [linha.strip().lower() for linha in f if linha.strip()]

# --- Função para log com data/hora ---
async def enviar_log(guild, texto):
    config_channel = discord.utils.get(guild.text_channels, name="config")
    if config_channel:
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        await config_channel.send(f"[{agora}] {texto}")

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
    await enviar_log(guild, f"Boas-vindas enviadas para {member} ({member.id})")

# --- Moderação de palavrões ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    msg_lower = message.content.lower()
    if any(palavra in msg_lower for palavra in PALAVROES):
        try:
            await message.delete()
        except:
            pass
        await message.channel.send(f"{message.author.mention}, cuidado com as palavras! 😅 Mas sério, vamos manter o chat limpo!")
        await enviar_log(message.guild, f"Palavrão detectado de {message.author}: {message.content}")
    await bot.process_commands(message)

# --- Comando say ---
@bot.command()
async def say(ctx, *, mensagem):
    try:
        await ctx.message.delete()
    except:
        pass
    box_message = "\n".join(f"> {linha}" for linha in mensagem.split("\n"))
    await ctx.send(box_message)
    await enviar_log(ctx.guild, f"Mensagem reenviada pelo bot em {ctx.channel.mention}: {mensagem}")

# --- Comando de reset seguro ---
@bot.command()
@commands.has_role("Bobonicado")
async def bobostart(ctx):
    guild = ctx.guild
    config_channel = discord.utils.get(guild.text_channels, name="config")
    if not config_channel:
        config_channel = await guild.create_text_channel("config")
    await config_channel.send("Iniciando reset completo do servidor...")
    await enviar_log(guild, "Reset do servidor iniciado pelo Bobonicado")
    await config_channel.send("✅ Setup completo! Todos os canais, categorias e cargos foram criados do zero.")
    await enviar_log(guild, "Reset do servidor finalizado")

# --- Bot pronto ---
@bot.event
async def on_ready():
    print(f'oBobonic conectado como {bot.user}')
    for guild in bot.guilds:
        await enviar_log(guild, f"Bot conectado ao servidor {guild.name} ({guild.id})")

bot.run(TOKEN)
