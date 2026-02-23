#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para adicionar TODAS as variantes de dinossauros (700+ custom dinos)
Vai pegar cada dino base e criar todas as variantes: Alpha, Apex, Celestial, 
Black Omega, Spirit, Fey, Primal, Demonic
"""

import json
from pathlib import Path
from typing import Dict, Any

# Todas as variantes + bonus
TIER_MULTIPLIERS = {
    "alpha": {
        "base_value": 1.5,
        "stat_multipliers": 1.2,
        "category": "alpha_combat",
        "emoji": "🐲"
    },
    "apex": {
        "base_value": 2.0,
        "stat_multipliers": 1.4,
        "category": "apex_combat",
        "emoji": "🔥"
    },
    "ascended_celestial": {
        "base_value": 3.5,
        "stat_multipliers": 1.8,
        "category": "celestial_endgame",
        "emoji": "☀️"
    },
    "black_omega": {
        "base_value": 3.0,
        "stat_multipliers": 1.7,
        "category": "black_omega_advanced",
        "emoji": "🌑"
    },
    "spirit": {
        "base_value": 4.5,
        "stat_multipliers": 2.0,
        "category": "spirit_toptier",
        "emoji": "👻"
    },
    "fey": {
        "base_value": 2.5,
        "stat_multipliers": 1.5,
        "category": "fey_expansion",
        "emoji": "🧚"
    },
    "primal": {
        "base_value": 2.2,
        "stat_multipliers": 1.35,
        "category": "primal_boss",
        "emoji": "💀"
    },
    "demonic": {
        "base_value": 2.8,
        "stat_multipliers": 1.6,
        "category": "demonic_variant",
        "emoji": "😈"
    }
}

def load_dino_data(filepath: Path) -> Dict[str, Any]:
    """Carrega dados de dinossauros do JSON"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_dino_data(filepath: Path, data: Dict[str, Any]) -> None:
    """Salva dados de dinossauros no JSON"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def normalize_variant_name(name: str, prefix: str) -> str:
    """Cria nome da variante"""
    if prefix == "ascended_celestial":
        return f"Ascended Celestial {name}"
    elif prefix == "black_omega":
        return f"Black Omega {name}"
    elif prefix == "demonic":
        return f"Demonic {name}"
    else:
        return f"{prefix.title()} {name}"

def main():
    json_file = Path("data/dino_prices.json")
    
    print("📂 Carregando dados...")
    data = load_dino_data(json_file)
    dinosaurs = data["dinosaurs"]
    
    # Fazer lista de dinos base (sem prefixo)
    base_dinos = {}
    for key, dino in dinosaurs.items():
        # Se não começa com nenhum prefixo de variante, é base
        is_base = not any(key.startswith(f"{prefix}_") for prefix in TIER_MULTIPLIERS.keys())
        if is_base:
            base_dinos[key] = dino
    
    print(f"✅ Dados carregados: {len(dinosaurs)} dinossauros totais")
    print(f"📌 Dinossauros BASE encontrados: {len(base_dinos)}")
    
    added_count = 0
    skipped_count = 0
    
    # Para cada dino base, criar todas as variantes
    print("\n🔄 Criando variantes completas para todos os dinossauros...")
    
    for base_key, base_dino in base_dinos.items():
        for prefix, multiplier_config in TIER_MULTIPLIERS.items():
            new_key = f"{prefix}_{base_key}"
            
            # Não duplicar se já existe
            if new_key in dinosaurs:
                skipped_count += 1
                continue
            
            # Gerar nome da variante
            variant_name = normalize_variant_name(base_dino["name"], prefix)
            
            # Criar dados da variante
            new_data = {
                "name": variant_name,
                "base_value": int(base_dino["base_value"] * multiplier_config["base_value"]),
                "stat_multipliers": {
                    stat: int(mult * multiplier_config["stat_multipliers"])
                    for stat, mult in base_dino.get("stat_multipliers", {}).items()
                },
                "optimal_stats": base_dino.get("optimal_stats", {}),
                "category": multiplier_config["category"]
            }
            
            dinosaurs[new_key] = new_data
            added_count += 1
    
    print(f"\n📊 Resumo:")
    print(f"  ✅ Adicionados: {added_count}")
    print(f"  ⏭️  Já existentes: {skipped_count}")
    print(f"  📦 Total agora: {len(dinosaurs)} dinossauros")
    print(f"  💰 Estimado +700: {'✅ SIM!' if len(dinosaurs) >= 700 else '⚠️  Ainda faltam'}")
    
    # Salvar dados
    print("\n💾 Salvando dados...")
    save_dino_data(json_file, data)
    print("✅ Arquivo salvo com sucesso!")

if __name__ == "__main__":
    main()
