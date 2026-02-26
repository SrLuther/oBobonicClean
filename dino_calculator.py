"""
Sistema modular de cálculo para dinossauros em ARK
Suporta múltiplos modos: VANILLA, PRIMAL_FEAR, OMEGA
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class CalculationMode(Enum):
    """Modos de cálculo disponíveis"""
    VANILLA = "VANILLA"
    PRIMAL_FEAR = "PRIMAL_FEAR"
    OMEGA = "OMEGA"


# ============================================
# MULTIPLICADORES PRIMAL FEAR
# ============================================
PRIMAL_FEAR_MULTIPLIERS = {
    "Alpha": 10,
    "Apex": 50,
    "Fabled": 80,
    "Demonic": 150,
    "Celestial": 500
}

# ============================================
# MULTIPLICADORES OMEGA
# ============================================
OMEGA_TIER_MULTIPLIERS = {
    "Basic": 1,
    "Augmented": 1.8,
    "Superior": 3.5,
    "Alpha": 7,
    "Omega": 15,
    "Mythical": 30,
    "Legendary": 60,
    "Godlike": 120,
    "Celestial": 240,
    "Chaos": 480,
    "Eternal": 960
}

OMEGA_VARIANT_MULTIPLIERS = {
    "Fire": 1.2,
    "Ice": 1.2,
    "Lightning": 1.3,
    "Poison": 1.2,
    "Celestial": 1.5,
    "Chaos": 1.5
}

OMEGA_PARAGON_MULTIPLIERS = {
    0: 1,
    1: 2,
    2: 4,
    3: 8,
    4: 16,
    5: 32
}


@dataclass
class DinoStats:
    """Estrutura para armazenar stats do dinossauro"""
    health: float = 0
    damage: float = 0
    stamina: float = 0
    weight: float = 0
    torpor: float = 0
    speed: float = 0
    oxygen: float = 0
    food: float = 0
    
    def to_dict(self) -> Dict[str, float]:
        """Converte para dicionário"""
        return {
            "health": self.health,
            "damage": self.damage,
            "stamina": self.stamina,
            "weight": self.weight,
            "torpor": self.torpor,
            "speed": self.speed,
            "oxygen": self.oxygen,
            "food": self.food
        }


@dataclass
class DinoData:
    """Estrutura para dados do dinossauro"""
    species: str
    level: float = 1
    base_stats: Optional[DinoStats] = None
    calculation_mode: CalculationMode = CalculationMode.VANILLA
    
    # Propriedades VANILLA
    castrado: bool = False
    
    # Propriedades PRIMAL_FEAR
    primal_tier: Optional[str] = None  # Alpha, Apex, Fabled, Demonic, Celestial
    
    # Propriedades OMEGA
    tier: Optional[str] = None  # Basic, Augmented, Superior, Alpha, Omega, etc
    variant: Optional[str] = None  # Fire, Ice, Lightning, Poison, Celestial, Chaos
    paragon: int = 0  # 0-5
    
    def __post_init__(self):
        if self.base_stats is None:
            self.base_stats = DinoStats()


@dataclass
class CalculationResult:
    """Resultado do cálculo de stats"""
    stats: DinoStats
    power_score: float
    mode: CalculationMode
    multipliers_applied: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte resultado para dicionário"""
        return {
            "stats": self.stats.to_dict(),
            "power_score": self.power_score,
            "mode": self.mode.value,
            "multipliers": self.multipliers_applied
        }


# ============================================
# CALCULADORA VANILLA (PADRÃO ARK)
# ============================================
def calculate_vanilla_stats(dino: DinoData) -> CalculationResult:
    """
    Calcula stats usando a fórmula vanilla padrão do ARK.
    
    Fórmula:
    - health = baseHealth * (1 + level * 0.054)
    - damage = baseDamage * (1 + level * 0.02)
    - stamina = baseStamina * (1 + level * 0.04)
    - weight = baseWeight * (1 + level * 0.01)
    - torpor = baseTorpor * (1 + level * 0.06)
    """
    level_factor = dino.level - 1  # Nível 1 = sem bonus
    
    stats = DinoStats(
        health=dino.base_stats.health * (1 + level_factor * 0.054),
        damage=dino.base_stats.damage * (1 + level_factor * 0.02),
        stamina=dino.base_stats.stamina * (1 + level_factor * 0.04),
        weight=dino.base_stats.weight * (1 + level_factor * 0.01),
        torpor=dino.base_stats.torpor * (1 + level_factor * 0.06),
        speed=dino.base_stats.speed,
        oxygen=dino.base_stats.oxygen,
        food=dino.base_stats.food
    )
    
    # Aplicar penalidade de castração (50%)
    if dino.castrado:
        stats.health *= 0.5
        stats.damage *= 0.5
    
    multipliers = {
        "level_factor": level_factor,
        "castrado": 0.5 if dino.castrado else 1.0
    }
    
    # Power score: nível do dinossauro
    power_score = float(dino.level)
    
    return CalculationResult(
        stats=stats,
        power_score=power_score,
        mode=CalculationMode.VANILLA,
        multipliers_applied=multipliers
    )


# ============================================
# CALCULADORA PRIMAL FEAR
# ============================================
def calculate_primal_fear_stats(dino: DinoData) -> CalculationResult:
    """
    Calcula stats usando multiplicadores Primal Fear.
    
    Cada tier (Alpha, Apex, Fabled, Demonic, Celestial) tem multiplicador próprio.
    """
    if not dino.primal_tier:
        # Se não tiver tier especificado, usar como vanilla
        return calculate_vanilla_stats(dino)
    
    multiplier = PRIMAL_FEAR_MULTIPLIERS.get(dino.primal_tier, 1)
    level_factor = dino.level - 1
    
    stats = DinoStats(
        health=dino.base_stats.health * multiplier * (1 + level_factor * 0.08),
        damage=dino.base_stats.damage * multiplier * (1 + level_factor * 0.04),
        stamina=dino.base_stats.stamina * multiplier,
        weight=dino.base_stats.weight * multiplier,
        torpor=dino.base_stats.torpor * multiplier * (1 + level_factor * 0.1),
        speed=dino.base_stats.speed,
        oxygen=dino.base_stats.oxygen,
        food=dino.base_stats.food
    )
    
    # Aplicar penalidade de castração
    if dino.castrado:
        stats.health *= 0.5
        stats.damage *= 0.5
    
    multipliers = {
        "primal_tier": dino.primal_tier,
        "tier_multiplier": multiplier,
        "level_factor": level_factor,
        "castrado": 0.5 if dino.castrado else 1.0
    }
    
    # Power score: nível * multiplicador do tier
    power_score = float(dino.level * multiplier)
    
    return CalculationResult(
        stats=stats,
        power_score=power_score,
        mode=CalculationMode.PRIMAL_FEAR,
        multipliers_applied=multipliers
    )


# ============================================
# CALCULADORA OMEGA
# ============================================
def calculate_omega_stats(dino: DinoData) -> CalculationResult:
    """
    Calcula stats usando sistema Omega completo.
    
    Combina: Tier * Variant * Paragon
    """
    if not dino.tier:
        # Se não tiver tier especificado, usar como vanilla
        return calculate_vanilla_stats(dino)
    
    tier_mult = OMEGA_TIER_MULTIPLIERS.get(dino.tier, 1)
    variant_mult = OMEGA_VARIANT_MULTIPLIERS.get(dino.variant, 1) if dino.variant else 1
    paragon_mult = OMEGA_PARAGON_MULTIPLIERS.get(dino.paragon, 1)
    
    level_factor = dino.level - 1
    
    stats = DinoStats(
        health=(
            dino.base_stats.health
            * tier_mult
            * variant_mult
            * paragon_mult
            * (1 + level_factor * 0.08)
        ),
        damage=(
            dino.base_stats.damage
            * tier_mult
            * variant_mult
            * paragon_mult
            * (1 + level_factor * 0.04)
        ),
        stamina=dino.base_stats.stamina * tier_mult,
        weight=dino.base_stats.weight * tier_mult,
        torpor=dino.base_stats.torpor * tier_mult * paragon_mult,
        speed=dino.base_stats.speed,
        oxygen=dino.base_stats.oxygen,
        food=dino.base_stats.food
    )
    
    # Aplicar penalidade de castração
    if dino.castrado:
        stats.health *= 0.5
        stats.damage *= 0.5
    
    multipliers = {
        "tier": dino.tier,
        "tier_multiplier": tier_mult,
        "variant": dino.variant,
        "variant_multiplier": variant_mult,
        "paragon": dino.paragon,
        "paragon_multiplier": paragon_mult,
        "level_factor": level_factor,
        "castrado": 0.5 if dino.castrado else 1.0
    }
    
    # Power score: nível * tier * paragon
    power_score = float(dino.level * tier_mult * paragon_mult)
    
    return CalculationResult(
        stats=stats,
        power_score=power_score,
        mode=CalculationMode.OMEGA,
        multipliers_applied=multipliers
    )


# ============================================
# FUNÇÃO PRINCIPAL DE CÁLCULO
# ============================================
def calculate_dino_stats(
    dino: DinoData,
    mode: CalculationMode = CalculationMode.VANILLA
) -> CalculationResult:
    """
    Função principal que roteia para o cálculo correto baseado no modo.
    
    Args:
        dino: Dados do dinossauro
        mode: Modo de cálculo (VANILLA, PRIMAL_FEAR, OMEGA)
    
    Returns:
        CalculationResult com stats calculados e power score
    """
    dino.calculation_mode = mode
    
    switcher = {
        CalculationMode.VANILLA: calculate_vanilla_stats,
        CalculationMode.PRIMAL_FEAR: calculate_primal_fear_stats,
        CalculationMode.OMEGA: calculate_omega_stats,
    }
    
    calculator = switcher.get(mode, calculate_vanilla_stats)
    return calculator(dino)


# ============================================
# UTILITÁRIOS
# ============================================
def get_available_modes() -> list:
    """Retorna lista de modos disponíveis"""
    return [mode.value for mode in CalculationMode]


def get_mode_by_name(name: str) -> Optional[CalculationMode]:
    """Obtém modo pelo nome"""
    try:
        return CalculationMode[name.upper()]
    except (KeyError, AttributeError):
        return None


def get_primal_tiers() -> list:
    """Retorna lista de tiers Primal Fear"""
    return list(PRIMAL_FEAR_MULTIPLIERS.keys())


def get_omega_tiers() -> list:
    """Retorna lista de tiers Omega"""
    return list(OMEGA_TIER_MULTIPLIERS.keys())


def get_omega_variants() -> list:
    """Retorna lista de variantes Omega"""
    return list(OMEGA_VARIANT_MULTIPLIERS.keys())


def get_paragon_levels() -> list:
    """Retorna níveis de Paragon disponíveis"""
    return list(OMEGA_PARAGON_MULTIPLIERS.keys())
