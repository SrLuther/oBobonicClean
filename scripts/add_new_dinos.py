#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para adicionar Alpha, Apex, Celestial e outros dinossauros ao arquivo JSON
"""

import json
from pathlib import Path
from typing import Dict, Any

# Melhoria dos dinos por tier relativo ao comum
TIER_MULTIPLIERS = {
    "alpha": {
        "base_value": 1.5,
        "stat_multipliers": 1.2,
        "category": "alpha_combat"
    },
    "apex": {
        "base_value": 2.0,
        "stat_multipliers": 1.4,
        "category": "apex_combat"
    },
    "celestial": {
        "base_value": 3.5,
        "stat_multipliers": 1.8,
        "category": "celestial_endgame"
    },
    "black_omega": {
        "base_value": 3.0,
        "stat_multipliers": 1.7,
        "category": "black_omega_advanced"
    },
    "spirit": {
        "base_value": 4.5,
        "stat_multipliers": 2.0,
        "category": "spirit_toptier"
    },
    "fey": {
        "base_value": 2.5,
        "stat_multipliers": 1.5,
        "category": "fey_expansion"
    },
    "primal": {
        "base_value": 2.2,
        "stat_multipliers": 1.35,
        "category": "primal_boss"
    }
}

# Alpha Creatures - derivados da lista do usuário
ALPHA_CREATURES = [
    "Allosaurus", "Ankylosaurus", "Araneo", "Argentavis", "Arthropluera",
    "Baryonyx", "Basilisk", "Basilosaurus", "Beelzebufo", "Bloodstalker",
    "Brachiosaurus", "Bronto", "Broodmother", "Bulbdog", "Bulbdog Rideable",
    "Carnotaurus", "Castoroides", "Chalicotherium", "Daeodon", "Defender",
    "Deinonychus", "Dilophosaur", "Dimorphodon", "Dire Bear", "Direwolf",
    "Dodo", "Dodo Rex", "Dodo Wyvern", "Doedicurus", "Dragon",
    "Enforcer", "Equus", "Featherlight", "Featherlight Rideable", "Ferox",
    "Fire Wyvern", "Gacha", "Gasbags", "Giganotosaurus", "Gigantopithecus",
    "Glowtail", "Glowtail Rideable", "Griffin", "Hesperornis", "Hyaenodon",
    "Ichthyosaurus", "Iguanodon", "Indominus Rex", "Kaprosuchus", "Karkinos",
    "Kentrosaurus", "Lightning Wyvern", "Liopleurodon", "Magmasaur",
    "Mammoth", "Managarmr", "Manticore", "Mantis", "Megalania",
    "Megaloceros", "Megalodon", "Megalosaurus", "Megapithecus", "Megatherium",
    "Morellatops", "Mosasaurus", "Nameless", "Onyc", "Otter",
    "Paracer", "Parasaur", "Pegomastax", "Phoenix", "Plesiosaur",
    "Poison Wyvern", "Pteranodon", "Pulmonoscorpius", "Purlovia", "Quetzal",
    "Raptor", "Ravager", "Reaper King", "Reaper Queen", "Rex",
    "Rock Drake", "Roll Rat", "Sabertooth", "Sarcosuchus", "Seeker",
    "Shinehorn", "Shinehorn Rideable", "Snow Owl", "Spinosaur",
    "Stegosaurus", "Stygimoloch", "Styracosaurus", "Tapejara", "Terror Bird",
    "Therizinosaurus", "Thorny Dragon", "Thylacoleo", "Titanoboa", "Triceratops",
    "Troodon", "Tropeognathus", "Tusoteuthis", "Velonasaur", "Woolly Rhino",
    "Yutyrannus"
]

# Apex Creatures
APEX_CREATURES = [
    "Allosaurus", "Argentavis", "Baryonyx", "Basilisk", "Basilosaurus",
    "Broodmother", "Carnotaurus", "Chalicotherium", "Daeodon", "Defender",
    "Deinonychus", "Dilophosaur", "Dire Bear", "Direwolf", "Dodo Rex",
    "Dodo Wyvern", "Dragon", "Enforcer", "Ferox", "Fire Wyvern",
    "Giganotosaurus", "Griffin", "Hyaenodon", "Indominus Rex", "Kaprosuchus",
    "Karkinos", "Kentrosaurus", "Lightning Wyvern", "Liopleurodon", "Magmasaur",
    "Managarmr", "Manticore", "Megalodon", "Megalosaurus", "Megapithecus",
    "Mosasaurus", "Phoenix", "Plesiosaur", "Poison Wyvern", "Pulmonoscorpius",
    "Purlovia", "Raptor", "Ravager", "Reaper King", "Reaper Queen",
    "Rex", "Rock Drake", "Sabertooth", "Sarco", "Seeker",
    "Snow Owl", "Spinosaur", "Terror Bird", "Therizinosaurus", "Thorny Dragon",
    "Thylacoleo", "Tusoteuthis", "Velonasaur", "Yutyrannus"
]

# Ascended Celestial Creatures
CELESTIAL_CREATURES = [
    "Allosaurus", "Argentavis", "Griffin",
    "Rex", "Rock Drake", "Seeker",
    "Spinosaur", "Thylacoleo", "Wyvern", "Yutyrannus"
]

# Black Omega Creatures
BLACK_OMEGA_CREATURES = [
    "Allosaurus", "Fire Wyvern", "Ice Wyvern", "Indominus Rex",
    "Lightning Wyvern", "Poison Wyvern", "Reaper", "Rex",
    "Sarco", "Spinosaur"
]

# Spirit/Chaos Creatures
SPIRIT_CREATURES = [
    "Chaos Guardian", "Spirit Guardian"
]

# Fey Tier (high-tiers)
FEY_CREATURES = [
    "Rex", "Spinosaur", "Therizinosaurus", "Thylacoleo",
    "Rock Drake", "Managarmr", "Griffin", "Wyvern"
]

# Primal Creatures
PRIMAL_CREATURES = [
    "Allosaurus", "Carnotaurus", "Dire Bear", "Giganotosaurus", "Kentrosaurus",
    "Liopleurodon", "Megalodon", "Mosasaurus", "Plesiosaur", "Raptor",
    "Rex", "Rock Drake", "Spinosaur", "Thylacoleo", "Broodmother",
    "Dodo Rex", "Dodo Wyvern", "Dragon", "Manticore", "Megapithecus"
]

def normalize_name(name: str) -> str:
    """Converte nome para minúsculas com underscore"""
    return name.lower().replace(" ", "_")

def load_dino_data(filepath: Path) -> Dict[str, Any]:
    """Carrega dados de dinossauros do JSON"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_dino_data(filepath: Path, data: Dict[str, Any]) -> None:
    """Salva dados de dinossauros no JSON"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def create_variant_dino(original_key: str, original_data: dict, prefix: str, multiplier_config: dict) -> tuple[str, dict]:
    """Cria um dinossauro variante baseado no original"""
    new_key = f"{prefix}_{original_key}" if prefix != "ascended_celestial" else f"ascended_celestial_{original_key}"
    
    # Para spirit creatures que são nomes especiais
    if original_data["name"] in ["Chaos Guardian", "Spirit Guardian"]:
        new_name = f"{prefix.replace('_', ' ').title()} {original_data['name']}"
    elif prefix == "ascended_celestial":
        new_name = f"Ascended Celestial {original_data['name']}"
    elif prefix == "black_omega":
        new_name = f"Black Omega {original_data['name']}"
    elif prefix == "fey":
        new_name = f"Fey {original_data['name']}"
    else:
        new_name = f"{prefix.title()} {original_data['name']}"
    
    # Aplicar multiplicadores
    new_data = {
        "name": new_name,
        "base_value": int(original_data["base_value"] * multiplier_config["base_value"]),
        "stat_multipliers": {
            stat: int(multiplier * multiplier_config["stat_multipliers"])
            for stat, multiplier in original_data.get("stat_multipliers", {}).items()
        },
        "optimal_stats": original_data.get("optimal_stats", {}),
        "category": multiplier_config["category"]
    }
    
    return new_key, new_data

def main():
    json_file = Path("data/dino_prices.json")
    
    print("📂 Carregando dados...")
    data = load_dino_data(json_file)
    dinosaurs = data["dinosaurs"]
    
    print(f"✅ Dados carregados: {len(dinosaurs)} dinossauros")
    
    # Processar adicione de novo variants
    variants_to_add = {
        "alpha": (ALPHA_CREATURES, TIER_MULTIPLIERS["alpha"]),
        "apex": (APEX_CREATURES, TIER_MULTIPLIERS["apex"]),
        "ascended_celestial": (CELESTIAL_CREATURES, TIER_MULTIPLIERS["celestial"]),
        "black_omega": (BLACK_OMEGA_CREATURES, TIER_MULTIPLIERS["black_omega"]),
        "spirit": (SPIRIT_CREATURES, TIER_MULTIPLIERS["spirit"]),
        "fey": (FEY_CREATURES, TIER_MULTIPLIERS["fey"]),
        "primal": (PRIMAL_CREATURES, TIER_MULTIPLIERS["primal"])
    }
    
    added_count = 0
    skipped_count = 0
    
    for prefix, (creature_names, multiplier_config) in variants_to_add.items():
        print(f"\n🔄 Processando {prefix.upper()}...")
        
        for creature_name in creature_names:
            # Normalizar nome para procura
            search_key = normalize_name(creature_name.replace(" rideable", ""))
            
            # Procura no dicionário existente
            found_key = None
            for existing_key in dinosaurs:
                if normalize_name(dinosaurs[existing_key]["name"]).split("(")[0].strip() == search_key:
                    found_key = existing_key
                    break
            
            if not found_key:
                print(f"  ⚠️  Não encontrado: {creature_name}")
                skipped_count += 1
                continue
            
            # Criar variante
            new_key, new_data = create_variant_dino(
                found_key,
                dinosaurs[found_key],
                prefix,
                multiplier_config
            )
            
            if new_key not in dinosaurs:
                dinosaurs[new_key] = new_data
                added_count += 1
                print(f"  ✅ Adicionado: {new_data['name']}")
            else:
                print(f"  ⏭️  Já existe: {new_key}")
    
    print(f"\n📊 Resumo:")
    print(f"  ✅ Adicionados: {added_count}")
    print(f"  ⚠️  Pulados: {skipped_count}")
    print(f"  📦 Total agora: {len(dinosaurs)} dinossauros")
    
    # Salvar dados
    print("\n💾 Salvando dados...")
    save_dino_data(json_file, data)
    print("✅ Arquivo salvo com sucesso!")

if __name__ == "__main__":
    main()
