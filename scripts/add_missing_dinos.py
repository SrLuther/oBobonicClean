#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para adicionar dinossauros que ainda faltam no banco
"""

import json
from pathlib import Path
from typing import Dict, Any

# Dinossauros que precisam ser adicionados manualmente (não encontrados com busca exata)
MISSING_DINOS = {
    # Nomes base que faltaram
    "t_rex": {
        "name": "T-Rex",
        "base_value": 9000,
        "stat_multipliers": {
            "melee": 270,
            "health": 181,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "apex_combat"
    },
    "rock_drake": {
        "name": "Rock Drake",
        "base_value": 8500,
        "stat_multipliers": {
            "melee": 250,
            "health": 170,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "apex_combat"
    },
    "spinosaur": {
        "name": "Spinosaur",
        "base_value": 7500,
        "stat_multipliers": {
            "melee": 230,
            "health": 150,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "pve_combat"
    },
    "therizinosaurus": {
        "name": "Therizinosaurus",
        "base_value": 7000,
        "stat_multipliers": {
            "melee": 220,
            "health": 145,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "pve_combat"
    },
    "fire_wyvern": {
        "name": "Fire Wyvern",
        "base_value": 6500,
        "stat_multipliers": {
            "melee": 200,
            "health": 130,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "pve_combat"
    },
    "lightning_wyvern": {
        "name": "Lightning Wyvern",
        "base_value": 6500,
        "stat_multipliers": {
            "melee": 200,
            "health": 130,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "pve_combat"
    },
    "ice_wyvern": {
        "name": "Ice Wyvern",
        "base_value": 6500,
        "stat_multipliers": {
            "melee": 200,
            "health": 130,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "pve_combat"
    },
    "poison_wyvern": {
        "name": "Poison Wyvern",
        "base_value": 6500,
        "stat_multipliers": {
            "melee": 200,
            "health": 130,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "pve_combat"
    },
    "wyvern": {
        "name": "Wyvern",
        "base_value": 6000,
        "stat_multipliers": {
            "melee": 190,
            "health": 125,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "pve_combat"
    },
    "dragon": {
        "name": "Dragon",
        "base_value": 12000,
        "stat_multipliers": {
            "melee": 300,
            "health": 200,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "apex_combat"
    },
    "broodmother": {
        "name": "Broodmother",
        "base_value": 10000,
        "stat_multipliers": {
            "melee": 280,
            "health": 190,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "apex_combat"
    },
    "reaper": {
        "name": "Reaper",
        "base_value": 9500,
        "stat_multipliers": {
            "melee": 275,
            "health": 185,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "apex_combat"
    },
    "reaper_king": {
        "name": "Reaper King",
        "base_value": 11000,
        "stat_multipliers": {
            "melee": 290,
            "health": 195,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "apex_combat"
    },
    "sarcosuchus": {
        "name": "Sarcosuchus",
        "base_value": 5500,
        "stat_multipliers": {
            "melee": 180,
            "health": 120,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "pve_combat"
    },
    "seeker": {
        "name": "Seeker",
        "base_value": 8000,
        "stat_multipliers": {
            "melee": 240,
            "health": 160,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "apex_combat"
    },
    "indominus_rex": {
        "name": "Indominus Rex",
        "base_value": 10000,
        "stat_multipliers": {
            "melee": 280,
            "health": 190,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "apex_combat"
    },
    "manticore": {
        "name": "Manticore",
        "base_value": 9000,
        "stat_multipliers": {
            "melee": 260,
            "health": 175,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "apex_combat"
    },
    "megapithecus": {
        "name": "Megapithecus",
        "base_value": 9000,
        "stat_multipliers": {
            "melee": 260,
            "health": 175,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "apex_combat"
    },
    "dodo_rex": {
        "name": "Dodo Rex",
        "base_value": 4000,
        "stat_multipliers": {
            "melee": 160,
            "health": 105,
            "stamina": 30,
            "weight": 25,
            "oxygen": 5,
            "food": 12
        },
        "optimal_stats": {"melee": 300, "health": 12000},
        "category": "otros"
    },
}

def load_dino_data(filepath: Path) -> Dict[str, Any]:
    """Carrega dados de dinossauros do JSON"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_dino_data(filepath: Path, data: Dict[str, Any]) -> None:
    """Salva dados de dinossauros no JSON"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    json_file = Path("data/dino_prices.json")
    
    print("📂 Carregando dados...")
    data = load_dino_data(json_file)
    dinosaurs = data["dinosaurs"]
    
    print(f"✅ Dados carregados: {len(dinosaurs)} dinossauros")
    
    added_count = 0
    skipped_count = 0
    
    print("\n🔄 Adicionando dinossauros base que faltaram...")
    for key, dino_data in MISSING_DINOS.items():
        if key not in dinosaurs:
            dinosaurs[key] = dino_data
            print(f"  ✅ Adicionado: {dino_data['name']}")
            added_count += 1
        else:
            print(f"  ⏭️  Já existe: {key}")
            skipped_count += 1
    
    # Agora adicionar variantes desses
    TIER_MULTIPLIERS = {
        "alpha": {"base_value": 1.5, "stat_multipliers": 1.2, "category": "alpha_combat"},
        "apex": {"base_value": 2.0, "stat_multipliers": 1.4, "category": "apex_combat"},
    }
    
    base_variants = list(MISSING_DINOS.keys())
    
    for prefix, multiplier_config in TIER_MULTIPLIERS.items():
        print(f"\n🔄 Adicionando {prefix.upper()} para dinossauros base...")
        for base_key in base_variants:
            new_key = f"{prefix}_{base_key}"
            
            if new_key not in dinosaurs and base_key in dinosaurs:
                base_dino = dinosaurs[base_key]
                new_data = {
                    "name": f"{prefix.title()} {base_dino['name']}",
                    "base_value": int(base_dino["base_value"] * multiplier_config["base_value"]),
                    "stat_multipliers": {
                        stat: int(mult * multiplier_config["stat_multipliers"])
                        for stat, mult in base_dino.get("stat_multipliers", {}).items()
                    },
                    "optimal_stats": base_dino.get("optimal_stats", {}),
                    "category": multiplier_config["category"]
                }
                dinosaurs[new_key] = new_data
                print(f"  ✅ Adicionado: {new_data['name']}")
                added_count += 1
    
    print(f"\n📊 Resumo:")
    print(f"  ✅ Adicionados: {added_count}")
    print(f"  ⏭️  Pulados: {skipped_count}")
    print(f"  📦 Total agora: {len(dinosaurs)} dinossauros")
    
    # Salvar dados
    print("\n💾 Salvando dados...")
    save_dino_data(json_file, data)
    print("✅ Arquivo salvo com sucesso!")

if __name__ == "__main__":
    main()
