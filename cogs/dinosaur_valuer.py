

import discord
from discord.ext import commands, tasks
import json
import os

PAINEL_CHANNEL_ID = 1474164587141271709
PRICES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".bancos", "dino_prices.json")

def load_dino_prices():
	try:
		with open(PRICES_PATH, "r", encoding="utf-8") as f:
			data = json.load(f)
		return data.get("dinosaurs", {})
	except Exception as e:
		print(f"[DinoValuer] Erro ao carregar dino_prices.json: {e}")
		return {}


class DinoStatModal(discord.ui.Modal):
	def __init__(self, dino_data, dino_key):
		super().__init__(title="Avaliação de Dinossauro")
		self.dino_data = dino_data
		self.dino_key = dino_key
		dino = dino_data[dino_key]
		self.stat_names = list(dino["stat_multipliers"].keys())
		for stat in self.stat_names:
			self.add_item(discord.ui.TextInput(label=stat.capitalize(), placeholder=f"Digite o valor de {stat}", required=False))

	async def on_submit(self, interaction: discord.Interaction):
		dino = self.dino_data[self.dino_key]
		stats = {}
		for child in self.children:
			if isinstance(child, discord.ui.TextInput):
				stat = child.label.lower()
				val = child.value
				try:
					stats[stat] = float(val) if val else 0
				except Exception:
					stats[stat] = 0
		valor = calcular_valor_dino(dino, stats)
		embed = discord.Embed(
			title=f"Avaliação: {dino['name']}",
			description=f"Valor estimado: **{valor:,.0f}**\n\nStats informados:",
			color=discord.Color.green()
		)
		for stat, val in stats.items():
			embed.add_field(name=stat.capitalize(), value=str(val), inline=True)
		embed.set_footer(text="Cálculo automático baseado em stats e valor base.")
		await interaction.response.send_message(embed=embed, ephemeral=True)

def calcular_valor_dino(dino, stats):
	valor = dino.get("base_value", 0)
	for stat, mult in dino.get("stat_multipliers", {}).items():
		stat_val = stats.get(stat, 0)
		valor += stat_val * mult
	return valor

class PainelView(discord.ui.View):
	def __init__(self, dino_data):
		super().__init__(timeout=None)
		self.dino_data = dino_data

	@discord.ui.button(label="Avaliar Dino", style=discord.ButtonStyle.green, custom_id="painel_avaliar_dino")
	async def avaliar_dino(self, interaction: discord.Interaction, button: discord.ui.Button):
		options = [discord.SelectOption(label=d["name"], value=k) for k, d in list(self.dino_data.items())[:25]]
		view = DinoSelectView(self.dino_data, options)
		embed = discord.Embed(
			title="🦖 Avaliação de Dinossauro (Vanilla)",
			description="Selecione o dinossauro para avaliar.",
			color=discord.Color.green()
		)
		await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class DinoSelect(discord.ui.Select):
	def __init__(self, dino_data, options):
		super().__init__(placeholder="Escolha o dinossauro...", min_values=1, max_values=1, options=options)
		self.dino_data = dino_data

	async def callback(self, interaction: discord.Interaction):
		dino_key = self.values[0]
		modal = DinoStatModal(self.dino_data, dino_key)
		await interaction.response.send_modal(modal)

class DinoSelectView(discord.ui.View):
	def __init__(self, dino_data, options):
		super().__init__(timeout=120)
		self.add_item(DinoSelect(dino_data, options))

	@discord.ui.button(label="Conversor de Recursos", style=discord.ButtonStyle.blurple, custom_id="painel_conversor")
	async def conversor(self, interaction: discord.Interaction, button: discord.ui.Button):
		embed = discord.Embed(
			title="💎 Conversor de Recursos",
			description="Converta rapidamente valores entre recursos do servidor.\n\n*Funcionalidade em desenvolvimento.*",
			color=discord.Color.blurple()
		)
		await interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(label="Tabela de Preços", style=discord.ButtonStyle.gray, custom_id="painel_precos")
	async def tabela_precos(self, interaction: discord.Interaction, button: discord.ui.Button):
		embed = discord.Embed(
			title="💰 Tabela de Preços Sugeridos",
			description="Veja valores médios para dinos, ovos, recursos e serviços.\n\n*Funcionalidade em desenvolvimento.*",
			color=discord.Color.gold()
		)
		await interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(label="Serviços", style=discord.ButtonStyle.red, custom_id="painel_servicos")
	async def servicos(self, interaction: discord.Interaction, button: discord.ui.Button):
		embed = discord.Embed(
			title="🛠️ Serviços",
			description="Consulte preços e regras para imprint, boss, mutação e outros serviços.\n\n*Funcionalidade em desenvolvimento.*",
			color=discord.Color.red()
		)
		await interaction.response.edit_message(embed=embed, view=self)


class PainelCog(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.painel_channel_id = PAINEL_CHANNEL_ID
		self.dino_data = load_dino_prices()

	@commands.Cog.listener()
	async def on_ready(self):
		await self.ensure_painel()

	async def ensure_painel(self):
		channel = self.bot.get_channel(self.painel_channel_id)
		if not isinstance(channel, discord.TextChannel):
			return
		async for msg in channel.history(limit=10):
			if msg.author == self.bot.user and msg.components:
				await msg.edit(embed=self.make_embed(), view=PainelView(self.dino_data))
				return
		await channel.send(embed=self.make_embed(), view=PainelView(self.dino_data))

	def make_embed(self):
		embed = discord.Embed(
			title="Painel de Câmbio & Avaliação",
			description=(
				"Bem-vindo ao painel interativo!\n\n"
				"Escolha uma opção abaixo para acessar as ferramentas de avaliação, câmbio e serviços do servidor.\n\n"
				"*Clique nos botões para navegar.*"
			),
			color=discord.Color.dark_teal()
		)
		embed.set_footer(text="Painel automático - sempre atualizado")
		return embed


async def setup(bot: commands.Bot):
	await bot.add_cog(PainelCog(bot))
