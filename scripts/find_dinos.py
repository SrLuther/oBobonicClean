#!/usr/bin/env python3
import json

with open('data/dino_prices.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Procurar por nomes que faltaram
missing_names = [
    'rex', 'rock', 'spino', 'therizino', 'fire', 'wyvern', 
    'dodo', 'dragon', 'broodmother', 'megapithecus', 'dire',
    'indominus', 'reaper', 'sarco', 'seeker', 'defender',
    'manticore', 'dimorpho', 'purlovia', 'poison'
]

print("Dinossauros encontrados com correspondência:")
for key, dino in data['dinosaurs'].items():
    name = dino['name'].lower()
    for search in missing_names:
        if search in name:
            print(f"  {key} -> {dino['name']}")
            break
