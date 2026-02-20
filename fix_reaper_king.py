#!/usr/bin/env python
"""Fix remaining Reaper King references in dinosaur_valuer.py"""

with open("cogs/dinosaur_valuer.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the old Reaper King logic with new one
old_pattern = """            # Se é Reaper King (asexuado sem broca), abre avaliação diretamente
            elif dino_data.get("asexual", False):
                print(f"[DINOSAUR] {dino_id} é Reaper King, mostrando ReaperKingSelectView...")
                select_view = ReaperKingSelectView(self.dados, dino_id)
                
                embed = discord.Embed(
                    title="🦖 Reaper King",
                    description=f"O dinossauro **{self.dados.get('dinosaurs', {}).get(dino_id, {}).get('name', dino_id)}** sempre vale seu valor total (sem penalidades)",
                    color=discord.Color.blue()
                )"""

new_pattern = """            # Se é Reaper King ou Mek (não podem ser castrados)
            elif dino_id in ["reaper_king", "mek"] or dino_data.get("no_castration", False):
                print(f"[DINOSAUR] {dino_id} não pode ser castrado, mostrando ReaperKingSelectView...")
                select_view = ReaperKingSelectView(self.dados, dino_id)
                
                embed = discord.Embed(
                    title="🦖 Criatura Selecionada",
                    description=f"O dinossauro **{self.dados.get('dinosaurs', {}).get(dino_id, {}).get('name', dino_id)}** não pode ser castrado",
                    color=discord.Color.blue()
                )"""

# COUNT occurrences and replace them
count = content.count(old_pattern)
print(f"Found {count} ocurrences of old Reaper King pattern")

content = content.replace(old_pattern, new_pattern)

with open("cogs/dinosaur_valuer.py", "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ Replaced {count} occurrences")
print("✅ dinosaur_valuer.py atualizado!")
