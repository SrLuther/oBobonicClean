"""
Sistema de Lojas Pessoais para ARK Survival Evolved
Permite que jogadores criem suas próprias lojas usando tópicos de fórum
"""

import discord
from discord.ext import commands
from discord import app_commands
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
            
            # Enviar dicas de formatação no canal específico
            try:
                canal_tips = interaction.guild.get_channel(TIPS_CHANNEL_ID)
                if canal_tips:
                    embed_tips = discord.Embed(
                        title=f"📝 Dicas de Formatação - {self.nome_loja.value}",
                        description=f"Loja do(a) {interaction.user.mention}",
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
# COG PRINCIPAL
# ============================================

class Lojas(commands.Cog):
    """Sistema de Lojas Pessoais"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Executa quando o bot está pronto"""
        try:
            # Registrar a view persistente
            self.bot.add_view(ViewCriarLoja(self.bot))
            print("✅ [LOJAS] View persistente registrada")
            
            # Criar/atualizar painel de lojas
            await self.atualizar_painel_lojas()
        except Exception as e:
            print(f"⚠️ [LOJAS] Erro ao inicializar: {e}")
    
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
            
            # Verificar e deletar mensagem antiga fixada
            try:
                mensagens_fixadas = [msg async for msg in canal.history(limit=50) if msg.pinned and msg.author.id == self.bot.user.id]
                if mensagens_fixadas:
                    for msg_antiga in mensagens_fixadas:
                        try:
                            await msg_antiga.unpin()
                            await msg_antiga.delete()
                            print(f"✅ [LOJAS] Painel anterior deletado e despinado")
                        except Exception as e:
                            print(f"⚠️ [LOJAS] Erro ao deletar painel anterior: {e}")
                            pass
            except Exception as e:
                print(f"⚠️ [LOJAS] Erro ao verificar mensagens fixadas: {e}")
            
            # Aguardar um pouco para evitar rate limit
            import asyncio
            await asyncio.sleep(1)
            
            # Criar NOVO painel com View recém-registrada
            painel_msg = await canal.send(
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
