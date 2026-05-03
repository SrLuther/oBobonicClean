"""
Sistema de Lojas Pessoais para ARK Survival Evolved
Permite que jogadores criem suas próprias lojas usando tópicos de fórum
"""

import discord
from discord.ext import commands
from discord import app_commands
import io
import json
import os
from datetime import datetime
from typing import Optional, Any

# ============================================
# CONFIGURAÇÃO
# ============================================
PANEL_CHANNEL_ID = 1473763773805363414  # Canal onde o painel será enviado
LOJAS_CATEGORY_ID = 1473763671485186239  # Categoria para criar os canais de lojas
LOJAS_VIEWER_ROLE_ID = 1440828415103074356  # Cargo que pode visualizar todas as lojas
COMMAND_CHANNEL_ID = 1440828497772679168  # Sala de comandos
TIPS_CHANNEL_ID = 1473771157160460359  # Canal para dicas de formatação
LOJAS_FILE = "data/lojas.json"          # Arquivo para armazenar dados das lojas
TIPS_SENT_FILE = "data/tips_sent.json"  # Arquivo de controle para dicas
PRODUTOS_FILE = ".bancos/produtos.json"  # Arquivo para armazenar produtos das lojas
LOGS_DIR = ".bancos/logs"               # Diretório de logs por loja

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def carregar_lojas() -> dict:
    """Carrega dados das lojas do arquivo JSON"""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    if not os.path.exists(LOJAS_FILE):
        with open(LOJAS_FILE, "w") as f:
            json.dump({}, f, indent=2)
        return {}
    
    try:
        with open(LOJAS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def salvar_lojas(lojas: dict) -> None:
    """Salva dados das lojas no arquivo JSON"""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    with open(LOJAS_FILE, "w") as f:
        json.dump(lojas, f, indent=2, ensure_ascii=False)

def obter_loja_jogador(user_id: int) -> Optional[dict]:
    """Obtém a loja ativa de um jogador"""
    lojas = carregar_lojas()
    user_id_str = str(user_id)
    
    if user_id_str in lojas and lojas[user_id_str].get("ativa", False):
        return lojas[user_id_str]
    
    return None

def dicas_ja_foram_enviadas() -> bool:
    """Verifica se as dicas de formatação já foram enviadas"""
    if not os.path.exists(TIPS_SENT_FILE):
        return False
    
    try:
        with open(TIPS_SENT_FILE, "r") as f:
            data = json.load(f)
            return data.get("enviado", False)
    except:
        return False

def marcar_dicas_como_enviadas() -> None:
    """Marca as dicas como já envidas"""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    with open(TIPS_SENT_FILE, "w") as f:
        json.dump({"enviado": True, "timestamp": datetime.now().isoformat()}, f, indent=2)


def carregar_produtos() -> dict:
    """Carrega produtos do arquivo JSON"""
    if not os.path.exists(".bancos"):
        os.makedirs(".bancos")
    if not os.path.exists(PRODUTOS_FILE):
        with open(PRODUTOS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        return {}
    try:
        with open(PRODUTOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def salvar_produtos(produtos: dict) -> None:
    """Salva produtos no arquivo JSON"""
    if not os.path.exists(".bancos"):
        os.makedirs(".bancos")
    with open(PRODUTOS_FILE, "w", encoding="utf-8") as f:
        json.dump(produtos, f, indent=2, ensure_ascii=False)


def registrar_log(channel_id: int, tipo: str, usuario: str, usuario_id: int, detalhes: str) -> None:
    """Registra um evento no arquivo de log da loja"""
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = f"{LOGS_DIR}/loja_{channel_id}.json"
    try:
        logs: list = []
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
        logs.append({
            "timestamp": datetime.now().isoformat(),
            "tipo": tipo,
            "usuario": usuario,
            "usuario_id": usuario_id,
            "detalhes": detalhes
        })
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ [LOJAS] Erro ao registrar log: {e}")


def obter_loja_por_canal(channel_id: int) -> Optional[dict]:
    """Obtém a loja ativa associada a um canal"""
    lojas = carregar_lojas()
    for _uid, loja in lojas.items():
        if loja.get("channel_id") == channel_id and loja.get("ativa", False):
            return loja
    return None


def obter_produto(product_id: str) -> Optional[dict]:
    """Obtém um produto pelo seu ID"""
    return carregar_produtos().get(product_id)


def gerar_embed_produto(produto: dict) -> discord.Embed:
    """Gera o embed de exibição de um produto"""
    disponivel = produto.get("disponibilidade", "Não informado")
    baixo = disponivel.lower()
    if "indispon" in baixo or "sem estoque" in baixo or "esgotado" in baixo:
        color = discord.Color.red()
        status_emoji = "🔴"
    elif "limitad" in baixo or "pouco" in baixo or "último" in baixo:
        color = discord.Color.orange()
        status_emoji = "🟡"
    else:
        color = discord.Color.green()
        status_emoji = "🟢"
    embed = discord.Embed(title=f"🛍️ {produto['nome']}", color=color)
    embed.add_field(name="📋 Descrição", value=produto.get("descricao", "—"), inline=False)
    embed.add_field(name="💰 Valor", value=produto.get("valor", "—"), inline=True)
    embed.add_field(name=f"{status_emoji} Disponibilidade", value=disponivel, inline=True)
    embed.set_footer(text=f"ID: {produto['product_id']}")
    try:
        embed.timestamp = datetime.fromisoformat(produto["criado_em"])
    except Exception:
        pass
    return embed


# ============================================
# VIEWS (BOTÕES E MODAIS)
# ============================================

class ModalCriarLoja(discord.ui.Modal):
    """Modal para o jogador informar dados da loja"""
    
    title = "Criar Loja Pessoal"
    
    nome_loja = discord.ui.TextInput(
        label="Nome da Loja",
        placeholder="Ex: Loja de Recursos, Dinossauros Premium...",
        required=True,
        max_length=100
    )
    
    nome_tribo = discord.ui.TextInput(
        label="Nome da Tribo",
        placeholder="Ex: Phoenix Rising, Dark Kingdom...",
        required=True,
        max_length=100
    )
    
    mapa_base = discord.ui.TextInput(
        label="Mapa da Base Principal",
        placeholder="Ex: The Island, Ragnarok, Crystal Isles...",
        required=True,
        max_length=100
    )
    
    mapas_entrega = discord.ui.TextInput(
        label="Mapas Onde Você Entrega",
        placeholder="Ex: The Island, Ragnarok (separe por vírgula)",
        required=True,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Processa o envio do modal"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Obter referências do bot e guild
            bot = interaction.client
            guild = interaction.guild
            
            if not guild:
                await interaction.followup.send(
                    "❌ Erro: Não foi possível identificar o servidor.",
                    ephemeral=True
                )
                return
            
            # Obter a categoria
            categoria = guild.get_channel(LOJAS_CATEGORY_ID)
            if not isinstance(categoria, discord.CategoryChannel):
                print(f"❌ [LOJAS] Categoria inválida: {LOJAS_CATEGORY_ID}")
                await interaction.followup.send(
                    "❌ Erro: Categoria de lojas não configurada.",
                    ephemeral=True
                )
                return
            
            # Verificar se jogador já tem loja ativa
            loja_existente = obter_loja_jogador(interaction.user.id)
            if loja_existente:
                await interaction.followup.send(
                    f"❌ Você já possui uma loja ativa: **{loja_existente['nome']}**\n\n"
                    f"Use `/fechar_loja` para fechar a loja atual e criar uma nova.",
                    ephemeral=True
                )
                return
            
            # Criar o canal para a loja
            nome_canal = f"🦖-loja-{interaction.user.name}".replace(' ', '-').lower()[:32]
            
            # Obter o cargo visualizador
            cargo_viewer = guild.get_role(LOJAS_VIEWER_ROLE_ID)
            
            # Configurar permissões: dono (total), cargo viewer (leitura), others (nada)
            permissoes = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_messages=True,
                    manage_webhooks=False
                )
            }
            
            # Adicionar permissões para o cargo viewer se existir
            if cargo_viewer:
                permissoes[cargo_viewer] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False,
                    read_message_history=True
                )
            
            # Criar o canal
            canal_loja = await guild.create_text_channel(
                nome_canal,
                category=categoria,
                overwrites=permissoes,
                topic=f"Loja de {self.nome_loja.value}",
                reason=f"Loja criada para {interaction.user.name}"
            )
            
            # Enviar mensagem de boas-vindas com informações da loja
            mensagem_inicial = (
                f"🏪 **Bem-vindo à sua loja!**\n\n"
                f"**Proprietário:** {interaction.user.mention}\n"
                f"**Nome da Loja:** {self.nome_loja.value}\n"
                f"**Tribo:** {self.nome_tribo.value}\n"
                f"**Mapa da Base:** {self.mapa_base.value}\n"
                f"**Mapas de Entrega:** {self.mapas_entrega.value}\n"
                f"**Criada em:** <t:{int(datetime.now().timestamp())}:f>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Você pode publicar seus produtos e serviços aqui!\n"
                f"Use `!fecharloja` para encerrar sua loja quando desejar.\n\n"
                f"✨ **Dica:** Confira o canal de dicas de formatação para deixar sua loja mais atrativa!"
            )
            
            await canal_loja.send(mensagem_inicial)

            # Painel de gerenciamento da loja (botão Adicionar Produto)
            embed_gerenciar = discord.Embed(
                title="⚙️ Gerenciamento da Loja",
                description=(
                    "Use o botão abaixo para publicar produtos nesta loja.\n\n"
                    "Cada produto terá um painel próprio com os botões "
                    "**Encomendar**, **Editar**, **Barganha** e **Excluir**."
                ),
                color=discord.Color.blurple()
            )
            embed_gerenciar.add_field(
                name="📋 Regras de Acesso",
                value=(
                    "• ➕ **Adicionar / ✏️ Editar / 🗑️ Excluir** — somente você\n"
                    "• 📦 **Encomendar / 🤝 Barganha** — toda a comunidade"
                ),
                inline=False
            )
            await canal_loja.send(embed=embed_gerenciar, view=ViewGerenciarLoja())

            # Armazenar dados da loja
            lojas = carregar_lojas()
            user_id_str = str(interaction.user.id)
            
            lojas[user_id_str] = {
                "nome": self.nome_loja.value,
                "tribo": self.nome_tribo.value,
                "mapa_base": self.mapa_base.value,
                "mapas_entrega": self.mapas_entrega.value,
                "channel_id": canal_loja.id,
                "owner_id": interaction.user.id,
                "owner_name": interaction.user.name,
                "criada_em": datetime.now().isoformat(),
                "ativa": True,
                "category_id": LOJAS_CATEGORY_ID
            }
            
            salvar_lojas(lojas)
            
            # Enviar dicas de formatação no canal específico (apenas uma vez)
            try:
                if not dicas_ja_foram_enviadas():
                    canal_tips = interaction.guild.get_channel(TIPS_CHANNEL_ID)
                    if canal_tips and isinstance(canal_tips, discord.TextChannel):
                        embed_tips = discord.Embed(
                            title=f"📝 Dicas de Formatação - CianoStore",
                            description=f"Guia de formatação para deixar suas lojas mais atrativas!",
                            color=discord.Color.gold()
                        )
                        embed_tips.add_field(
                            name="Estilos de Texto",
                            value="• **Negrito** - `**texto**`\n"
                                  "• *Itálico* - `*texto*` ou `_texto_`\n"
                                  "• ***Negrito + Itálico*** - `***texto***`\n"
                                  "• ~~Tachado~~ - `~~texto~~`\n"
                                  "• __Sublinhado__ - `__texto__`\n"
                                  "• `Código inline` - `` `código` ``",
                            inline=False
                        )
                        embed_tips.add_field(
                            name="Blocos de Código",
                            value="```\nCod aqui\n```\n"
                                  "(Útil para mostrar estatísticas formatadas)",
                            inline=False
                        )
                        embed_tips.add_field(
                            name="Listas",
                            value="• Bullet com `•` ou `-`\n"
                                  "1. Numerada com número seguido de `.`",
                            inline=False
                        )
                        embed_tips.add_field(
                            name="Citar Texto",
                            value="> Use `>` para criar uma citação\n"
                                  ">> Use `>>` para citação aninhada",
                            inline=False
                        )
                        embed_tips.add_field(
                            name="Spoilers & Links",
                            value="• ||Texto escondido|| - `||texto||`\n"
                                  "• [Texto](url) - `[Texto](https://link.com)`",
                            inline=False
                        )
                        embed_tips.add_field(
                            name="Emojis Úteis",
                            value="🎯 💎 ✨ 🔥 ⭐ 🏆 📦 🛍️ 💰 📊",
                            inline=False
                        )
                        embed_tips.add_field(
                            name="Exemplo de Produto",
                            value="```\n🎯 RECURSO X - 100 unidades\n"
                                  "├ Descrição detalhada aqui\n"
                                  "├ 📊 Em estoque: 50\n"
                                  "└ 📞 Contato: MP\n```",
                            inline=False
                        )
                        embed_tips.set_footer(text="Use criatividade! 🎨")
                        await canal_tips.send(embed=embed_tips)
                        marcar_dicas_como_enviadas()
                        print(f"✅ [LOJAS] Dicas de formatação enviadas no canal {TIPS_CHANNEL_ID}")
            except Exception as e:
                print(f"⚠️ [LOJAS] Erro ao enviar dicas: {e}")
            
            # Confirmar ao usuário
            await interaction.followup.send(
                f"✅ **Loja criada com sucesso!**\n\n"
                f"**Nome:** {self.nome_loja.value}\n"
                f"**Acesso:** {canal_loja.mention}\n\n"
                f"Sua loja está pronta para receber produtos!",
                ephemeral=True
            )
            
            print(f"✅ [LOJAS] Loja criada para {interaction.user.name} ({interaction.user.id}) - Canal: {canal_loja.id}")
            
        except Exception as e:
            print(f"❌ [LOJAS] Erro ao criar loja: {e}")
            await interaction.followup.send(
                f"❌ Erro ao criar a loja: {str(e)}",
                ephemeral=True
            )


class ViewCriarLoja(discord.ui.View):
    """View com botão para criar loja"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(
        label="Criar Minha Loja",
        style=discord.ButtonStyle.green,
        emoji="🏪",
        custom_id="criar_loja_btn"
    )
    async def criar_loja(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Abre o modal para criar loja"""
        try:
            await interaction.response.send_modal(ModalCriarLoja())
        except Exception as e:
            print(f"❌ [LOJAS] Erro ao abrir modal: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao abrir o formulário. Tente novamente.",
                    ephemeral=True
                )
            except:
                pass


# ============================================
# SISTEMA DE PRODUTOS — Modais
# ============================================

class ModalEncomenda(discord.ui.Modal, title="📦 Encomendar Produto"):
    """Modal de encomenda — aberto pela comunidade"""

    quantidade = discord.ui.TextInput(
        label="Quantidade",
        placeholder="Ex: 1 unidade, 5 stacks...",
        required=True,
        max_length=100
    )
    mensagem = discord.ui.TextInput(
        label="Mensagem ao Vendedor",
        placeholder="Informações adicionais, forma de contato...",
        required=False,
        max_length=400,
        style=discord.TextStyle.paragraph
    )

    def __init__(self, produto: dict) -> None:
        super().__init__()
        self._product_id = produto["product_id"]
        self._owner_id = produto["owner_id"]
        self._product_name = produto["nome"]
        self._channel_id = produto.get("channel_id", 0)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="📦 Nova Encomenda!",
            description=f"**{interaction.user.mention}** quer comprar **{self._product_name}**",
            color=discord.Color.green()
        )
        embed.add_field(name="🔢 Quantidade", value=self.quantidade.value, inline=True)
        if self.mensagem.value:
            embed.add_field(name="💬 Mensagem", value=self.mensagem.value, inline=False)
        if isinstance(interaction.channel, discord.TextChannel):
            embed.add_field(name="📍 Canal", value=interaction.channel.mention, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.timestamp = datetime.now()

        notificado = False
        try:
            owner = await interaction.client.fetch_user(self._owner_id)
            await owner.send(embed=embed)
            notificado = True
        except Exception:
            pass

        try:
            if isinstance(interaction.channel, discord.TextChannel):
                await interaction.channel.send(
                    f"📦 <@{self._owner_id}>, você recebeu uma encomenda de {interaction.user.mention}!",
                    embed=embed
                )
        except Exception as e:
            print(f"⚠️ [LOJAS] Erro ao notificar encomenda no canal: {e}")

        aviso = "✅ Encomenda enviada ao vendedor! Aguarde o contato."
        if not notificado:
            aviso += "\n⚠️ Não foi possível notificar via DM, mas a encomenda foi enviada no canal."
        registrar_log(
            self._channel_id, "ENCOMENDA_RECEBIDA",
            str(interaction.user), interaction.user.id,
            f"Produto: {self._product_name} | Qtd: {self.quantidade.value}"
            + (f" | Msg: {self.mensagem.value}" if self.mensagem.value else "")
        )
        await interaction.followup.send(aviso, ephemeral=True)


class ModalEditarProduto(discord.ui.Modal, title="✏️ Editar Produto"):
    """Modal de edição com campos pré-preenchidos — exclusivo do dono"""

    def __init__(self, produto: dict) -> None:
        super().__init__()
        self._product_id = produto["product_id"]

        self.nome = discord.ui.TextInput(
            label="Nome do Produto",
            default=produto["nome"],
            required=True,
            max_length=100
        )
        self.descricao = discord.ui.TextInput(
            label="Descrição",
            default=produto["descricao"],
            required=True,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.valor = discord.ui.TextInput(
            label="Valor",
            default=produto["valor"],
            required=True,
            max_length=200
        )
        self.disponibilidade = discord.ui.TextInput(
            label="Disponibilidade",
            default=produto["disponibilidade"],
            required=True,
            max_length=100
        )
        self.add_item(self.nome)
        self.add_item(self.descricao)
        self.add_item(self.valor)
        self.add_item(self.disponibilidade)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        produtos = carregar_produtos()
        if self._product_id not in produtos:
            await interaction.response.send_message("❌ Produto não encontrado.", ephemeral=True)
            return

        produto = produtos[self._product_id]
        produto["nome"] = self.nome.value
        produto["descricao"] = self.descricao.value
        produto["valor"] = self.valor.value
        produto["disponibilidade"] = self.disponibilidade.value
        salvar_produtos(produtos)

        try:
            if interaction.guild and produto.get("message_id"):
                canal = interaction.guild.get_channel(produto["channel_id"])
                if canal and isinstance(canal, discord.TextChannel):
                    msg = await canal.fetch_message(produto["message_id"])
                    await msg.edit(embed=gerar_embed_produto(produto))
        except Exception as e:
            print(f"⚠️ [LOJAS] Erro ao atualizar embed do produto: {e}")

        await interaction.response.send_message(
            f"✅ Produto **{self.nome.value}** atualizado com sucesso!",
            ephemeral=True
        )
        registrar_log(
            produto.get("channel_id", 0), "PRODUTO_EDITADO",
            str(interaction.user), interaction.user.id,
            f"Produto: {self.nome.value} | Valor: {self.valor.value} | Disponibilidade: {self.disponibilidade.value}"
        )


class ModalBarganha(discord.ui.Modal, title="🤝 Proposta de Barganha"):
    """Modal para troca por pontos + recursos — aberto pela comunidade"""

    def __init__(self, produto: dict) -> None:
        super().__init__()
        self._product_id = produto["product_id"]
        self._owner_id = produto["owner_id"]
        self._product_name = produto["nome"]
        self._channel_id = produto.get("channel_id", 0)

        self.pontos = discord.ui.TextInput(
            label="Pontos Oferecidos",
            placeholder="Ex: 300 pontos",
            required=True,
            max_length=100
        )
        self.recursos = discord.ui.TextInput(
            label="Recursos para Troca",
            placeholder="Ex: 500 metal, 200 cemento, 100 cristal...",
            required=True,
            max_length=300,
            style=discord.TextStyle.paragraph
        )
        self.mensagem = discord.ui.TextInput(
            label="Mensagem ao Vendedor (opcional)",
            placeholder="Explique sua proposta...",
            required=False,
            max_length=300,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.pontos)
        self.add_item(self.recursos)
        self.add_item(self.mensagem)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="🤝 Nova Proposta de Barganha!",
            description=f"**{interaction.user.mention}** propõe barganha por **{self._product_name}**",
            color=discord.Color.orange()
        )
        embed.add_field(name="💰 Pontos Oferecidos", value=self.pontos.value, inline=True)
        embed.add_field(name="📦 Recursos para Troca", value=self.recursos.value, inline=False)
        if self.mensagem.value:
            embed.add_field(name="💬 Mensagem", value=self.mensagem.value, inline=False)
        if isinstance(interaction.channel, discord.TextChannel):
            embed.add_field(name="📍 Canal", value=interaction.channel.mention, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.timestamp = datetime.now()

        notificado = False
        try:
            owner = await interaction.client.fetch_user(self._owner_id)
            await owner.send(embed=embed)
            notificado = True
        except Exception:
            pass

        try:
            if isinstance(interaction.channel, discord.TextChannel):
                await interaction.channel.send(
                    f"🤝 <@{self._owner_id}>, você recebeu uma proposta de barganha de {interaction.user.mention}!",
                    embed=embed
                )
        except Exception as e:
            print(f"⚠️ [LOJAS] Erro ao notificar barganha no canal: {e}")

        aviso = "✅ Proposta de barganha enviada ao vendedor!"
        if not notificado:
            aviso += "\n⚠️ Não foi possível notificar via DM, mas a proposta foi enviada no canal."
        registrar_log(
            self._channel_id, "BARGANHA_RECEBIDA",
            str(interaction.user), interaction.user.id,
            f"Produto: {self._product_name} | Pontos: {self.pontos.value} | Recursos: {self.recursos.value}"
            + (f" | Msg: {self.mensagem.value}" if self.mensagem.value else "")
        )
        await interaction.followup.send(aviso, ephemeral=True)


class ModalAdicionarProduto(discord.ui.Modal, title="➕ Adicionar Produto"):
    """Modal para o dono da loja publicar um novo produto"""

    nome = discord.ui.TextInput(
        label="Nome do Produto",
        placeholder="Ex: Rex 50k melee, Cemento (200 uni)...",
        required=True,
        max_length=100
    )
    descricao = discord.ui.TextInput(
        label="Descrição",
        placeholder="Descreva o produto com detalhes...",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    valor = discord.ui.TextInput(
        label="Valor",
        placeholder="Ex: 500 pontos, 1000 metal + 200 pontos...",
        required=True,
        max_length=200
    )
    disponibilidade = discord.ui.TextInput(
        label="Disponibilidade",
        placeholder="Ex: Em estoque, Limitado (5 uni), Sob encomenda...",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel_id = interaction.channel_id or 0
        loja = obter_loja_por_canal(channel_id)
        if not loja:
            await interaction.response.send_message(
                "❌ Este canal não pertence a uma loja ativa.", ephemeral=True
            )
            return

        if interaction.user.id != loja["owner_id"]:
            await interaction.response.send_message(
                "❌ Apenas o proprietário da loja pode adicionar produtos.", ephemeral=True
            )
            return

        product_id = f"prod_{interaction.user.id}_{int(datetime.now().timestamp() * 1000)}"
        produto = {
            "product_id": product_id,
            "owner_id": interaction.user.id,
            "channel_id": channel_id,
            "message_id": None,
            "nome": self.nome.value,
            "descricao": self.descricao.value,
            "valor": self.valor.value,
            "disponibilidade": self.disponibilidade.value,
            "criado_em": datetime.now().isoformat()
        }

        embed = gerar_embed_produto(produto)
        view = ViewProduto(product_id)
        interaction.client.add_view(view)

        await interaction.response.defer(ephemeral=True)

        canal = interaction.channel or interaction.client.get_channel(channel_id or 0)
        if not canal or not isinstance(canal, discord.TextChannel):
            await interaction.followup.send("❌ Não foi possível publicar o produto.", ephemeral=True)
            return

        msg = await canal.send(embed=embed, view=view)
        produto["message_id"] = msg.id

        produtos = carregar_produtos()
        produtos[product_id] = produto
        salvar_produtos(produtos)

        registrar_log(
            channel_id, "PRODUTO_ADICIONADO",
            str(interaction.user), interaction.user.id,
            f"Produto: {self.nome.value} | Valor: {self.valor.value} | Disponibilidade: {self.disponibilidade.value}"
        )

        await interaction.followup.send(
            f"✅ Produto **{self.nome.value}** publicado com sucesso!", ephemeral=True
        )
        print(f"✅ [LOJAS] Produto {product_id} adicionado por {interaction.user.name}")


# ── Botões do painel de produto ──────────────────────────────────────────────

class BotaoEncomendar(discord.ui.Button):
    def __init__(self, product_id: str) -> None:
        super().__init__(
            label="Encomendar",
            style=discord.ButtonStyle.green,
            emoji="📦",
            custom_id=f"prod_enc_{product_id}"
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        produto = obter_produto(self.view.product_id)
        if not produto:
            await interaction.response.send_message("❌ Produto não encontrado.", ephemeral=True)
            return
        if interaction.user.id == produto["owner_id"]:
            await interaction.response.send_message(
                "❌ Você não pode encomendar seus próprios produtos.", ephemeral=True
            )
            return
        await interaction.response.send_modal(ModalEncomenda(produto))


class BotaoEditar(discord.ui.Button):
    def __init__(self, product_id: str) -> None:
        super().__init__(
            label="Editar",
            style=discord.ButtonStyle.blurple,
            emoji="✏️",
            custom_id=f"prod_edi_{product_id}"
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        produto = obter_produto(self.view.product_id)
        if not produto:
            await interaction.response.send_message("❌ Produto não encontrado.", ephemeral=True)
            return
        if interaction.user.id != produto["owner_id"]:
            await interaction.response.send_message(
                "❌ Apenas o dono da loja pode editar produtos.", ephemeral=True
            )
            return
        await interaction.response.send_modal(ModalEditarProduto(produto))


class BotaoBarganha(discord.ui.Button):
    def __init__(self, product_id: str) -> None:
        super().__init__(
            label="Barganha",
            style=discord.ButtonStyle.secondary,
            emoji="🤝",
            custom_id=f"prod_bar_{product_id}"
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        produto = obter_produto(self.view.product_id)
        if not produto:
            await interaction.response.send_message("❌ Produto não encontrado.", ephemeral=True)
            return
        if interaction.user.id == produto["owner_id"]:
            await interaction.response.send_message(
                "❌ Você não pode barganhar em seus próprios produtos.", ephemeral=True
            )
            return
        await interaction.response.send_modal(ModalBarganha(produto))


class BotaoExcluir(discord.ui.Button):
    def __init__(self, product_id: str) -> None:
        super().__init__(
            label="Excluir",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            custom_id=f"prod_del_{product_id}"
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        produto = obter_produto(self.view.product_id)
        if not produto:
            await interaction.response.send_message("❌ Produto não encontrado.", ephemeral=True)
            return
        if interaction.user.id != produto["owner_id"]:
            await interaction.response.send_message(
                "❌ Apenas o dono da loja pode excluir produtos.", ephemeral=True
            )
            return

        produtos = carregar_produtos()
        if self.view.product_id in produtos:
            del produtos[self.view.product_id]
            salvar_produtos(produtos)

        await interaction.response.send_message("✅ Produto excluído com sucesso.", ephemeral=True)
        registrar_log(
            produto.get("channel_id", 0), "PRODUTO_EXCLUIDO",
            str(interaction.user), interaction.user.id,
            f"Produto: {produto.get('nome', self.view.product_id)}"
        )
        try:
            await interaction.message.delete()
        except Exception:
            pass
        print(f"✅ [LOJAS] Produto {self.view.product_id} excluído por {interaction.user.name}")


class ViewProduto(discord.ui.View):
    """View persistente anexada ao painel de cada produto"""

    def __init__(self, product_id: str) -> None:
        super().__init__(timeout=None)
        self.product_id = product_id
        self.add_item(BotaoEncomendar(product_id))
        self.add_item(BotaoEditar(product_id))
        self.add_item(BotaoBarganha(product_id))
        self.add_item(BotaoExcluir(product_id))


class BotaoLog(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Log",
            style=discord.ButtonStyle.secondary,
            emoji="📋",
            custom_id="loja_ver_log_btn"
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        loja = obter_loja_por_canal(interaction.channel_id or 0)
        if not loja:
            await interaction.response.send_message(
                "❌ Este canal não pertence a uma loja ativa.", ephemeral=True
            )
            return

        eh_dono = interaction.user.id == loja["owner_id"]
        eh_admin = (
            isinstance(interaction.user, discord.Member)
            and interaction.user.guild_permissions.administrator
        )
        if not (eh_dono or eh_admin):
            await interaction.response.send_message(
                "❌ Apenas o proprietário da loja ou administradores podem acessar o log.",
                ephemeral=True
            )
            return

        channel_id = interaction.channel_id or 0
        log_file = f"{LOGS_DIR}/loja_{channel_id}.json"

        if not os.path.exists(log_file):
            await interaction.response.send_message(
                "📋 Ainda não há registros no log desta loja.", ephemeral=True
            )
            return

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            await interaction.response.send_message(
                "❌ Erro ao ler o log da loja.", ephemeral=True
            )
            return

        linhas = [
            f"LOG DA LOJA: {loja['nome']}",
            f"Dono      : {loja['owner_name']} (ID: {loja['owner_id']})",
            f"Exportado : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            f"Eventos   : {len(logs)}",
            "=" * 60,
            ""
        ]
        for entrada in logs:
            ts = datetime.fromisoformat(entrada["timestamp"]).strftime("%d/%m/%Y %H:%M:%S")
            linhas.append(f"[{ts}] {entrada['tipo'].upper()}")
            linhas.append(f"  Usuário : {entrada['usuario']} (ID: {entrada['usuario_id']})")
            linhas.append(f"  Detalhe : {entrada['detalhes']}")
            linhas.append("")

        conteudo = "\n".join(linhas)
        arquivo = io.BytesIO(conteudo.encode("utf-8"))
        nome_arquivo = (
            f"log_loja_{channel_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        await interaction.response.send_message(
            f"📋 Log da loja **{loja['nome']}** — **{len(logs)}** evento(s):",
            file=discord.File(arquivo, filename=nome_arquivo),
            ephemeral=True
        )


class ViewGerenciarLoja(discord.ui.View):
    """View com botão Adicionar Produto — enviada ao criar a loja"""

    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(BotaoLog())

    @discord.ui.button(
        label="➕ Adicionar Produto",
        style=discord.ButtonStyle.green,
        emoji="🛍️",
        custom_id="loja_add_produto_btn"
    )
    async def adicionar_produto(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        loja = obter_loja_por_canal(interaction.channel_id or 0)
        if not loja:
            await interaction.response.send_message(
                "❌ Este canal não pertence a uma loja ativa.", ephemeral=True
            )
            return
        if interaction.user.id != loja["owner_id"]:
            await interaction.response.send_message(
                "❌ Apenas o proprietário da loja pode adicionar produtos.", ephemeral=True
            )
            return
        await interaction.response.send_modal(ModalAdicionarProduto())


# ============================================
# COG PRINCIPAL
# ============================================

class Lojas(commands.Cog):
    """Sistema de Lojas Pessoais"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Executa quando o bot está pronto"""
        import asyncio
        try:
            # Registrar views persistentes
            self.bot.add_view(ViewCriarLoja(self.bot))
            self.bot.add_view(ViewGerenciarLoja())

            # Registrar view de cada produto existente
            produtos_existentes = carregar_produtos()
            for pid in produtos_existentes:
                self.bot.add_view(ViewProduto(pid))
            print(f"✅ [LOJAS] Views registradas ({len(produtos_existentes)} produtos ativos)")
            
            # Aguardar um pouco para o bot ficar totalmente pronto
            await asyncio.sleep(2)
            
            # Criar/atualizar painel de lojas
            await self.atualizar_painel_lojas()
        except Exception as e:
            print(f"⚠️ [LOJAS] Erro ao inicializar: {e}")
            import traceback
            traceback.print_exc()
    
    async def atualizar_painel_lojas(self) -> None:
        """Cria ou atualiza o painel de lojas no canal - recriar ao reiniciar para garantir Views funcionem"""
        try:
            guild = self.bot.get_guild(1440802112601854159)  # GUILD_ID do config
            if not guild:
                print("⚠️ [LOJAS] Guild não encontrada")
                return
            
            # Obter o canal do painel
            canal = guild.get_channel(PANEL_CHANNEL_ID)
            if not isinstance(canal, discord.TextChannel):
                print(f"⚠️ [LOJAS] Canal {PANEL_CHANNEL_ID} não é um canal de texto")
                return
            
            # Deletar TODAS as mensagens antigas do bot no canal (fixadas ou não)
            try:
                msgs_antigas = [msg async for msg in canal.history(limit=50) if msg.author.id == self.bot.user.id]
                for msg_antiga in msgs_antigas:
                    try:
                        if msg_antiga.pinned:
                            await msg_antiga.unpin()
                        await msg_antiga.delete()
                        print(f"✅ [LOJAS] Mensagem anterior removida")
                    except Exception as e:
                        print(f"⚠️ [LOJAS] Erro ao deletar mensagem anterior: {e}")
            except Exception as e:
                print(f"⚠️ [LOJAS] Erro ao limpar canal: {e}")
            
            # Aguardar um pouco para evitar rate limit
            import asyncio
            await asyncio.sleep(1)
            
            # Criar NOVO painel com View recém-registrada
            painel_msg = await canal.send(
                "🏪 **SISTEMA DE COMÉRCIO**\n\n"
                "═══════════════════════════════════════\n\n"
                "**Bem-vindo ao sistema de comércio!**\n\n"
                "Clique no botão abaixo para criar sua própria loja "
                "e começar a vender seus recursos, dinossauros e serviços.\n\n"
                "**✨ Como Funciona:**\n"
                "1️⃣ Clique em \"Criar Minha Loja\"\n"
                "2️⃣ Defina um nome para sua loja\n"
                "3️⃣ Um canal exclusivo será criado para você\n"
                "4️⃣ Publique seus produtos!\n\n"
                "**⚙️ Gerenciamento:**\n"
                "• Use `!fecharloja` para encerrar sua loja\n"
                "• Você é o único que pode postar em sua loja\n"
                "• Lojas inativas podem ser reabertas\n\n"
                "**💡 Dicas:**\n"
                "• Descreva bem seus produtos\n"
                "• Inclua preços e disponibilidade\n"
                "• Seja claro na comunicação\n\n"
                "═══════════════════════════════════════",
                view=ViewCriarLoja(self.bot)
            )
            
            # Fixar a mensagem
            await painel_msg.pin()
            print(f"✅ [LOJAS] Painel recriado e fixado no canal {PANEL_CHANNEL_ID}")
            
        except Exception as e:
            print(f"❌ [LOJAS] Erro ao atualizar painel: {e}")
    
    @commands.command(name="fecharloja", description="Fecha sua loja pessoal")
    async def fecharloja(self, ctx: commands.Context) -> None:
        """Fecha a loja do jogador - funciona apenas na sala de comandos ou no canal da loja"""
        
        # Verificar se o comando está sendo executado no canal correto
        if ctx.channel.id != COMMAND_CHANNEL_ID:
            # Verificar se está no canal de uma loja do usuário
            loja = obter_loja_jogador(ctx.author.id)
            if not loja or loja.get("channel_id") != ctx.channel.id:
                await ctx.send(
                    f"❌ Este comando só pode ser usado na sala de comandos ({ctx.guild.get_channel(COMMAND_CHANNEL_ID).mention}) "
                    f"ou no canal da sua loja.",
                    delete_after=5
                )
                return
        
        try:
            # Obter loja do jogador
            loja = obter_loja_jogador(ctx.author.id)
            
            if not loja:
                await ctx.send(
                    "❌ Você não possui uma loja ativa.",
                    delete_after=5
                )
                return
            
            # Atualizar status
            lojas = carregar_lojas()
            user_id_str = str(ctx.author.id)
            lojas[user_id_str]["ativa"] = False
            lojas[user_id_str]["fechada_em"] = datetime.now().isoformat()
            salvar_lojas(lojas)
            
            # Tentar renomear o canal para indicar fechamento
            try:
                guild = ctx.guild
                if guild:
                    canal = guild.get_channel(loja["channel_id"])
                    if canal and isinstance(canal, discord.TextChannel):
                        await canal.edit(name=f"🔒-{canal.name[-25:]}", topic="LOJA FECHADA")
            except Exception as e:
                print(f"⚠️ [LOJAS] Erro ao fechar canal: {e}")
            
            await ctx.send(
                f"✅ **Loja Fechada**\n\n"
                f"Sua loja **{loja['nome']}** foi arquivada.\n"
                f"Você pode criar uma nova loja a qualquer momento!",
                delete_after=10
            )
            
            print(f"✅ [LOJAS] Loja fechada para {ctx.author.name} ({ctx.author.id})")
            
        except Exception as e:
            print(f"❌ [LOJAS] Erro ao fechar loja: {e}")
            await ctx.send(
                f"❌ Erro ao fechar a loja: {str(e)}",
                delete_after=5
            )
    
    @app_commands.command(name="minhas_lojas", description="Mostra informações sobre suas lojas")
    async def minhas_lojas(self, interaction: discord.Interaction) -> None:
        """Mostra informações sobre as lojas do jogador"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            lojas = carregar_lojas()
            user_id_str = str(interaction.user.id)
            
            if user_id_str not in lojas:
                await interaction.followup.send(
                    "❌ Você ainda não criou nenhuma loja.",
                    ephemeral=True
                )
                return
            
            loja = lojas[user_id_str]
            status = "✅ Ativa" if loja.get("ativa", False) else "🔒 Inativa"
            
            # Obter o link do canal
            guild = interaction.guild
            canal = None
            if guild:
                canal = guild.get_channel(loja.get("channel_id"))
            
            canal_link = f"{canal.mention}" if canal else "Canal não encontrado"
            
            embed = discord.Embed(
                title="🏪 Minhas Lojas",
                color=discord.Color.green()
            )
            embed.add_field(
                name=f"Loja: {loja['nome']}",
                value=(
                    f"**Status:** {status}\n"
                    f"**Acesso:** {canal_link}\n"
                    f"**Criada em:** <t:{int(datetime.fromisoformat(loja['criada_em']).timestamp())}:f>\n"
                ),
                inline=False
            )
            
            if not loja.get("ativa", False) and "fechada_em" in loja:
                embed.add_field(
                    name="Reabertura",
                    value="Use `/criar_loja` novamente para reabrir uma loja",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"❌ [LOJAS] Erro ao obter lojas: {e}")
            await interaction.followup.send(
                f"❌ Erro ao buscar suas lojas: {str(e)}",
                ephemeral=True
            )
    
    @commands.command(name="lojastart", description="Verifica e cria o painel de lojas se necessário")
    @commands.has_permissions(administrator=True)
    async def lojastart(self, ctx: commands.Context) -> None:
        """Verifica se o painel existe e o cria se necessário"""
        
        try:
            guild = ctx.guild
            if not guild:
                await ctx.send("❌ Erro: Não foi possível identificar o servidor.")
                return
            
            # Obter o canal do painel
            canal_painel = guild.get_channel(PANEL_CHANNEL_ID)
            if not isinstance(canal_painel, discord.TextChannel):
                await ctx.send(
                    f"❌ Erro: Canal de painel ({PANEL_CHANNEL_ID}) não encontrado ou inválido."
                )
                return
            
            # Verificar se já existe mensagem fixada
            try:
                mensagens_fixadas = [msg async for msg in canal_painel.history() if msg.pinned]
                if mensagens_fixadas:
                    await ctx.send(
                        f"✅ **Painel já existe!**\n\n"
                        f"O painel de lojas está disponível em {canal_painel.mention}\n"
                        f"Mensagens fixadas encontradas: {len(mensagens_fixadas)}"
                    )
                    print(f"✅ [LOJAS] Painel verificado - já existe no canal {PANEL_CHANNEL_ID}")
                    return
            except Exception as e:
                print(f"⚠️ [LOJAS] Erro ao verificar mensagens fixadas: {e}")
            
            # Criar o painel se não existir
            painel_msg = await canal_painel.send(
                "🏪 **SISTEMA DE LOJAS PESSOAIS**\n\n"
                "═══════════════════════════════════════\n\n"
                "**Bem-vindo ao sistema de lojas!**\n\n"
                "Clique no botão abaixo para criar sua própria loja "
                "e começar a vender seus recursos, dinossauros e serviços.\n\n"
                "**✨ Como Funciona:**\n"
                "1️⃣ Clique em \"Criar Minha Loja\"\n"
                "2️⃣ Defina um nome para sua loja\n"
                "3️⃣ Um canal exclusivo será criado para você\n"
                "4️⃣ Publique seus produtos!\n\n"
                "**⚙️ Gerenciamento:**\n"
                "• Use `/fechar_loja` para encerrar sua loja\n"
                "• Você é o único que pode postar em sua loja\n"
                "• Lojas inativas podem ser reabertas\n\n"
                "**💡 Dicas:**\n"
                "• Descreva bem seus produtos\n"
                "• Inclua preços e disponibilidade\n"
                "• Seja claro na comunicação\n\n"
                "═══════════════════════════════════════",
                view=ViewCriarLoja(self.bot)
            )
            
            # Fixar a mensagem
            await painel_msg.pin()
            
            await ctx.send(
                f"✅ **Painel criado e fixado com sucesso!**\n\n"
                f"O painel de lojas está disponível em {canal_painel.mention}"
            )
            
            print(f"✅ [LOJAS] Painel criado e fixado no canal {PANEL_CHANNEL_ID}")
            
        except Exception as e:
            print(f"❌ [LOJAS] Erro ao verificar/criar painel: {e}")
            await ctx.send(
                f"❌ Erro ao verificar/criar painel: {str(e)}"
            )

# ============================================
# SETUP
# ============================================

async def setup(bot: commands.Bot) -> None:
    """Carrega o cog"""
    await bot.add_cog(Lojas(bot))
    print("✅ [LOJAS] Cog carregado com sucesso")
