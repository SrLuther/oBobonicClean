#!/usr/bin/env python
"""Script para adicionar categorias ao arquivo dino_prices.json"""

import json

# Mapeamento de criaturas por categoria
CATEGORIES = {
    "apex_combat": {
        "multiplier": 1.30,
        "creatures": [
            "carcharodontosaurus", "giganotosaurus", "reaper_king", "rock_elemental",
            "wyvern_fire", "wyvern_lightning", "wyvern_poison", "wyvern_ice",
            "voidwyrm", "shadowmane", "mek"
        ]
    },
    "pve_combat": {
        "multiplier": 1.20,
        "creatures": [
            "rex", "tek_rex", "spinosaurus", "therizinosaur", "allosaurus",
            "direwolf", "sabertooth", "megalosaurus", "yutyrannus", "carno",
            "baryonyx", "kaprosuchus", "microraptor", "velonasaur", "managarmr",
            "enforcer"
        ]
    },
    "criacao": {
        "multiplier": 1.40,
        "creatures": [
            "maewing", "procoptodon", "oviraptor", "daeodon", "phiomia",
            "paraceratherium", "diplodocus", "carbonemys", "megachelon"
        ]
    },
    "transporte": {
        "multiplier": 1.25,
        "creatures": [
            "argentavis", "quetzal", "tapejara", "pteranodon", "griffin",
            "snow_owl", "astrocetus", "brontosaurus", "diplocaulus", "gallimimus",
            "equus"
        ]
    },
    "farming": {
        "multiplier": 1.15,
        "creatures": [
            "ankylosaurus", "doedicurus", "castoroides", "mammoth", "magmasaur",
            "roll_rat", "dunkleosteus", "thorny_dragon", "mantis", "karkinos",
            "gigantopithecus"
        ]
    },
    "utilidade": {
        "multiplier": 1.10,
        "creatures": [
            "beelzebufo", "troodon", "ichthyornis", "otter", "shinehorn",
            "bulbdog", "featherlight", "glowtail", "mesopithecus", "compy",
            "vulture", "archaeopteryx", "lystrosaurus", "scout"
        ]
    }
}

# Criaturas que não podem ser castradas
NO_CASTRATION = ["reaper_king", "mek", "tek_stryder"]

# Mapa inverso: creature -> category
CREATURE_TO_CATEGORY = {}
for category, data in CATEGORIES.items():
    for creature in data["creatures"]:
        CREATURE_TO_CATEGORY[creature] = category

# Carrega JSON
with open("data/dino_prices.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Atualiza cada dinossauro
updated_count = 0
for dino_id, dino_info in data["dinosaurs"].items():
    # Define categoria (usa "outros" como padrão)
    category = CREATURE_TO_CATEGORY.get(dino_id, "outros")
    dino_info["category"] = category
    
    # Para Reaper King e Mek, marca que não podem ser castrados
    if dino_id in NO_CASTRATION:
        dino_info["no_castration"] = True
    
    updated_count += 1

print(f"✅ Atualizados {updated_count} dinossauros")

# Salva JSON atualizado
with open("data/dino_prices.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ arquivo dino_prices.json atualizado com sucesso!")
