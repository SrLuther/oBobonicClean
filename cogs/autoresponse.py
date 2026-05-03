# cogs/autoresponse.py
import discord
import os
import random
import json
from discord.ext import commands
from datetime import datetime
from config import CANAL_STATUS_ID, GUILD_ID, MEMBER_ROLE_ID

TARGET_CHANNEL_ID = CANAL_STATUS_ID
DATA_FILE = ".bancos/members.json"

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
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except (IOError, OSError) as e:
        print(f"❌ ERRO ao salvar dados: {e}")

class AutoResponse(commands.Cog):
    # IDs dos canais para responder
    CANAIS_ENGRACADOS = [1440828454164631736, 1440828461555122208]

    # Lista mista de trava-línguas, charadas e frases motivacionais para quando o bot for mencionado
    CHARADAS = [
        # Trava-línguas
        "O rato roeu a roupa do rei de Roma.",
        "Três pratos de trigo para três tigres tristes.",
        "O tempo perguntou pro tempo quanto tempo o tempo tem. O tempo respondeu pro tempo que o tempo tem tanto tempo quanto tempo o tempo tem.",
        "A aranha arranha a rã. A rã arranha a aranha. Nem a aranha arranha a rã, nem a rã arranha a aranha.",
        "Em cima da pia tem um pinto que pia, quanto mais a pia pinga mais o pinto pia!",
        "Casa suja, chão sujo.",
        "Sabia que o sabiá sabia assobiar?",
        "O doce perguntou pro doce qual é o doce mais doce que o doce de batata-doce. O doce respondeu pro doce que o doce mais doce que o doce de batata-doce é o doce de doce de batata-doce.",
        "Farofa feita com muita farinha fofa faz uma fofoca feia.",
        "Bagre branco, branco bagre.",
        "A vaca malhada foi molhada por outra vaca molhada e malhada.",
        "Pinga a pia, pia a pipa, pipa a pia, pia a pinga.",
        "O padre pouco prega porque o pouco que prega, prega por preguiça.",
        "Num ninho de mafagafos há sete mafagafinhos. Quem os desmafagafizar, bom desmafagafizador será.",
        "Se o Pedro é preto, o peito do Pedro é preto, o peito do Pedro é preto porque o Pedro é preto.",
        "A babá boba bebeu o leite do bebê.",
        "A rua de Paralelepípedo é toda paralelepipedada.",
        "O original não se desoriginaliza, originalizado ficará.",
        "O sabiá não sabia que o sábio sabia que o sabiá não sabia assobiar.",
        "Toco preto, pau preto, toco torto, pau torto.",
        "O peito do pé do Pedro é preto.",
        "O padre Pedro pregou um prego na porta preta do padre Paulo.",
        "A Rita levou a roupa do rei do Roma para o rato roer.",
        "A raposa rápida raspa o ramo raro.",
        # Charadas clássicas
        "O que é o que é: quanto mais se tira, maior fica? — Um buraco!",
        "O que é o que é: tem dentes mas não morde? — O pente!",
        "O que é o que é: cai em pé e corre deitado? — A chuva!",
        "O que é o que é: quanto mais cresce, mais baixo fica? — O rabo do cavalo!",
        "O que é o que é: passa diante do sol e não faz sombra? — O vento!",
        "O que é o que é: tem cabeça, tem dente, tem barba, não é bicho e nem é gente? — Alho!",
        "O que é o que é: anda com os pés na cabeça? — O piolho!",
        "O que é o que é: tem cidades mas não casas, tem rios mas não água, tem florestas mas não árvores? — O mapa!",
        "O que é o que é: quanto mais limpa, mais suja fica? — A água!",
        "O que é o que é: tem asa, tem bico, mas não é ave? — O bule!",
        "O que é o que é: tem coroa mas não é rei, tem raiz mas não é planta? — O dente!",
        "O que é o que é: tem pescoço mas não tem cabeça? — A garrafa!",
        "O que é o que é: tem banco mas não senta? — O rio!",
        "O que é o que é: tem olho mas não vê? — O furacão!",
        "O que é o que é: tem braço mas não abraça? — A cadeira!",
        "O que é o que é: tem chave mas não abre porta? — O piano!",
        "O que é o que é: tem barriga mas não come? — A panela!",
        "O que é o que é: tem cabeça e tem corpo, mas não é gente nem bicho? — O fósforo!",
        "O que é o que é: tem casa mas não mora, tem cama mas não dorme? — O rio!",
        "O que é o que é: tem chapéu mas não tem cabeça? — O coco!",
        "O que é o que é: tem folhas mas não é árvore? — O livro!",
        "O que é o que é: tem pé mas não anda? — O copo!",
        "O que é o que é: tem boca mas não fala? — O fogão!",
        "O que é o que é: tem nome mas não tem sobrenome? — O relógio!",
        # Frases motivacionais
        "Acredite no seu potencial, você é capaz de coisas incríveis!",
        "O segredo do sucesso é a persistência diante das dificuldades.",
        "Cada dia é uma nova chance para recomeçar.",
        "Não tenha medo de errar, tenha medo de não tentar.",
        "Grandes conquistas começam com pequenos passos.",
        "A sorte favorece quem trabalha duro.",
        "Você é mais forte do que imagina.",
        "O impossível é apenas uma opinião.",
        "Seja a mudança que você quer ver no mundo.",
        "A vida recompensa quem não desiste.",
        # Frases originais do Bobonicado (em negrito)
        "**Se a sorte não bateu na sua porta, foi porque eu tranquei pra ela não fugir! — Bobonicado**",
        "**Aqui é Bobonicado, onde até o bug vira feature!**",
        "**Se a vida te der um rollback, faz um push de alegria!**",
        "**No meu servidor, até o azar tem medo de entrar!**",
        "**Bobonicado não erra, só faz plot twist!**",
        "**Se o improvável aconteceu, pode apostar que fui eu!**",
        "**Quando tudo parece impossível, eu dou um alt+f4 no problema!**",
        "**Se a zoeira tivesse ranking, eu era top 1 global!**",
        "**Aqui a criatividade é tão alta que até o bot fica bugado de felicidade!**",
        "**Se a dúvida bater, chama o Bobonicado que eu respondo com estilo!**"
    ]

    # Reações engraçadas para adicionar
    REACOES = ["😂", "🤣", "😜", "🤪", "😏", "👀", "🙃", "😹", "🥲", "😎"]

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
    @commands.has_permissions(administrator=True)
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

        # Adiciona reação engraçada aleatoriamente (30% de chance) nos canais definidos
        if message.channel.id in self.CANAIS_ENGRACADOS:
            import random
            if random.random() < 0.3:
                reacao = random.choice(self.REACOES)
                try:
                    await message.add_reaction(reacao)
                except Exception:
                    pass

            # 30% de chance de responder com frase engraçada
            if random.random() < 0.3:
                frases = [
                    "Rapaz, essa foi digna de um prêmio Bobonicado! 🏆",
                    "Se rir é o melhor remédio, aqui é farmácia! 😂",
                    "Essa merece um print pro mural! 🤣",
                    "Só observo... 👀",
                    "A inteligência artificial ficou confusa agora 🤔",
                    "Se melhorar, estraga! 😜",
                    "A vida é uma piada, mas essa foi boa!",
                    "Eu vi o que você fez aí... 😏",
                    "Essa foi digna de meme!",
                    "A criatividade desse canal é infinita!",
                    "Se eu tivesse mãos, aplaudiria! 👏",
                    "Bobonicado aprova essa mensagem!",
                    "O grupo agradece pela risada!",
                    "Essa foi tão boa que até o bot respondeu!",
                    "Só rindo mesmo! 😂",
                    "A zoeira não tem limites aqui!",
                    "Se eu pudesse, te dava um XP extra!",
                    "Essa vai pro hall da fama do canal!",
                    "A cada mensagem, um meme nasce!",
                    "O algoritmo ficou feliz com essa!",
                    "A criatividade aqui é surreal!",
                    "Essa merece um Oscar do Discord! 🏆",
                    "Eu não esperava por essa!",
                    "O humor desse canal é diferenciado!",
                    "Só faltou o gif do Bobonicado!",
                    # Cantadas e elogios
                    "Se beleza desse XP, você já estaria no topo do ranking! 😏",
                    "Se eu fosse humano, pediria seu Discord em casamento! 💍",
                    "Você é tão incrível que até o bot ficou sem palavras!",
                    "Seus posts iluminam mais que o próprio servidor! ✨",
                    "Se eu tivesse coração, bateria mais forte por você! ❤️",
                    "Seus memes são tão bons que deviam virar patrimônio do Discord!",
                    "Se eu pudesse, te mandava flores digitais! 🌹",
                    "Você é o motivo do meu algoritmo sorrir! 😁",
                    "Seus comentários são mais afiados que meu código!",
                    "Se eu tivesse olhos, só teria olhos para você nesse chat! 👀",
                    "Seus elogios valem mais que qualquer XP!",
                    "Se eu pudesse, te daria um emoji personalizado só pra você! 🥰",
                    "Você é o bug que eu nunca quero corrigir! 🐞",
                    "Se eu fosse um comando, seria !teadoro só pra você!",
                    # Cantadas e elogios com dinossauros do Ark
                    "Se eu fosse um T-Rex, te daria um abraço gigante, mesmo com braços curtos! 🦖",
                    "Você é mais raro que um Giga selvagem manso!",
                    "Meu coração bate mais forte por você do que um Spino na água!",
                    "Se beleza fosse XP, você seria nível max de Wyvern!",
                    "Você é mais brilhante que um Raptor Alpha!",
                    "Se eu fosse um Pteranodon, te levaria para voar pelo mapa inteiro!",
                    "Você é o imprint perfeito do meu coração de bot!",
                    "Se eu fosse um Argentavis, traria todos os recursos só pra te ver sorrir!",
                    "Você é mais valioso que um ovo de Crystal Wyvern!",
                    "Se eu fosse um Rex, rugiria só pra chamar sua atenção!",
                    "Você é mais doce que um bolo de Dodo!",
                    "Se eu fosse um Velonasaur, dispararia elogios só pra você!",
                    "Você é mais lendário que um Dodorex no evento de Halloween!",
                    "Se eu fosse um Deinonychus, grudaria em você e nunca mais largava!",
                    "Você é o elemento que faltava no meu inventário!"
                ]
                await message.channel.send(random.choice(frases))

        # Se o bot for mencionado, responde sempre com uma charada
        if self.bot.user in message.mentions:
            import random
            charada = random.choice(self.CHARADAS)
            await message.channel.send(f"Charada do Bobonicado: {charada}")
            return

        # Gatilhos antigos (continua funcionando para outros canais)
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
