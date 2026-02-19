"""
Sistema de Avaliação de Dinossauros para ARK
Calcula valor de venda baseado em stats e tipo/uso
Com painel interativo no Discord
"""

import discord
from discord.ext import commands
from discord import ui
import json
import os
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import asyncio

# ============================================
# CONFIGURAÇÃO
# ============================================
DINO_PRICES_FILE = "data/dino_prices.json"
VALUATION_HISTORY_FILE = "data/valuation_history.json"
PAINEL_CONFIG_FILE = "data/dino_painel.json"
VALUATION_CHANNEL_ID = 1474164587141271709  # Canal para avaliações

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def carregar_dados_dinos() -> dict:
    """Carrega dados de dinossauros do JSON"""
    if not os.path.exists(DINO_PRICES_FILE):
        return {}
    
    try:
        with open(DINO_PRICES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def carregar_historico() -> dict:
    """Carrega histórico de avaliações"""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    if not os.path.exists(VALUATION_HISTORY_FILE):
        with open(VALUATION_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2, ensure_ascii=False)
        return {}
    
    try:
        with open(VALUATION_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def salvar_historico(historico: dict) -> None:
    """Salva histórico de avaliações"""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    with open(VALUATION_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)


def carregar_painel_config() -> dict:
    """Carrega configuração do painel (ID da mensagem)"""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    if not os.path.exists(PAINEL_CONFIG_FILE):
        return {"painel_message_id": None}
    
    try:
        with open(PAINEL_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"painel_message_id": None}


def salvar_painel_config(config: dict) -> None:
    """Salva configuração do painel"""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    with open(PAINEL_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def formatar_moeda(valor: int) -> str:
    """Retorna a moeda formatada com singular/plural correto"""
    moeda = "Arkium" if valor == 1 else "Arkiums"
    return f"{valor} {moeda}"


def encontrar_dino(nome_procurado: str, dados: dict) -> Optional[Tuple[str, dict]]:
    """Encontra dinossauro por nome (fuzzy matching)"""
    nome_procurado = nome_procurado.lower().strip()
    
    # Busca exata primeiro
    if nome_procurado in dados.get("dinosaurs", {}):
        key = nome_procurado
        return key, dados["dinosaurs"][key]
    
    # Busca parcial
    for key, dino in dados.get("dinosaurs", {}).items():
        if nome_procurado in key or nome_procurado in dino.get("name", "").lower():
            return key, dino
    
    return None


def calcular_valor_dino(
    especie: str,
    stats: Dict[str, int],
    tipo_uso: Optional[str] = None,
    dados: Optional[dict] = None,
    eh_castrado: bool = False
) -> Dict[str, Any]:
    """Calcula o valor de um dinossauro baseado em stats e tipo de uso
    Se eh_castrado=True, o valor final é reduzido em 50%
    """
    if dados is None:
        dados = carregar_dados_dinos()
    
    resultado = {
        "especie": especie,
        "valor_total": 0,
        "breakdown": {},
        "analise": "",
        "tier": "Comum",
        "recomendacoes": [],
        "eh_castrado": eh_castrado
    }
    
    # Encontrar dinossauro
    dino_info = encontrar_dino(especie, dados)
    if not dino_info:
        resultado["analise"] = f"❌ Dinossauro '{especie}' não encontrado no banco de dados."
        return resultado
    
    dino_key, dino = dino_info
    resultado["especie"] = dino.get("name", especie)
    base_value = dino.get("base_value", 1000)
    stat_multipliers = dino.get("stat_multipliers", {})
    
    # Calcular valor por stat
    valor_stats = base_value
    resultado["breakdown"]["valor_base"] = base_value
    
    for stat_name, stat_value in stats.items():
        if stat_name in stat_multipliers:
            multiplier = stat_multipliers[stat_name]
            contribuicao = stat_value * multiplier
            valor_stats += contribuicao
            resultado["breakdown"][f"{stat_name}_value"] = int(contribuicao)
    
    # Aplicar bônus de tipo de uso
    bonus_tipo_uso = 1.0
    tipo_uso_info = None
    
    if tipo_uso:
        tipo_uso = tipo_uso.lower()
        tipos_disponiveis = dados.get("usage_types", {})
        
        if tipo_uso in tipos_disponiveis:
            tipo_uso_info = tipos_disponiveis[tipo_uso]
            bonus_tipo_uso = tipo_uso_info.get("bonus_multiplier", 1.0)
            resultado["tipo_uso"] = tipo_uso_info.get("name", tipo_uso)
            resultado["breakdown"]["bonus_tipo_uso"] = int(valor_stats * (bonus_tipo_uso - 1.0))
    
    # Calcular valor final
    valor_final = int(valor_stats * bonus_tipo_uso)
    
    # Aplicar desconto se castrado
    if eh_castrado:
        valor_final = int(valor_final * 0.5)  # Reduz 50% do valor
        resultado["breakdown"]["desconto_castrado"] = -int(valor_final)  # Mostra o desconto negativo
    
    resultado["valor_total"] = valor_final
    resultado["bonus_tipo_uso_multiplier"] = bonus_tipo_uso
    
    # Classificar tier
    if valor_final < 500:
        resultado["tier"] = "🟤 Comum"
    elif valor_final < 2000:
        resultado["tier"] = "🟢 Raro"
    elif valor_final < 5000:
        resultado["tier"] = "🔵 Épico"
    elif valor_final < 8000:
        resultado["tier"] = "🟣 Lendário"
    else:
        resultado["tier"] = "🟡 Mítico"
    
    # Análise de stats
    analise_stats = []
    optimal = dino.get("optimal_stats", {})
    
    for stat_name, stat_value in stats.items():
        if stat_name in optimal:
            optimal_value = optimal[stat_name]
            percentual = (stat_value / optimal_value) * 100
            
            if percentual >= 90:
                analise_stats.append(f"✅ {stat_name.upper()}: {stat_value} ({percentual:.0f}% do ótimo)")
            elif percentual >= 70:
                analise_stats.append(f"⚠️ {stat_name.upper()}: {stat_value} ({percentual:.0f}% do ótimo)")
            else:
                analise_stats.append(f"❌ {stat_name.upper()}: {stat_value} ({percentual:.0f}% do ótimo)")
    
    resultado["analise_stats"] = analise_stats
    
    # Recomendações
    if bonus_tipo_uso >= 1.3:
        resultado["recomendacoes"].append(f"🎯 Excelente para {tipo_uso_info.get('description', tipo_uso) if tipo_uso_info else 'este uso'}!")
    elif bonus_tipo_uso >= 1.15:
        resultado["recomendacoes"].append(f"👍 Bom para {tipo_uso_info.get('description', tipo_uso) if tipo_uso_info else 'este uso'}")
    
    return resultado


# ============================================
# VIEWS E MODALS
# ============================================

class StatsModal(ui.Modal):
    """Modal para inserir os stats do dinossauro"""
    
    def __init__(self, dino_id: str, dados: dict):
        super().__init__(title="Inserir Stats do Dinossauro")
        self.dino_id = dino_id
        self.dados = dados
    
    melee = ui.TextInput(label="Melee Damage", required=False, placeholder="0", default="0")
    health = ui.TextInput(label="Health/Saúde", required=False, placeholder="0", default="0")
    stamina = ui.TextInput(label="Stamina", required=False, placeholder="0", default="0")
    weight = ui.TextInput(label="Weight/Peso", required=False, placeholder="0", default="0")
    oxygen = ui.TextInput(label="Oxygen/Oxigênio", required=False, placeholder="0", default="0")
    food = ui.TextInput(label="Food/Comida", required=False, placeholder="0", default="0")
    castrado = ui.TextInput(label="Castrado? (sim/não)", required=False, placeholder="não", default="não")
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Processa o envio do modal"""
        await interaction.response.defer()
        
        # Extrair dados do modal
        stats = {}
        eh_castrado = False
        
        try:
            if self.melee.value and self.melee.value != "0":
                stats["melee"] = int(self.melee.value)
            if self.health.value and self.health.value != "0":
                stats["health"] = int(self.health.value)
            if self.stamina.value and self.stamina.value != "0":
                stats["stamina"] = int(self.stamina.value)
            if self.weight.value and self.weight.value != "0":
                stats["weight"] = int(self.weight.value)
            if self.oxygen.value and self.oxygen.value != "0":
                stats["oxygen"] = int(self.oxygen.value)
            if self.food.value and self.food.value != "0":
                stats["food"] = int(self.food.value)
            
            # Verificar se é castrado
            if self.castrado.value.lower() in ["sim", "yes", "s", "y", "1", "true"]:
                eh_castrado = True
        except ValueError:
            embed = discord.Embed(
                title="❌ Erro",
                description="Um ou mais valores não são números válidos!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        if not stats:
            embed = discord.Embed(
                title="❌ Erro",
                description="Você precisa preencher pelo menos um stat!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Calcular valor
        resultado = calcular_valor_dino(self.dino_id, stats, None, self.dados, eh_castrado)
        
        # Enviar resultado
        embed = discord.Embed(
            title=f"💎 {resultado['especie']}",
            description=resultado.get("tipo_uso", ""),
            color=self._get_tier_color(resultado["tier"])
        )
        
        # Adicionar status de castrado se aplicável
        status_castrado = " 🔪 **(CASTRADO - 50% OFF)**" if eh_castrado else ""
        
        embed.add_field(
            name="💰 Valor Total",
            value=f"`{formatar_moeda(resultado['valor_total'])}` {resultado['tier']}{status_castrado}",
            inline=False
        )
        
        breakdown_text = f"Base: `{formatar_moeda(resultado['breakdown'].get('valor_base', 0))}`\n"
        for stat_name in ["melee", "health", "stamina", "weight", "oxygen", "food"]:
            if f"{stat_name}_value" in resultado["breakdown"]:
                valor_stat = resultado["breakdown"][f"{stat_name}_value"]
                if stats.get(stat_name, 0) > 0:
                    breakdown_text += f"{stat_name.capitalize()}: `+{formatar_moeda(valor_stat)}`\n"
        
        if eh_castrado and "desconto_castrado" in resultado["breakdown"]:
            breakdown_text += f"**Desconto Castrado: `-50%`**\n"
        
        embed.add_field(name="📊 Breakdown", value=breakdown_text, inline=False)
        
        if resultado.get("analise_stats"):
            analise_text = "\n".join(resultado["analise_stats"])
            embed.add_field(name="📈 Análise de Stats", value=analise_text, inline=False)
        
        if resultado.get("recomendacoes"):
            embed.add_field(name="💡 Recomendações", value="\n".join(resultado["recomendacoes"]), inline=False)
        
        await interaction.followup.send(embed=embed)
    
    @staticmethod
    def _get_tier_color(tier: str) -> discord.Color:
        """Retorna cor baseado no tier"""
        if "Comum" in tier:
            return discord.Color.greyple()
        elif "Raro" in tier:
            return discord.Color.green()
        elif "Épico" in tier:
            return discord.Color.blue()
        elif "Lendário" in tier:
            return discord.Color.purple()
        else:
            return discord.Color.gold()


class SearchDinoModal(ui.Modal):
    """Modal para buscar dinossauro por nome"""
    
    search_input = ui.TextInput(
        label="Digite o nome do dinossauro",
        placeholder="Ex: carc, rex, trike, allo...",
        min_length=1,
        max_length=100,
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, dados: dict):
        super().__init__(title="🔍 Buscar Dinossauro")
        self.dados = dados
    
    async def on_submit(self, interaction: discord.Interaction):
        """Processa a busca"""
        await interaction.response.defer()
        
        search_text = str(self.search_input).lower().strip()
        dinos = self.dados.get("dinosaurs", {})
        
        # Filtrar dinossauros que correspondem ao search
        resultados = {}
        for key, dino in dinos.items():
            nome = dino.get("name", key).lower()
            if search_text in nome:
                resultados[key] = dino
        
        # Resultado da busca
        if not resultados:
            embed = discord.Embed(
                title="❌ Nenhum Dinossauro Encontrado",
                description=f"Nenhum dinossauro contém '{search_text}' no nome.\n\n"
                           f"Tente: T-Rex, Trike, Allosaurus, Carcharino...",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Se encontrou apenas 1, vai direto para stats
        if len(resultados) == 1:
            dino_id = list(resultados.keys())[0]
            modal = StatsModal(dino_id, self.dados)
            await interaction.response.send_modal(modal)
            return
        
        # Se encontrou múltiplos, mostra um Select
        select_view = DinoSearchSelectView(self.dados, resultados)
        
        embed = discord.Embed(
            title="🦖 Dinossauros Encontrados",
            description=f"Encontrei {len(resultados)} dinossauro(s) que correspondem a '{search_text}'.\n"
                       f"Escolha um abaixo:",
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, view=select_view, ephemeral=True)


class DinoSearchSelect(ui.Select):
    """Select para escolher entre dinossauros encontrados"""
    
    def __init__(self, dados: dict, resultados: dict):
        self.dados = dados
        self.todos_dinos = resultados
        
        opcoes = []
        for key, dino in list(resultados.items())[:25]:
            nome = dino.get("name", key)
            valor_base = dino.get("base_value", 0)
            opcoes.append(
                discord.SelectOption(
                    label=f"{nome}",
                    value=key,
                    description=f"Base: {valor_base} Arkiums"
                )
            )
        
        super().__init__(
            placeholder="Selecione um dinossauro...",
            min_values=1,
            max_values=1,
            options=opcoes if opcoes else [discord.SelectOption(label="Nenhum", value="none")]
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback quando o dinossauro é selecionado"""
        dino_id = self.values[0]
        modal = StatsModal(dino_id, self.dados)
        await interaction.response.send_modal(modal)


class DinoSearchSelectView(ui.View):
    """View para o select de dinossauros encontrados"""
    
    def __init__(self, dados: dict, resultados: dict):
        super().__init__()
        self.dados = dados
        self.resultados = resultados
        self.add_item(DinoSearchSelect(dados, resultados))
    
    async def on_timeout(self) -> None:
        """Chamado quando o view expira"""
        pass


class DinoSelect(ui.Select):
    """Select para escolher o dinossauro"""
    
    def __init__(self, dados: dict):
        self.dados = dados
        dinos = dados.get("dinosaurs", {})
        
        opcoes = []
        for i, (key, dino) in enumerate(list(dinos.items())[:25]):
            nome = dino.get("name", key)
            valor_base = dino.get("base_value", 0)
            opcoes.append(
                discord.SelectOption(
                    label=f"{nome} (Base: {valor_base})",
                    value=key,
                    description=f"ID: {key}"
                )
            )
        
        super().__init__(
            placeholder="Escolha um dinossauro...",
            min_values=1,
            max_values=1,
            options=opcoes if opcoes else [discord.SelectOption(label="Nenhum", value="none")]
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback quando o dinossauro é selecionado"""
        dino_id = self.values[0]
        modal = StatsModal(dino_id, self.dados)
        await interaction.response.send_modal(modal)


class DinoSelectView(ui.View):
    """View para o select de dinossauros"""
    
    def __init__(self, dados: dict):
        super().__init__()
        self.dados = dados
        self.add_item(DinoSelect(dados))
    
    async def on_timeout(self) -> None:
        """Chamado quando o view expira"""
        pass


class ValuationPanelView(ui.View):
    """View para o painel principal de avaliação"""
    
    def __init__(self, bot: commands.Bot, dados: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.dados = dados
    
    @ui.button(label="💎 Avaliar Dinossauro", style=discord.ButtonStyle.primary, custom_id="avaliar_dino_btn")
    async def avaliar_button(self, interaction: discord.Interaction, button: ui.Button):
        """Abre o modal de busca de dinossauro"""
        modal = SearchDinoModal(self.dados)
        await interaction.response.send_modal(modal)


class DinosaurValuerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        print("[DINOSAUR] ✅ DinosaurValuerCog INICIALIZADO!")
        self.bot = bot
        self.dados = carregar_dados_dinos()
        self.painel_criado = False
    
    async def cog_load(self):
        """Ajusta a persistência do painel"""
        print("[DINOSAUR] ✅ cog_load() foi chamado!")
        self.bot.add_view(ValuationPanelView(self.bot, self.dados))
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Verifica e cria o painel ao iniciar"""
        if self.painel_criado:
            return
        
        self.painel_criado = True
        print("[PAINEL DINOSAURO] on_ready foi acionado!")
        
        try:
            print("[PAINEL DINOSAURO] Carregando configuração do painel...")
            config = carregar_painel_config()
            print(f"[PAINEL DINOSAURO] Config carregada: {config}")
            
            guild = self.bot.get_guild(1440802112601854159)
            print(f"[PAINEL DINOSAURO] Guild obtida: {guild}")
            
            if not guild:
                print("[PAINEL] ❌ Guild não encontrada")
                return
            
            canal = guild.get_channel(VALUATION_CHANNEL_ID)
            print(f"[PAINEL DINOSAURO] Canal obtido: {canal}")
            
            if not canal:
                print(f"[PAINEL] ❌ Canal {VALUATION_CHANNEL_ID} não encontrado")
                return
            
            # Verificar se o painel já existe
            painel_msg_id = config.get("painel_message_id")
            print(f"[PAINEL DINOSAURO] ID do painel na config: {painel_msg_id}")
            
            if painel_msg_id:
                try:
                    msg = await canal.fetch_message(painel_msg_id)
                    print(f"✅ [PAINEL] Painel de dinossauros já existe (ID: {painel_msg_id})")
                    self.bot.add_view(ValuationPanelView(self.bot, self.dados))
                    return
                except discord.NotFound:
                    print("[PAINEL] ❌ Painel anterior não encontrado, criando novo...")
            else:
                print("[PAINEL] Nenhum painel na config, criando novo...")
            
            # Criar novo painel
            print("[PAINEL DINOSAURO] Criando novo painel...")
            embed = discord.Embed(
                title="🦖 CALCULADORA DE VALOR DE DINOSSAUROS",
                description=(
                    "Bem-vindo ao sistema de avaliação de dinossauros!\n\n"
                    "**Como usar:**\n"
                    "1. Clique no botão abaixo\n"
                    "2. Selecione o tipo de dinossauro\n"
                    "3. Preencha os stats (Melee, Health, Stamina, etc)\n"
                    "4. Receba a avaliação detalhada\n\n"
                    "**Nossas Categorias:**\n"
                    "⚔️ **PvP Combat** - Dinossauros de combate PvP (bonus x1.3)\n"
                    "🐉 **PvE Combat** - Para derrotar bosses (bonus x1.2)\n"
                    "⛏️ **Farming** - Para coletar recursos (bonus x1.15)\n"
                    "🚚 **Transporte** - Para carregar/voar (bonus x1.25)\n"
                    "🥚 **Criação** - Para reprodução (bonus x1.4)\n"
                    "🔧 **Utilidade** - Funções especiais (bonus x1.1)\n\n"
                    "**Dinossauros Disponíveis:** "
                    f"{len(self.dados.get('dinosaurs', {}))} espécies diferentes!\n\n"
                    "═══════════════════════════════════════"
                ),
                color=discord.Color.gold()
            )
            
            embed.set_footer(text="Sistema de Avaliação ARK | Clique no botão para começar!")
            
            view = ValuationPanelView(self.bot, self.dados)
            msg = await canal.send(embed=embed, view=view)
            await msg.pin()
            
            # Salvar ID do painel
            salvar_painel_config({"painel_message_id": msg.id})
            print(f"✅ [PAINEL] Painel de dinossauros criado automaticamente (ID: {msg.id})")
        
        except Exception as e:
            print(f"❌ [PAINEL] Erro ao criar painel: {e}")
            import traceback
            traceback.print_exc()
    
    @commands.command(name="criarcalc", aliases=["criarpainel"])
    @commands.has_permissions(administrator=True)
    async def criar_painel(self, ctx: commands.Context):
        """Cria o painel de avaliação de dinossauros no canal designado"""
        try:
            canal = ctx.guild.get_channel(VALUATION_CHANNEL_ID)
            
            if not canal:
                embed = discord.Embed(
                    title="❌ Erro",
                    description=f"Canal com ID `{VALUATION_CHANNEL_ID}` não encontrado!",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            
            # Criar embed do painel
            embed = discord.Embed(
                title="🦖 CALCULADORA DE VALOR DE DINOSSAUROS",
                description=(
                    "Bem-vindo ao sistema de avaliação de dinossauros!\n\n"
                    "**Como usar:**\n"
                    "1. Clique no botão abaixo\n"
                    "2. Selecione o tipo de dinossauro\n"
                    "3. Preencha os stats (Melee, Health, Stamina, etc)\n"
                    "4. Receba a avaliação detalhada\n\n"
                    "**Nossas Categorias:**\n"
                    "⚔️ **PvP Combat** - Dinossauros de combate PvP (bonus x1.3)\n"
                    "🐉 **PvE Combat** - Para derrotar bosses (bonus x1.2)\n"
                    "⛏️ **Farming** - Para coletar recursos (bonus x1.15)\n"
                    "🚚 **Transporte** - Para carregar/voar (bonus x1.25)\n"
                    "🥚 **Criação** - Para reprodução (bonus x1.4)\n"
                    "🔧 **Utilidade** - Funções especiais (bonus x1.1)\n\n"
                    "**Dinossauros Disponíveis:** "
                    f"{len(self.dados.get('dinosaurs', {}))} espécies diferentes!\n\n"
                    "═══════════════════════════════════════"
                ),
                color=discord.Color.gold()
            )
            
            embed.set_footer(text="Sistema de Avaliação ARK | Clique no botão para começar!")
            
            view = ValuationPanelView(self.bot, self.dados)
            msg = await canal.send(embed=embed, view=view)
            await msg.pin()
            
            # Salvar ID do painel
            salvar_painel_config({"painel_message_id": msg.id})
            
            confirm_embed = discord.Embed(
                title="✅ Painel Criado",
                description=f"Painel criado com sucesso no canal {canal.mention}!",
                color=discord.Color.green()
            )
            await ctx.send(embed=confirm_embed)
        
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Erro ao criar painel",
                description=f"Erro: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
    
    @commands.command(name="tipos")
    async def tipos_comando(self, ctx: commands.Context):
        """Mostra os tipos de uso disponíveis para dinossauros"""
        embed = discord.Embed(
            title="📋 Tipos de Uso de Dinossauros",
            description="Use esses tipos com o painel interativo",
            color=discord.Color.blue()
        )
        
        tipos = self.dados.get("usage_types", {})
        
        for tipo_key, tipo_info in tipos.items():
            nome = tipo_info.get("name", tipo_key)
            desc = tipo_info.get("description", "")
            bonus = tipo_info.get("bonus_multiplier", 1.0)
            icon = tipo_info.get("icon", "")
            
            embed.add_field(
                name=f"{icon} {nome}",
                value=f"{desc}\nBônus: x{bonus:.2f}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="dinos")
    async def dinos_comando(self, ctx: commands.Context):
        """Lista todos os dinossauros no banco de dados"""
        dinos = self.dados.get("dinosaurs", {})
        
        embed = discord.Embed(
            title="🦖 Dinossauros Disponíveis",
            description=f"Total: {len(dinos)} dinossauros",
            color=discord.Color.green()
        )
        
        dino_list = ""
        for i, (key, dino) in enumerate(list(dinos.items())[:20]):
            nome = dino.get("name", key)
            valor_base = dino.get("base_value", 0)
            dino_list += f"`{key}` - {nome} (Base: {formatar_moeda(valor_base)})\n"
        
        embed.add_field(
            name="Dinossauros",
            value=dino_list if dino_list else "Nenhum encontrado",
            inline=False
        )
        
        if len(dinos) > 20:
            embed.add_field(
                name="📌 Nota",
                value=f"Mostrando 20 de {len(dinos)} dinossauros",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="historico")
    async def historico_comando(self, ctx: commands.Context):
        """Mostra o histórico de avaliações do servidor"""
        historico = carregar_historico()
        
        if not historico:
            embed = discord.Embed(
                title="📜 Histórico de Avaliações",
                description="Nenhuma avaliação realizada ainda",
                color=discord.Color.greyple()
            )
            await ctx.send(embed=embed)
            return
        
        # Pegar últimas 10 avaliações
        avaliacoes = list(historico.values())[-10:]
        avaliacoes.reverse()
        
        embed = discord.Embed(
            title="📜 Histórico de Avaliações",
            description=f"Últimas {len(avaliacoes)} avaliações",
            color=discord.Color.gold()
        )
        
        for aval in avaliacoes:
            data = aval.get("data", "Data desconhecida")
            usuario = aval.get("usuario", "Desconhecido")
            especie = aval.get("especie", "?")
            valor = aval.get("valor_total", 0)
            
            embed.add_field(
                name=f"{especie} - {formatar_moeda(valor)}",
                value=f"Por: {usuario} | {data}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    def _salvar_avaliacao(self, user_id: int, username: str, resultado: dict) -> None:
        """Salva avaliação no histórico"""
        historico = carregar_historico()
        
        aval_id = len(historico) + 1
        historico[str(aval_id)] = {
            "id": aval_id,
            "usuario_id": user_id,
            "usuario": username,
            "especie": resultado.get("especie", "?"),
            "valor_total": resultado.get("valor_total", 0),
            "tier": resultado.get("tier", "?"),
            "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        
        salvar_historico(historico)
    
    def _get_tier_color(self, tier: str) -> discord.Color:
        """Retorna cor baseado no tier"""
        if "Comum" in tier:
            return discord.Color.greyple()
        elif "Raro" in tier:
            return discord.Color.green()
        elif "Épico" in tier:
            return discord.Color.blue()
        elif "Lendário" in tier:
            return discord.Color.purple()
        else:
            return discord.Color.gold()


async def setup(bot: commands.Bot):
    print("[DINOSAUR] 🦖 setup() INICIADO!")
    cog = DinosaurValuerCog(bot)
    await bot.add_cog(cog)
    print("[DINOSAUR] 🦖 Cog adicionado!")
    
    # Adicionar persistência do painel
    bot.add_view(ValuationPanelView(bot, cog.dados))
    print("[DINOSAUR] 🦖 View adicionada!")
    
    # Criar painel automaticamente
    print("[DINOSAUR] 🦖 Iniciando criação do painel...")
    try:
        guild = bot.get_guild(1440802112601854159)
        print(f"[DINOSAUR] Guild obtida: {guild}")
        
        if guild:
            canal = guild.get_channel(VALUATION_CHANNEL_ID)
            print(f"[DINOSAUR] Canal obtido: {canal}")
            
            if canal:
                config = carregar_painel_config()
                painel_msg_id = config.get("painel_message_id")
                
                if painel_msg_id:
                    try:
                        msg = await canal.fetch_message(painel_msg_id)
                        print(f"[DINOSAUR] ✅ Painel já existe (ID: {painel_msg_id})")
                    except discord.NotFound:
                        print("[DINOSAUR] Painel anterior não encontrado, criando novo...")
                        # Criar novo painel
                        await criar_painel_automatico(bot, canal, cog.dados)
                else:
                    print("[DINOSAUR] Nenhum painel na config, criando novo...")
                    # Criar novo painel
                    await criar_painel_automatico(bot, canal, cog.dados)
        else:
            print("[DINOSAUR] ❌ Guild não encontrada")
    except Exception as e:
        print(f"[DINOSAUR] ❌ Erro ao criar painel no setup: {e}")
        import traceback
        traceback.print_exc()


async def criar_painel_automatico(bot: commands.Bot, canal: discord.TextChannel, dados: dict):
    """Cria o painel automaticamente"""
    try:
        print("[DINOSAUR] Criando painel...")
        embed = discord.Embed(
            title="🦖 CALCULADORA DE VALOR DE DINOSSAUROS",
            description=(
                "Bem-vindo ao sistema de avaliação de dinossauros!\n\n"
                "**Como usar:**\n"
                "1. Clique no botão abaixo\n"
                "2. Selecione o tipo de dinossauro\n"
                "3. Preencha os stats (Melee, Health, Stamina, etc)\n"
                "4. Receba a avaliação detalhada\n\n"
                "**Nossas Categorias:**\n"
                "⚔️ **PvP Combat** - Dinossauros de combate PvP (bonus x1.3)\n"
                "🐉 **PvE Combat** - Para derrotar bosses (bonus x1.2)\n"
                "⛏️ **Farming** - Para coletar recursos (bonus x1.15)\n"
                "🚚 **Transporte** - Para carregar/voar (bonus x1.25)\n"
                "🥚 **Criação** - Para reprodução (bonus x1.4)\n"
                "🔧 **Utilidade** - Funções especiais (bonus x1.1)\n\n"
                f"**Dinossauros Disponíveis:** {len(dados.get('dinosaurs', {}))} espécies diferentes!\n\n"
                "═══════════════════════════════════════"
            ),
            color=discord.Color.gold()
        )
        
        embed.set_footer(text="Sistema de Avaliação ARK | Clique no botão para começar!")
        
        view = ValuationPanelView(bot, dados)
        msg = await canal.send(embed=embed, view=view)
        await msg.pin()
        
        # Salvar ID do painel
        salvar_painel_config({"painel_message_id": msg.id})
        print(f"[DINOSAUR] ✅ Painel criado automaticamente (ID: {msg.id})")
    except Exception as e:
        print(f"[DINOSAUR] ❌ Erro ao criar painel: {e}")
        import traceback
        traceback.print_exc()
