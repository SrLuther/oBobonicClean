"""
Sistema de Avaliação de Dinossauros para ARK
Calcula valor de venda baseado em stats e tipo/uso
Com painel interativo no Discord

Versão 2.0: Suporta múltiplos modos de cálculo
- VANILLA: Cálculo padrão ARK
- PRIMAL_FEAR: Com multiplicadores de tier
- OMEGA: Com tier, variante e paragon
"""

import discord
from discord.ext import commands
from discord import ui
import json
import os
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import asyncio

# Importar novo módulo de cálculo
from dino_calculator import (
    CalculationMode,
    DinoData,
    DinoStats,
    calculate_dino_stats,
    get_available_modes,
    get_mode_by_name,
    PRIMAL_FEAR_MULTIPLIERS,
    OMEGA_TIER_MULTIPLIERS,
    OMEGA_VARIANT_MULTIPLIERS,
    OMEGA_PARAGON_MULTIPLIERS
)

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


def arredondar_valor_comercial(valor: int, multiplo: int = 500) -> int:
    """Arredonda valor para o múltiplo mais próximo (padrão: 500)"""
    return round(valor / multiplo) * multiplo


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
    castrado: bool = False,
    calculation_mode: str = "VANILLA",
    # Parâmetros adicionais para modos especiais
    primal_tier: Optional[str] = None,
    omega_tier: Optional[str] = None,
    omega_variant: Optional[str] = None,
    omega_paragon: int = 0,
    level: int = 1
) -> Dict[str, Any]:
    """Calcula o valor de um dinossauro baseado em stats e tipo de uso
    
    Suporta múltiplos modos de cálculo:
    - VANILLA: Cálculo padrão (compatibilidade total)
    - PRIMAL_FEAR: Com multiplicadores de tier Primal Fear
    - OMEGA: Com tier, variante e paragon
    
    Args:
        especie: Nome da espécie de dinossauro
        stats: Dicionário com stats {stat_name: value}
        tipo_uso: Tipo de uso (opcional)
        dados: Dados dos dinossauros (carrega se None)
        castrado: Se o dinossauro é castrado
        calculation_mode: Modo de cálculo (VANILLA, PRIMAL_FEAR, OMEGA)
        primal_tier: Tier Primal Fear (Alpha, Apex, Fabled, Demonic, Celestial)
        omega_tier: Tier Omega (Basic, Augmented, Superior, Alpha, Omega, etc)
        omega_variant: Variante Omega (Fire, Ice, Lightning, Poison, Celestial, Chaos)
        omega_paragon: Nível de Paragon (0-5)
        level: Nível do dinossauro (afeta cálculo de stats)
    
    Returns:
        Dicionário com resultado da avaliação
    """
    if dados is None:
        dados = carregar_dados_dinos()
    
    # Validar modo de cálculo
    valid_modes = get_available_modes()
    if calculation_mode not in valid_modes:
        calculation_mode = "VANILLA"
    
    resultado = {
        "especie": especie,
        "valor_total": 0,
        "breakdown": {},
        "analise": "",
        "tier": "Comum",
        "recomendacoes": [],
        "categoria": "Outros",
        "castrado": castrado,
        "calculation_mode": calculation_mode,
        "power_score": 0,
        "calculation_details": {}
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
    
    # ============================================
    # NOVO SISTEMA: Usar calculadora modular
    # ============================================
    # Preparar dados para calculadora
    base_stats = DinoStats(
        health=stats.get("health", 0),
        damage=stats.get("damage", stats.get("melee", 0)),  # Compatibilidade com "melee"
        stamina=stats.get("stamina", 0),
        weight=stats.get("weight", 0),
        torpor=stats.get("torpor", 0),
        speed=stats.get("speed", 0),
        oxygen=stats.get("oxygen", 0),
        food=stats.get("food", 0)
    )
    
    # Criar objeto DinoData para cálculo
    dino_calc = DinoData(
        species=dino.get("name", especie),
        level=level,
        base_stats=base_stats,
        castrado=castrado,
        primal_tier=primal_tier,
        tier=omega_tier,
        variant=omega_variant,
        paragon=omega_paragon
    )
    
    # Executar cálculo no modo especificado
    mode = get_mode_by_name(calculation_mode) or CalculationMode.VANILLA
    calculation_result = calculate_dino_stats(dino_calc, mode)
    
    # Armazenar detalhes do cálculo
    resultado["power_score"] = calculation_result.power_score
    resultado["calculation_details"] = calculation_result.to_dict()
    resultado["calculation_details"]["multipliers"] = calculation_result.multipliers_applied
    
    # ============================================
    # CONTINUAR COM CÁLCULO DE VALOR (compatibilidade)
    # ============================================
    
    # Calcular valor por stat (base + stats) - MANTÉM COMPATIBILIDADE
    valor_base = base_value
    valor_stats = base_value
    resultado["breakdown"]["valor_base"] = base_value
    
    for stat_name, stat_value in stats.items():
        if stat_name in stat_multipliers:
            multiplier = stat_multipliers[stat_name]
            contribuicao = stat_value * multiplier
            valor_stats += contribuicao
            resultado["breakdown"][f"{stat_name}_value"] = int(contribuicao)
    
    # Aplicar penalidade de castração (50% desconto)
    castrado_final = castrado
    if dino.get("no_castration", False):
        # Reaper King e Mek não podem ser castrados
        castrado_final = False
    
    if castrado_final:
        valor_stats = int(valor_stats * 0.5)
        resultado["breakdown"]["desconto_castrado"] = -int(valor_base * 0.5)
    
    # Aplicar multiplicador de categoria DEPOIS dos stats
    categoria = dino.get("category", "outros").lower()
    categoria_map = {
        "apex_combat": 1.30,
        "pve_combat": 1.20,
        "criacao": 1.40,
        "transporte": 1.25,
        "farming": 1.15,
        "utilidade": 1.10,
        "outros": 1.00
    }
    
    multiplicador_categoria = categoria_map.get(categoria, 1.0)
    categoria_nome_map = {
        "apex_combat": "Apex Combat",
        "pve_combat": "PvE Combat",
        "criacao": "Criação",
        "transporte": "Transporte",
        "farming": "Farming",
        "utilidade": "Utilidade",
        "outros": "Outros"
    }
    resultado["categoria"] = categoria_nome_map.get(categoria, "Outros")
    
    # Calcular valor final COM multiplicador de categoria
    valor_final = int(valor_stats * multiplicador_categoria)
    resultado["breakdown"]["multiplo_categoria"] = int(valor_final - valor_stats)
    
    resultado["valor_total"] = valor_final
    resultado["multiplicador_categoria"] = multiplicador_categoria
    
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
    
    # Recomendações baseadas no tier
    if valor_final >= 8000:
        resultado["recomendacoes"].append("🎯 Espécime Excepcional!")
    elif valor_final >= 5000:
        resultado["recomendacoes"].append("👍 Ótimo espécime")
    
    return resultado


# ============================================
# VIEWS E MODALS
# ============================================


class CastradoSelect(ui.Select):
    """Select para escolher se dinossauro é castrado ou não"""
    
    def __init__(self, dados: dict, dino_id: str):
        self.dados = dados
        self.dino_id = dino_id
        
        opcoes = [
            discord.SelectOption(label="✅ Não Castrado", value="nao", emoji="✅"),
            discord.SelectOption(label="🔪 Castrado (-50%)", value="sim", emoji="⚠️")
        ]
        
        super().__init__(
            placeholder="É castrado?",
            min_values=1,
            max_values=1,
            options=opcoes
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback quando castrado é selecionado"""
        try:
            eh_castrado = self.values[0] == "sim"
            # Passar boolean em vez de desconto
            modal = StatsModal(self.dino_id, self.dados, castrado=eh_castrado)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"[DINOSAUR] ❌ Erro no callback do CastradoSelect: {type(e).__name__}: {e}")
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)


class CastradoSelectView(ui.View):
    """View para o select de castrado"""
    
    def __init__(self, dados: dict, dino_id: str):
        super().__init__()
        self.dados = dados
        self.dino_id = dino_id
        self.add_item(CastradoSelect(dados, dino_id))
    
    async def on_timeout(self) -> None:
        """Chamado quando o view expira"""
        pass


class SaddleSelect(ui.Select):
    """Select para escolher qual broca é usada (exclusivo Stryder)"""
    
    def __init__(self, dados: dict, dino_id: str):
        self.dados = dados
        self.dino_id = dino_id
        
        opcoes = [
            discord.SelectOption(label="🪟 Broca Normal (-25%)", value="broca", emoji="⚙️"),
            discord.SelectOption(label="🪟 Broca + Bolsa Peso (0%)", value="broca_bolsa", emoji="💼")
        ]
        
        super().__init__(
            placeholder="Qual tipo de broca?",
            min_values=1,
            max_values=1,
            options=opcoes
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback quando broca é selecionada"""
        try:
            saddle_type = self.values[0]
            # broca normal = 25% penalty, broca+bolsa = 0% penalty
            tem_broca_e_bolsa = (saddle_type == "broca_bolsa")
            
            # Para Stryder, usar modal especializado
            modal = StryderStatsModal(self.dino_id, self.dados, tem_broca_e_bolsa=tem_broca_e_bolsa)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"[DINOSAUR] ❌ Erro no callback do SaddleSelect: {type(e).__name__}: {e}")
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)


class ReaperKingSelect(ui.Select):
    """Select para abrir avaliação de Reaper King ou Mek (sem castração)"""
    
    def __init__(self, dados: dict, dino_id: str):
        self.dados = dados
        self.dino_id = dino_id
        
        opcoes = [
            discord.SelectOption(label="🦖 Iniciar Avaliação", value="start", emoji="✨")
        ]
        
        super().__init__(
            placeholder="Iniciar avaliação...",
            min_values=1,
            max_values=1,
            options=opcoes
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback para abrir modal de stats (sem castração)"""
        try:
            # Reaper King e Mek não podem ser castrados
            modal = StatsModal(self.dino_id, self.dados, castrado=False)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"[DINOSAUR] ❌ Erro no callback do ReaperKingSelect: {type(e).__name__}: {e}")
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)


class SaddleSelectView(ui.View):
    """View para o select de broca"""
    
    def __init__(self, dados: dict, dino_id: str):
        super().__init__()
        self.dados = dados
        self.dino_id = dino_id
        self.add_item(SaddleSelect(dados, dino_id))


class ReaperKingSelectView(ui.View):
    """View para abrir avaliação de Reaper King"""
    
    def __init__(self, dados: dict, dino_id: str):
        super().__init__()
        self.dados = dados
        self.dino_id = dino_id
        self.add_item(ReaperKingSelect(dados, dino_id))
    
    async def on_timeout(self) -> None:
        """Chamado quando o view expira"""
        pass


class StryderBrocaBolsaSelect(ui.Select):
    """Select para escolher configuração de broca/bolsa do Stryder"""
    
    def __init__(self, dados: dict, dino_id: str):
        self.dados = dados
        self.dino_id = dino_id
        
        opcoes = [
            discord.SelectOption(label="🪟 Apenas Broca (-25%)", value="broca_so", emoji="⚙️"),
            discord.SelectOption(label="🪟 Broca + Bolsa (0%)", value="broca_bolsa", emoji="💼")
        ]
        
        super().__init__(
            placeholder="Qual é a configuração?",
            min_values=1,
            max_values=1,
            options=opcoes
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback quando configuração é selecionada"""
        try:
            config = self.values[0]
            # broca_so = apenas broca (será -25%), broca_bolsa = com bolsa (sem desconto)
            tem_broca_e_bolsa = (config == "broca_bolsa")
            
            # Abre modal do Stryder com a configuração selecionada
            modal = StryderStatsModal(self.dino_id, self.dados, tem_broca_e_bolsa)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"[DINOSAUR] ❌ Erro no callback do StryderBrocaBolsaSelect: {type(e).__name__}: {e}")
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)


class StryderBrocaBolsaSelectView(ui.View):
    """View para o select de broca/bolsa do Stryder"""
    
    def __init__(self, dados: dict, dino_id: str):
        super().__init__()
        self.dados = dados
        self.dino_id = dino_id
        self.add_item(StryderBrocaBolsaSelect(dados, dino_id))


class StryderStatsModal(ui.Modal):
    """Modal especializado para Stryder (usa Oxigênio, Stamina, Peso, Velocidade)"""
    
    def __init__(self, dino_id: str, dados: dict, tem_broca_e_bolsa: bool = False):
        super().__init__(title="Stats do Stryder")
        self.dino_id = dino_id
        self.dados = dados
        self.tem_broca_e_bolsa = tem_broca_e_bolsa
    
    oxygen = ui.TextInput(label="Oxygen/Oxigênio", required=False, placeholder="0", min_length=0)
    stamina = ui.TextInput(label="Stamina", required=False, placeholder="0", min_length=0)
    weight = ui.TextInput(label="Weight/Peso", required=False, placeholder="0", min_length=0)
    velocity = ui.TextInput(label="Velocidade", required=False, placeholder="0", min_length=0)
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Processa o envio do modal"""
        await interaction.response.defer()
        
        # Extrair dados do modal
        stats = {}
        
        try:
            if self.oxygen.value and self.oxygen.value != "0":
                stats["oxygen"] = int(self.oxygen.value)
            if self.stamina.value and self.stamina.value != "0":
                stats["stamina"] = int(self.stamina.value)
            if self.weight.value and self.weight.value != "0":
                stats["weight"] = int(self.weight.value)
            if self.velocity.value and self.velocity.value != "0":
                stats["velocity"] = int(self.velocity.value)
        except ValueError:
            embed = discord.Embed(
                title="❌ Erro",
                description="Um ou mais valores não são números válidos!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if not stats:
            embed = discord.Embed(
                title="❌ Erro",
                description="Você precisa preencher pelo menos um stat!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Calcular valor base (sem descontos)
        resultado = calcular_valor_dino(self.dino_id, stats, None, self.dados, False)
        valor_original = resultado['valor_total']
        
        # Aplicar lógica de penalidades para Tek Stryder
        valor_final = valor_original
        status_broca = "✅ Broca + Bolsa (Sem penalidade)"
        
        # Se tem apenas broca (sem bolsa), aplica -25%
        if not self.tem_broca_e_bolsa:
            valor_final = int(valor_original * 0.75)
            status_broca = "🪟 Apenas Broca (-25%)"
        # Se tem broca + bolsa, sem desconto
        
        # Aplicar cap de 10000 Arkium máximo
        if valor_final > 10000:
            valor_final = 10000
            status_broca += " (Cap 10k)"
        
        # Calcular valor comercial sugerido
        valor_comercial = arredondar_valor_comercial(valor_final)
        
        # Enviar resultado
        embed = discord.Embed(
            title=f"💎 {resultado['especie']}",
            description=status_broca,
            color=self._get_tier_color(resultado["tier"])
        )
        
        # Mostrar valor exato e sugerido
        if valor_comercial != valor_final:
            valor_field = f"**Exato:** `{formatar_moeda(valor_final)}` Arkiums\n"
            valor_field += f"**Sugerido:** `{formatar_moeda(valor_comercial)}` Arkiums *(comercial)*\n"
            valor_field += f"{resultado['tier']} - {status_broca}"
        else:
            valor_field = f"`{formatar_moeda(valor_final)}` {resultado['tier']} - {status_broca}"
        
        embed.add_field(
            name="💰 Valor Total",
            value=valor_field,
            inline=False
        )
        
        # Breakdown dos stats
        breakdown_text = f"Base: `{formatar_moeda(resultado['breakdown'].get('valor_base', 0))}`\n"
        for stat_name in ["oxygen", "stamina", "weight", "velocity"]:
            if f"{stat_name}_value" in resultado["breakdown"]:
                valor_stat = resultado["breakdown"][f"{stat_name}_value"]
                if stats.get(stat_name, 0) > 0:
                    breakdown_text += f"{stat_name.capitalize()}: `+{formatar_moeda(valor_stat)}`\n"
        
        # Mostrar desconto/penalidade se aplicável
        if not self.tem_broca_e_bolsa:
            desconto = valor_original - valor_final
            breakdown_text += f"**Desconto (Apenas Broca): `-{formatar_moeda(desconto)}`**\n"
        
        # Mostrar cap se aplicado
        if valor_final == 10000 and valor_original > 10000:
            breakdown_text += f"**Cap Máximo: `10000 Arkiums`**\n"
        
        embed.add_field(name="📊 Breakdown", value=breakdown_text, inline=False)
        
        if resultado.get("analise_stats"):
            analise_text = "\n".join(resultado["analise_stats"])
            embed.add_field(name="📈 Análise de Stats", value=analise_text, inline=False)
        
        if resultado.get("recomendacoes"):
            embed.add_field(name="💡 Recomendações", value="\n".join(resultado["recomendacoes"]), inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @staticmethod
    def _get_tier_color(tier: str) -> discord.Color:
        """Retorna a cor baseada no tier"""
        if "Comum" in tier:
            return discord.Color.from_rgb(139, 69, 19)
        elif "Raro" in tier:
            return discord.Color.green()
        elif "Épico" in tier:
            return discord.Color.blue()
        elif "Lendário" in tier:
            return discord.Color.purple()
        else:
            return discord.Color.gold()


class StatsModal(ui.Modal):
    """Modal para inserir os stats do dinossauro"""
    
    def __init__(self, dino_id: str, dados: dict, castrado: bool = False):
        super().__init__(title="Inserir Stats do Dinossauro")
        self.dino_id = dino_id
        self.dados = dados
        self.castrado = castrado
    
    melee = ui.TextInput(label="Melee Damage", required=False, placeholder="0", min_length=0)
    health = ui.TextInput(label="Health/Saúde", required=False, placeholder="0", min_length=0)
    stamina = ui.TextInput(label="Stamina", required=False, placeholder="0", min_length=0)
    weight = ui.TextInput(label="Weight/Peso", required=False, placeholder="0", min_length=0)
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Processa o envio do modal"""
        await interaction.response.defer()
        
        # Extrair dados do modal
        stats = {}
        
        try:
            if self.melee.value and self.melee.value != "0":
                stats["melee"] = int(self.melee.value)
            if self.health.value and self.health.value != "0":
                stats["health"] = int(self.health.value)
            if self.stamina.value and self.stamina.value != "0":
                stats["stamina"] = int(self.stamina.value)
            if self.weight.value and self.weight.value != "0":
                stats["weight"] = int(self.weight.value)
        except ValueError:
            embed = discord.Embed(
                title="❌ Erro",
                description="Um ou mais valores não são números válidos!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if not stats:
            embed = discord.Embed(
                title="❌ Erro",
                description="Você precisa preencher pelo menos um stat!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Calcular valor com castração (se aplicável)
        resultado = calcular_valor_dino(self.dino_id, stats, None, self.dados, self.castrado)
        
        # Calcular valor comercial sugerido
        valor_comercial = arredondar_valor_comercial(resultado['valor_total'])
        
        # Enviar resultado
        embed = discord.Embed(
            title=f"💎 {resultado['especie']}",
            description=f"**Categoria:** {resultado.get('categoria', 'Outros')}",
            color=self._get_tier_color(resultado["tier"])
        )
        
        # Mostrar valor exato e sugerido
        if valor_comercial != resultado['valor_total']:
            valor_field = f"**Exato:** `{formatar_moeda(resultado['valor_total'])}` Arkiums\n"
            valor_field += f"**Sugerido:** `{formatar_moeda(valor_comercial)}` Arkiums *(comercial)*\n"
            valor_field += f"{resultado['tier']}"
        else:
            valor_field = f"`{formatar_moeda(resultado['valor_total'])}` {resultado['tier']}"
        
        if self.castrado:
            valor_field += " 🔪 **(Castrado -50%)**"
        
        embed.add_field(
            name="💰 Valor Total",
            value=valor_field,
            inline=False
        )
        
        breakdown_text = f"Base: `{formatar_moeda(resultado['breakdown'].get('valor_base', 0))}`\n"
        for stat_name in ["melee", "health", "stamina", "weight", "oxygen", "food"]:
            if f"{stat_name}_value" in resultado["breakdown"]:
                valor_stat = resultado["breakdown"][f"{stat_name}_value"]
                if stats.get(stat_name, 0) > 0:
                    breakdown_text += f"{stat_name.capitalize()}: `+{formatar_moeda(valor_stat)}`\n"
        
        if self.castrado and "desconto_castrado" in resultado["breakdown"]:
            desconto = resultado["breakdown"]["desconto_castrado"]
            breakdown_text += f"**Desconto Castrado: `-{formatar_moeda(abs(desconto))}`**\n"
        
        if "multiplo_categoria" in resultado["breakdown"]:
            breakdown_text += f"**Multiplicador ({resultado.get('categoria', 'Outros')} x{resultado.get('multiplicador_categoria', 1.0):.2f}):** `+{formatar_moeda(resultado['breakdown']['multiplo_categoria'])}`\n"
        
        embed.add_field(name="📊 Breakdown", value=breakdown_text, inline=False)
        
        if resultado.get("analise_stats"):
            analise_text = "\n".join(resultado["analise_stats"])
            embed.add_field(name="📈 Análise de Stats", value=analise_text, inline=False)
        
        if resultado.get("recomendacoes"):
            embed.add_field(name="💡 Recomendações", value="\n".join(resultado["recomendacoes"]), inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
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
        
        # Filtrar dinossauros que correspondem ao search (exato ou parcial)
        resultados = {}
        
        # 1. Busca exata por chave
        if search_text in dinos:
            resultados[search_text] = dinos[search_text]
        
        # 2. Busca por substring na chave ou nome
        for key, dino in dinos.items():
            nome = dino.get("name", "").lower()
            if search_text in key or search_text in nome:
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
        
        # Se encontrou apenas 1, vai para seleção de castrado ou broca
        if len(resultados) == 1:
            dino_id = list(resultados.keys())[0]
            dino_data = resultados[dino_id]
            
            # Se é Stryder (asexuado com broca), pergunta qual tipo de broca
            if dino_data.get("asexual", False) and dino_data.get("has_broca", False):
                print(f"[DINOSAUR] {dino_id} é Stryder, mostrando StryderBrocaBolsaSelectView...")
                select_view = StryderBrocaBolsaSelectView(self.dados, dino_id)
                
                embed = discord.Embed(
                    title="🦖 Stryder Selecionado",
                    description=f"**{resultados[dino_id].get('name')}**\n\n"
                               f"Selecione se tem Broca e Bolsa",
                    color=discord.Color.blue()
                )
            # Se é Reaper King ou Mek (não podem ser castrados)
            elif dino_id in ["reaper_king", "mek"] or dino_data.get("no_castration", False):
                print(f"[DINOSAUR] {dino_id} não pode ser castrado, mostrando ReaperKingSelectView...")
                select_view = ReaperKingSelectView(self.dados, dino_id)
                
                embed = discord.Embed(
                    title="🦖 Criatura Selecionada",
                    description=f"**{resultados[dino_id].get('name')}**\n\n"
                               f"Esta criatura não pode ser castrada",
                    color=discord.Color.blue()
                )
            else:
                # Para outros dinossauros, pergunta se é castrado
                print(f"[DINOSAUR] {dino_id} é outro dino, mostrando CastradoSelectView...")
                select_view = CastradoSelectView(self.dados, dino_id)
                
                embed = discord.Embed(
                    title="🦖 Dinossauro Selecionado",
                    description=f"**{resultados[dino_id].get('name')}**\n\n"
                               f"É castrado?",
                    color=discord.Color.blue()
                )
            
            await interaction.followup.send(embed=embed, view=select_view, ephemeral=True)
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
        try:
            print(f"[DINOSAUR] DinoSearchSelect callback acionado! Valores: {self.values}")
            dino_id = self.values[0]
            print(f"[DINOSAUR] Dino ID selecionado: {dino_id}")
            
            # Verificar se dino existe
            dinos = self.dados.get("dinosaurs", {})
            if dino_id not in dinos:
                print(f"[DINOSAUR] ❌ Dinossauro {dino_id} não encontrado!")
                await interaction.response.send_message(
                    f"❌ Dinossauro não encontrado: {dino_id}",
                    ephemeral=True
                )
                return
            
            dino_data = dinos[dino_id]
            
            # Se é Stryder (asexuado com broca), pergunta qual tipo de broca
            if dino_data.get("asexual", False) and dino_data.get("has_broca", False):
                print(f"[DINOSAUR] {dino_id} é Stryder, mostrando StryderBrocaBolsaSelectView...")
                select_view = StryderBrocaBolsaSelectView(self.dados, dino_id)
                
                embed = discord.Embed(
                    title="🦖 Qual tipo de broca?",
                    description=f"O dinossauro **{self.dados.get('dinosaurs', {}).get(dino_id, {}).get('name', dino_id)}** tem qual broca?",
                    color=discord.Color.blue()
                )
            # Se é Reaper King ou Mek (não podem ser castrados)
            elif dino_id in ["reaper_king", "mek"] or dino_data.get("no_castration", False):
                print(f"[DINOSAUR] {dino_id} não pode ser castrado, mostrando ReaperKingSelectView...")
                select_view = ReaperKingSelectView(self.dados, dino_id)
                
                embed = discord.Embed(
                    title="🦖 Criatura Selecionada",
                    description=f"O dinossauro **{self.dados.get('dinosaurs', {}).get(dino_id, {}).get('name', dino_id)}** não pode ser castrado",
                    color=discord.Color.blue()
                )
            else:
                # Para outros dinossauros, pergunta se é castrado
                print(f"[DINOSAUR] {dino_id} é outro dino, mostrando CastradoSelectView...")
                select_view = CastradoSelectView(self.dados, dino_id)
                
                embed = discord.Embed(
                    title="🦖 É castrado?",
                    description=f"O dinossauro **{self.dados.get('dinosaurs', {}).get(dino_id, {}).get('name', dino_id)}** é castrado?",
                    color=discord.Color.blue()
                )
            
            await interaction.response.send_message(embed=embed, view=select_view, ephemeral=True)
            print(f"[DINOSAUR] ✅ View enviada com sucesso!")
        except Exception as e:
            print(f"[DINOSAUR] ❌ Erro no callback do DinoSearchSelect: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.response.send_message(
                    f"❌ Erro ao abrir o modal: {str(e)}",
                    ephemeral=True
                )
            except:
                pass


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
        try:
            print(f"[DINOSAUR] DinoSelect callback acionado! Valores: {self.values}")
            dino_id = self.values[0]
            print(f"[DINOSAUR] Dino ID selecionado: {dino_id}")
            
            # Verificar se dino existe
            dinos = self.dados.get("dinosaurs", {})
            if dino_id not in dinos:
                print(f"[DINOSAUR] ❌ Dinossauro {dino_id} não encontrado!")
                await interaction.response.send_message(
                    f"❌ Dinossauro não encontrado: {dino_id}",
                    ephemeral=True
                )
                return
            
            dino_data = dinos[dino_id]
            
            # Se é Stryder (asexuado com broca), pergunta qual tipo de broca
            if dino_data.get("asexual", False) and dino_data.get("has_broca", False):
                print(f"[DINOSAUR] {dino_id} é Stryder, mostrando StryderBrocaBolsaSelectView...")
                select_view = StryderBrocaBolsaSelectView(self.dados, dino_id)
                
                embed = discord.Embed(
                    title="🦖 Qual tipo de broca?",
                    description=f"O dinossauro **{self.dados.get('dinosaurs', {}).get(dino_id, {}).get('name', dino_id)}** tem qual broca?",
                    color=discord.Color.blue()
                )
            # Se é Reaper King ou Mek (não podem ser castrados)
            elif dino_id in ["reaper_king", "mek"] or dino_data.get("no_castration", False):
                print(f"[DINOSAUR] {dino_id} não pode ser castrado, mostrando ReaperKingSelectView...")
                select_view = ReaperKingSelectView(self.dados, dino_id)
                
                embed = discord.Embed(
                    title="🦖 Criatura Selecionada",
                    description=f"O dinossauro **{self.dados.get('dinosaurs', {}).get(dino_id, {}).get('name', dino_id)}** não pode ser castrado",
                    color=discord.Color.blue()
                )
            else:
                # Para outros dinossauros, pergunta se é castrado
                print(f"[DINOSAUR] {dino_id} é outro dino, mostrando CastradoSelectView...")
                select_view = CastradoSelectView(self.dados, dino_id)
                
                embed = discord.Embed(
                    title="🦖 É castrado?",
                    description=f"O dinossauro **{self.dados.get('dinosaurs', {}).get(dino_id, {}).get('name', dino_id)}** é castrado?",
                    color=discord.Color.blue()
                )
            
            await interaction.response.send_message(embed=embed, view=select_view, ephemeral=True)
            print(f"[DINOSAUR] ✅ View enviada com sucesso!")
        except Exception as e:
            print(f"[DINOSAUR] ❌ Erro no callback do DinoSelect: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.response.send_message(
                    f"❌ Erro ao abrir o modal: {str(e)}",
                    ephemeral=True
                )
            except:
                pass


class DinoSelectView(ui.View):
    """View para o select de dinossauros"""
    
    def __init__(self, dados: dict):
        super().__init__()
        self.dados = dados
        self.add_item(DinoSelect(dados))
    
    async def on_timeout(self) -> None:
        """Chamado quando o view expira"""
        pass


class AdicionarDinoModal(ui.Modal):
    """Modal para adicionar um novo dinossauro sugerido"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(title="Adicionar Dinossauro Sugerido")
        self.bot = bot
    
    nome_dino = ui.TextInput(
        label="Nome do Dinossauro",
        placeholder="Ex: Ultraxenovenator",
        required=True,
        min_length=1,
        max_length=100
    )
    
    valor_full = ui.TextInput(
        label="Valor para Dino Full (254 stats)",
        placeholder="Ex: 15000",
        required=True,
        min_length=1,
        max_length=10
    )
    
    observacoes = ui.TextInput(
        label="Observações",
        placeholder="Ex: Tem mutações, coloração única, etc...",
        required=True,
        min_length=1,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    nome_mod = ui.TextInput(
        label="Nome do Mod (deixe em branco se for vanilla)",
        placeholder="Ex: Ark Additions, Primal Fear, Genesis",
        required=False,
        min_length=0,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Processa o envio do modal"""
        await interaction.response.defer()
        
        try:
            # Validar valor
            try:
                valor = int(self.valor_full.value)
                if valor <= 0:
                    raise ValueError("Valor deve ser maior que 0")
            except ValueError:
                embed = discord.Embed(
                    title="❌ Erro",
                    description="O valor deve ser um número válido e maior que 0!",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar se é de mod
            nome_mod_final = self.nome_mod.value.strip()
            é_de_mod = bool(nome_mod_final)
            
            # Enviar sugestão
            await enviar_sugestao_dino(
                interaction,
                self.nome_dino.value,
                valor,
                self.observacoes.value,
                interaction.user,
                self.bot,
                é_de_mod=é_de_mod,
                nome_mod=nome_mod_final
            )
        
        except Exception as e:
            print(f"[DINOSAUR] ❌ Erro ao processar sugestão: {e}")
            import traceback
            traceback.print_exc()
            
            embed = discord.Embed(
                title="❌ Erro ao enviar sugestão",
                description=f"Ocorreu um erro: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


class AdicionarDinoModalSemMod(ui.Modal):
    """Modal para adicionar um novo dinossauro sugerido"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(title="Adicionar Dinossauro Sugerido")
        self.bot = bot
    
    nome_dino = ui.TextInput(
        label="Nome do Dinossauro",
        placeholder="Ex: Ultraxenovenator",
        required=True,
        min_length=1,
        max_length=100
    )
    
    valor_full = ui.TextInput(
        label="Valor para Dino Full (254 stats)",
        placeholder="Ex: 15000",
        required=True,
        min_length=1,
        max_length=10
    )
    
    observacoes = ui.TextInput(
        label="Observações",
        placeholder="Ex: Tem mutações, coloração única, etc...",
        required=True,
        min_length=1,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Processa o envio do modal para dinossauro vanilla"""
        await interaction.response.defer()
        
        try:
            # Validar valor
            try:
                valor = int(self.valor_full.value)
                if valor <= 0:
                    raise ValueError("Valor deve ser maior que 0")
            except ValueError:
                embed = discord.Embed(
                    title="❌ Erro",
                    description="O valor deve ser um número válido e maior que 0!",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Enviar sugestão sem mod
            await enviar_sugestao_dino(
                interaction,
                self.nome_dino.value,
                valor,
                self.observacoes.value,
                interaction.user,
                self.bot,
                é_de_mod=False,
                nome_mod=""
            )
        
        except Exception as e:
            print(f"[DINOSAUR] ❌ Erro ao processar sugestão: {e}")
            import traceback
            traceback.print_exc()
            
            embed = discord.Embed(
                title="❌ Erro ao enviar sugestão",
                description=f"Ocorreu um erro: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


class AdicionarDinoModalComMod(ui.Modal):
    """Modal para adicionar dinossauro COM mod (4 campos)"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(title="Adicionar Dinossauro Sugerido")
        self.bot = bot
    
    nome_dino = ui.TextInput(
        label="Nome do Dinossauro",
        placeholder="Ex: Ultraxenovenator",
        required=True,
        min_length=1,
        max_length=100
    )
    
    valor_full = ui.TextInput(
        label="Valor para Dino Full (254 stats)",
        placeholder="Ex: 15000",
        required=True,
        min_length=1,
        max_length=10
    )
    
    observacoes = ui.TextInput(
        label="Observações",
        placeholder="Ex: Tem mutações, coloração única, etc...",
        required=True,
        min_length=1,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    nome_mod = ui.TextInput(
        label="Nome do Mod",
        placeholder="Ex: Ark Additions, Primal Fear, Genesis",
        required=True,
        min_length=1,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Processa o envio do modal para dinossauro com mod"""
        await interaction.response.defer()
        
        try:
            # Validar valor
            try:
                valor = int(self.valor_full.value)
                if valor <= 0:
                    raise ValueError("Valor deve ser maior que 0")
            except ValueError:
                embed = discord.Embed(
                    title="❌ Erro",
                    description="O valor deve ser um número válido e maior que 0!",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Enviar sugestão com mod
            await enviar_sugestao_dino(
                interaction,
                self.nome_dino.value,
                valor,
                self.observacoes.value,
                interaction.user,
                self.bot,
                é_de_mod=True,
                nome_mod=self.nome_mod.value
            )
        
        except Exception as e:
            print(f"[DINOSAUR] ❌ Erro ao processar sugestão: {e}")
            import traceback
            traceback.print_exc()
            
            embed = discord.Embed(
                title="❌ Erro ao enviar sugestão",
                description=f"Ocorreu um erro: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


class ModSelect(ui.Select):
    """Select para escolher se é de mod ou não"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        opcoes = [
            discord.SelectOption(label="Sim", value="sim", emoji="✅", description="É de um mod"),
            discord.SelectOption(label="Não", value="nao", emoji="❌", description="É vanilla")
        ]
        
        super().__init__(
            placeholder="Escolha uma opção...",
            min_values=1,
            max_values=1,
            options=opcoes
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback quando a opção é selecionada"""
        try:
            opcao = self.values[0]
            
            if opcao == "sim":
                # Mostrar modal COM campo de mod
                modal = AdicionarDinoModalComMod(self.bot)
                await interaction.response.send_modal(modal)
            else:
                # Mostrar modal SEM campo de mod
                modal = AdicionarDinoModalSemMod(self.bot)
                await interaction.response.send_modal(modal)
        
        except Exception as e:
            print(f"[DINOSAUR] ❌ Erro no ModSelect: {e}")
            import traceback
            traceback.print_exc()
            
            embed = discord.Embed(
                title="❌ Erro",
                description=f"Ocorreu um erro: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class ModSelectView(ui.View):
    """View para o select de mod"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.add_item(ModSelect(bot))


async def enviar_sugestao_dino(
    interaction: discord.Interaction,
    nome_dino: str,
    valor_full: int,
    observacoes: str,
    usuario: discord.User,
    bot: commands.Bot,
    é_de_mod: bool,
    nome_mod: str = ""
) -> None:
    """Função auxiliar para enviar a sugestão de dinossauro"""
    
    agora = datetime.now()
    data_formatada = agora.strftime("%d/%m/%Y às %H:%M:%S")
    
    # Enviar para o canal designado
    canal_id = 1475129137201942560
    canal = bot.get_channel(canal_id)
    
    if not canal:
        embed = discord.Embed(
            title="❌ Erro",
            description=f"Canal de sugestões não encontrado!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Criar embed para enviar ao canal
    embed = discord.Embed(
        title=f"🦖 Nova Sugestão de Dinossauro",
        description=f"Sugestão preparada para análise",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="👤 Usuário", value=f"{usuario.mention} ({usuario.name})", inline=False)
    embed.add_field(name="📅 Data e Hora", value=data_formatada, inline=False)
    embed.add_field(name="🦖 Nome do Dinossauro", value=f"```{nome_dino}```", inline=False)
    embed.add_field(name="💰 Valor Full (254 stats)", value=f"```{valor_full} Arkiums```", inline=False)
    embed.add_field(name="📝 Observações", value=f"```{observacoes}```", inline=False)
    
    if é_de_mod:
        embed.add_field(name="📦 Mod", value=f"```✅ {nome_mod}```", inline=False)
    else:
        embed.add_field(name="📦 Mod", value="```❌ Vanilla```", inline=False)
    
    embed.set_footer(text=f"ID do Usuário: {usuario.id}")
    
    # Enviar ao canal
    mensagem = await canal.send(embed=embed)
    await mensagem.add_reaction("✅")
    await mensagem.add_reaction("❌")
    
    # Confirmar para o usuário
    confirm_embed = discord.Embed(
        title="✅ Sugestão Enviada!",
        description=f"Sua sugestão foi enviada com sucesso para análise!\n\n"
                   f"**Dinossauro:** {nome_dino}\n"
                   f"**Valor Sugerido:** {valor_full} Arkiums",
        color=discord.Color.green()
    )
    
    await interaction.followup.send(embed=confirm_embed, ephemeral=True)


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
    
    @ui.button(label="➕ Adicionar Dino", style=discord.ButtonStyle.success, custom_id="adicionar_dino_btn")
    async def adicionar_button(self, interaction: discord.Interaction, button: ui.Button):
        """Abre o modal para adicionar um novo dinossauro sugerido"""
        modal = AdicionarDinoModal(self.bot)
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
    
    @commands.command(name="ajudacalc")
    async def ajuda_calculadora(self, ctx: commands.Context):
        """Exibe guia completo sobre como os cálculos de valor funcionam"""
        
        # PÁGINA 1: INTRODUÇÃO E FÓRMULA PRINCIPAL
        embed1 = discord.Embed(
            title="📖 Guia Completo da Calculadora de Arkiums",
            description="**Página 1 de 6** - Fundamentos",
            color=discord.Color.gold()
        )
        
        embed1.add_field(
            name="🧮 Fórmula Principal",
            value="```\nVALOR FINAL = (Base + Stats) × Multiplicador da Categoria\n```",
            inline=False
        )
        
        embed1.add_field(
            name="📊 Como Funciona",
            value=(
                "**Passo 1:** Cada dinossauro começa com um **Base Value** (valor base fixo)\n"
                "**Passo 2:** Adicionamos a contribuição de cada **Stat** (Melee, Health, etc)\n"
                "**Passo 3:** Se castrado, aplicamos penalidade de **-50%**\n"
                "**Passo 4:** Multiplicamos pelo **Multiplicador da Categoria**\n"
                "**Passo 5:** Classificamos em um **Tier** baseado no resultado"
            ),
            inline=False
        )
        
        embed1.set_footer(text="Use !ajudacalc para ver todas as páginas")
        await ctx.send(embed=embed1, ephemeral=True)
        
        # PÁGINA 2: PASSO A PASSO DETALHADO
        embed2 = discord.Embed(
            title="📖 Guia Completo da Calculadora de Arkiums",
            description="**Página 2 de 6** - Passo a Passo",
            color=discord.Color.gold()
        )
        
        embed2.add_field(
            name="📐 Exemplo Prático: T-Rex",
            value=(
                "**Base Value:** 3.500\n"
                "**MELEE:** 250 × 1.50 = 375\n"
                "**HEALTH:** 10.000 × 1.10 = 11.000\n"
                "**STAMINA:** 500 × 0.30 = 150\n"
                "─────────────────────────\n"
                "**Base + Stats = 3.500 + 11.525 = 15.025**"
            ),
            inline=False
        )
        
        embed2.add_field(
            name="🔪 Passo 3: Castração",
            value=(
                "Se **NÃO** castrado → sem penalidade\n"
                "Se **SIM** castrado → × 0.50 (perde 50%)\n\n"
                "❌ **EXCEÇÕES:**\n"
                "• Reaper King (nunca castrado)\n"
                "• Mek (nunca castrado)"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed2, ephemeral=True)
        
        # PÁGINA 3: CATEGORIAS (PARTE 1)
        embed3 = discord.Embed(
            title="👑 As 7 Categorias e Seus Multiplicadores",
            description="**Página 3 de 6** - Categorias Elite & Reprodução",
            color=discord.Color.gold()
        )
        
        embed3.add_field(
            name="👑 Apex Combat • x1.30",
            value=(
                "**Elite máxima de combate**\n"
                "• Carcharadontosaurus\n"
                "• Giganotosaurus\n"
                "• Reaper King\n"
                "• Rock Elemental\n"
                "• Wyverns (todas)\n"
                "• Voidwyrm\n"
                "• Shadowmane\n"
                "• Mek\n\n"
                "💡 Criaturas mais perigosas e valiosas para PvP"
            ),
            inline=False
        )
        
        embed3.add_field(
            name="🥚 Criação • x1.40 ⭐ MAIS VALIOSA",
            value=(
                "**Reprodução e mutação**\n"
                "• Maewing (melhor reprodutor!)\n"
                "• Procoptodon\n"
                "• Oviraptor\n"
                "• Daeodon\n"
                "• Phiomia\n"
                "• Paraceratherium\n"
                "• Diplodocus\n"
                "• Carbonemys\n"
                "• Megachelon\n\n"
                "💡 Criam mutações = valor econômico MÁXIMO!"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed3, ephemeral=True)
        
        # PÁGINA 4: CATEGORIAS (PARTE 2)
        embed4 = discord.Embed(
            title="👑 As 7 Categorias - Continuação",
            description="**Página 4 de 6** - Transporte & Combate PvE",
            color=discord.Color.gold()
        )
        
        embed4.add_field(
            name="🚚 Transporte • x1.25",
            value=(
                "**Mobilidade e logística**\n"
                "• Argentavis\n"
                "• Quetzal\n"
                "• Tapejara\n"
                "• Pteranodon\n"
                "• Griffin\n"
                "• Snow Owl\n"
                "• Astrocetus\n"
                "• E mais...\n\n"
                "💡 Indispensáveis para movimento de bases"
            ),
            inline=False
        )
        
        embed4.add_field(
            name="🐉 PvE Combat • x1.20",
            value=(
                "**Combate geral e progressão**\n"
                "• T-Rex\n"
                "• Spinosaurus\n"
                "• Therizinosaur\n"
                "• Allosaurus\n"
                "• Direwolf\n"
                "• Velonasaur\n"
                "• Managarmr\n"
                "• And 9+ more\n\n"
                "💡 Essenciais para derrotar bosses"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed4, ephemeral=True)
        
        # PÁGINA 5: CATEGORIAS (PARTE 3) & TIERS
        embed5 = discord.Embed(
            title="👑 As 7 Categorias - Finalização & Tiers",
            description="**Página 5 de 6** - Farming, Utilidade & Classificação",
            color=discord.Color.gold()
        )
        
        embed5.add_field(
            name="⛏️ Farming • x1.15",
            value=(
                "**Coleta de recursos**\n"
                "Ankylosaurus, Doedicurus, Castoroides,\n"
                "Mammoth, Magmasaur, Roll Rat, e mais\n\n"
                "💡 Aumentam velocidade de recursos"
            ),
            inline=False
        )
        
        embed5.add_field(
            name="🔧 Utilidade • x1.10",
            value=(
                "**Funções especiais**\n"
                "Beelzebufo, Troodon, Ichthyornis,\n"
                "Otter, Shinehorn, Compy, Vulture, etc\n\n"
                "💡 Úteis mas não econômicos"
            ),
            inline=False
        )
        
        embed5.add_field(
            name="🦕 Outros • x1.00",
            value=(
                "**Sem função principal**\n"
                "Dodos, Dilophosaurus, e não categorizados\n\n"
                "💡 Sem valor econômico significativo"
            ),
            inline=False
        )
        
        embed5.add_field(
            name="🎯 Tiers de Classificação",
            value=(
                "🟤 **Comum** - Valor < 500\n"
                "🟢 **Raro** - Valor 500-1.999\n"
                "🔵 **Épico** - Valor 2.000-4.999\n"
                "🟣 **Lendário** - Valor 5.000-7.999\n"
                "🟡 **Mítico** - Valor 8.000+"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed5, ephemeral=True)
        
        # PÁGINA 6: EXEMPLO PRÁTICO E DICAS
        embed6 = discord.Embed(
            title="📖 Guia Completo - Encerramento",
            description="**Página 6 de 6** - Exemplo Completo & Dicas",
            color=discord.Color.gold()
        )
        
        embed6.add_field(
            name="📈 Exemplo Prático: Maewing Criação (x1.40)",
            value=(
                "**Base:** 4.000\n"
                "**MELEE:** 200 × 1.50 = 300\n"
                "**HEALTH:** 8.000 × 1.10 = 8.800\n"
                "**Subtotal:** 4.000 + 9.100 = 13.100\n"
                "**Castrado?** Não (sem penalidade)\n"
                "**Multiplicador (x1.40):** 13.100 × 1.40\n"
                "═════════════════════════════\n"
                "**VALOR FINAL = 18.340 Arkiums** 🟡 Mítico"
            ),
            inline=False
        )
        
        embed6.add_field(
            name="💡 Dicas Importantes",
            value=(
                "✅ **Criação** é a categoria mais lucrativa (x1.40)\n"
                "✅ **Stats altos** impactam muito (cada 100 Melee = +150)\n"
                "⚠️ **Castração custa 50%** - pense bem antes\n"
                "⚠️ **Reaper King/Mek** nunca são castrados\n"
                "⚠️ **Multiplicadores** são aplicados ao final\n"
                "⚠️ **Tek Stryder** usa sistema exclusivo (broca/bolsa)"
            ),
            inline=False
        )
        
        embed6.set_footer(text="Sistema de Avaliação ARK | Escrito por SrLuther")
        await ctx.send(embed=embed6, ephemeral=True)
    
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
                
                # SEMPRE deletar o painel anterior se existir
                if painel_msg_id:
                    try:
                        msg = await canal.fetch_message(painel_msg_id)
                        await msg.delete()
                        print(f"[DINOSAUR] 🗑️ Painel anterior deletado (ID: {painel_msg_id})")
                    except discord.NotFound:
                        print("[DINOSAUR] Painel anterior não encontrado no Discord")
                    except Exception as e:
                        print(f"[DINOSAUR] ⚠️ Erro ao deletar painel anterior: {e}")
                
                # Criar novo painel
                print("[DINOSAUR] 🆕 Criando novo painel...")
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
                "**📖 Como usar:**\n"
                "1. Clique no botão abaixo\n"
                "2. Selecione o tipo de dinossauro\n"
                "3. Preencha os stats (Melee, Health, Stamina, etc)\n"
                "4. Receba a avaliação detalhada\n\n"
                "**📚 Quer aprender como os cálculos funcionam?**\n"
                "Use o comando `!ajudacalc` para ver o guia completo com:\n"
                "• Fórmula principal e fundamentos\n"
                "• Passo a passo detalhado\n"
                "• Todas as 7 categorias explicadas\n"
                "• Exemplos práticos\n"
                "• Dicas importantes\n\n"
                "**👑 Nossas Categorias:**\n"
                "👑 **Apex Combat** (x1.30) - Elite de combate\n"
                "🥚 **Criação** (x1.40) - Reprodução (MAIS VALIOSA!)\n"
                "🚚 **Transporte** (x1.25) - Mobilidade\n"
                "🐉 **PvE Combat** (x1.20) - Bosses\n"
                "⛏️ **Farming** (x1.15) - Recursos\n"
                "🔧 **Utilidade** (x1.10) - Especial\n"
                "🦕 **Outros** (x1.00) - Sem função\n\n"
                f"**🦖 Dinossauros:** {len(dados.get('dinosaurs', {}))} espécies!\n\n"
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
