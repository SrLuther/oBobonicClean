# cogs/autoresponse.py
import discord
import random
import json
from discord.ext import commands
from datetime import datetime
from config import CANAL_STATUS_ID, GUILD_ID, MEMBER_ROLE_ID

TARGET_CHANNEL_ID = CANAL_STATUS_ID
DATA_FILE = "bot_data.json"

def get_datetime_pt_br():
    now = datetime.now()
    meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    data_extenso = f"{now.day} de {meses[now.month]} de {now.year}"
    hora = now.strftime("%H:%M:%S")
    return data_extenso, hora, now.timestamp()

def load_data():
    """Carrega dados do bot de forma otimizada."""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "last_member_number": 0,
            "member_data": {},
            "list_message_id": None
        }

def save_data(data):
    """Salva dados do bot de forma otimizada."""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except (IOError, OSError) as e:
        print(f"❌ ERRO ao salvar dados: {e}")

class AutoResponse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        data = load_data()

        self.last_member_number = data.get("last_member_number", 0)
        self.member_data = data.get("member_data", {})
        self.list_message_id = data.get("list_message_id", None)

        self.gatilhos = {
            "oi bot": "Oi! 😄",
            "como vai?": "Eu vou bem, e você?",
            "bobonicado": "Se o impossível aconteceu… foi coisa dele. 😎"
        }

        self.frases_aleatorias = [
            "A sorte é uma visitante frequente neste lugar, mas a sua coragem é a chave que abre todas as portas.",
            "Mesmo quando tudo parece improvável, lembre-se: o inesperado muitas vezes guarda a melhor surpresa.",
            "Hoje, os pequenos gestos podem criar grandes oportunidades. Fique atento, a vida tem senso de humor.",
            "Às vezes, a vitória não está em evitar o caos, mas em dançar com ele sem perder o sorriso.",
            "Seu caminho pode parecer cheio de curvas, mas cada passo é parte do mapa que a sorte traçou para você.",
            "O impossível existe apenas até alguém decidir que ele é possível… e essa pessoa pode ser você.",
            "Mesmo os tropeços carregam aprendizado. A sorte sorri para quem se levanta com leveza.",
            "Hoje é um bom dia para acreditar no improvável: o universo adora se surpreender com quem acredita.",
            "Não subestime os sinais pequenos; eles muitas vezes escondem portas para grandes conquistas.",
            "Sorria, mesmo que a vida pareça absurda: é nesse instante que a sorte gosta de aparecer."
        ]

    async def update_member_list_message(self, guild):
        """Atualiza mensagem da lista de membros de forma otimizada."""
        try:
            from utils.cache import channel_cache
            list_channel = channel_cache.get(self.bot, TARGET_CHANNEL_ID) if channel_cache else guild.get_channel(TARGET_CHANNEL_ID)
        except ImportError:
            list_channel = guild.get_channel(TARGET_CHANNEL_ID)
        
        data_extenso, hora, _ = get_datetime_pt_br()
        
        if not isinstance(list_channel, discord.TextChannel):
            print(f"ERRO: Canal de lista com ID {TARGET_CHANNEL_ID} não encontrado.")
            return

        member_list_text = ""
        # Otimizado: evita múltiplas buscas de membros, filtra None antes
        member_items = [(num, guild.get_member(int(mid))) for mid, num in self.member_data.items()]
        sorted_members = sorted(
            [(num, mem) for num, mem in member_items if mem is not None],
            key=lambda x: x[0]
        )

        for num, member in sorted_members:
            if member:
                member_list_text += f"`{num}.` **{member.display_name}** ({member.mention})\n"

        if not member_list_text:
            member_list_text = "Nenhum membro registrado ainda."

        embed = discord.Embed(
            title="👤 Lista Oficial de Membros Sequenciais 🔢",
            description=member_list_text,
            color=discord.Color.blue()
        )

        embed.set_footer(
            text=f"Última Edição: {data_extenso} às {hora}"
        )

        try:
            if self.list_message_id:
                message = await list_channel.fetch_message(self.list_message_id)
                await message.edit(embed=embed)
            else:
                message = await list_channel.send(embed=embed)
                self.list_message_id = message.id

        except discord.NotFound:
            print("Mensagem de lista não encontrada, criando uma nova.")
            message = await list_channel.send(embed=embed)
            self.list_message_id = message.id
        except Exception as e:
            print(f"Erro ao editar/criar mensagem de lista: {e}")
            return

        save_data({
            "last_member_number": self.last_member_number,
            "member_data": self.member_data,
            "list_message_id": self.list_message_id
        })

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            print(f"ERRO: Guilda com ID {GUILD_ID} não encontrada. Verifique o GUILD_ID no config.py.")
            return

        if not self.member_data and self.last_member_number == 0:
            print("Inicializando lista de membros com números sequenciais...")
            all_members = [m for m in guild.members if not m.bot]

            for i, member in enumerate(all_members, 1):
                self.member_data[str(member.id)] = i

            self.last_member_number = len(all_members)
            print(f"Lista inicializada. Total de membros: {self.last_member_number}")

            save_data({
                "last_member_number": self.last_member_number,
                "member_data": self.member_data,
                "list_message_id": self.list_message_id
            })

        await self.update_member_list_message(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return

        self.last_member_number += 1
        member_number = self.last_member_number
        self.member_data[str(member.id)] = member_number

        try:
            try:
                from utils.cache import role_cache
                role = role_cache.get(member.guild, MEMBER_ROLE_ID) if role_cache else member.guild.get_role(MEMBER_ROLE_ID)
            except ImportError:
                role = member.guild.get_role(MEMBER_ROLE_ID)
            
            if role:
                await member.add_roles(role)
                print(f"[CARGO] Concedido '{role.name}' a {member.name}")
            else:
                print(f"[ALERTA] Cargo com ID {MEMBER_ROLE_ID} não encontrado.")
        except Exception as e:
            print(f"[ERRO CARGO] Falha ao adicionar cargo a {member.name}: {e}")

        try:
            from utils.cache import channel_cache
            canal_boas_vindas = channel_cache.get(self.bot, TARGET_CHANNEL_ID) if channel_cache else member.guild.get_channel(TARGET_CHANNEL_ID)
        except ImportError:
            canal_boas_vindas = member.guild.get_channel(TARGET_CHANNEL_ID)

        if canal_boas_vindas:
            data_extenso, hora, _ = get_datetime_pt_br()
            frase_final = random.choice(self.frases_aleatorias)

            embed = discord.Embed(
                title=f"🚨 Alerta de Novidade! | Membro #{member_number} 🚨",
                color=discord.Color.from_rgb(255, 215, 0)
            )

            descricao_inicial = (
                f"Um novo membro foi detectado, {member.mention} foi detetado por meu trevo da sorte "
                f"em **{data_extenso}** E **{hora}**."
            )

            boas_vindas_acolhedoras = (
                "\n\nBrincadeiras à parte, é um prazer imenso receber você! "
                "Esperamos que se sinta em casa e encontre muita diversão e boas conversas por aqui."
            )

            frase_motivacional = f"\n\n*\"{frase_final}\"*"

            embed.description = descricao_inicial + boas_vindas_acolhedoras + frase_motivacional

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"ID do Usuário: {member.id} | Seu número é: {member_number}")

            await canal_boas_vindas.send(embed=embed)
        else:
            print(f"ERRO: Canal de boas-vindas com ID {TARGET_CHANNEL_ID} não encontrado.")

        await self.update_member_list_message(member.guild)

    @commands.command(name='testar_boas_vindas')
    async def testar_boas_vindas(self, ctx):
        member_number = "TESTE"
        data_extenso, hora, _ = get_datetime_pt_br()
        frase_final = random.choice(self.frases_aleatorias)
        member = ctx.author

        embed = discord.Embed(
            title=f"🚨 Alerta de Novidade! (MODO TESTE) | Membro #{member_number} 🚨",
            color=discord.Color.from_rgb(255, 215, 0)
        )

        descricao_inicial = (
            f"Um novo membro foi detectado, {member.mention} foi detetado por meu trevo da sorte "
            f"em **{data_extenso}** E **{hora}**."
        )

        boas_vindas_acolhedoras = (
            "\n\nBrincadeiras à parte, é um prazer imenso receber você! "
            "Esperamos que se sinta em casa e encontre muita diversão e boas conversas por aqui."
        )

        frase_motivacional = f"\n\n*\"{frase_final}\"*"

        embed.description = descricao_inicial + boas_vindas_acolhedoras + frase_motivacional

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID do Usuário: {member.id}")

        await ctx.send(embed=embed)
        await ctx.send("✅ Teste de boas-vindas concluído no canal atual.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        conteudo = message.content.lower()
        for gatilho, resposta in self.gatilhos.items():
            if gatilho in conteudo:
                await message.channel.send(resposta)
                return  # Responde apenas uma vez

async def setup(bot):
    await bot.add_cog(AutoResponse(bot))

# ============================================================
# Atualizado em: 2025-11-23 22:41:53 (Horário de Brasília)
# ============================================================
