import discord
from discord.ext import commands
from discord import ui, Interaction, ButtonStyle
import asyncio
import time
import uuid
import random
from collections import Counter

from config import VOTACAO_CANAL_ID, VOTACAO_CONFIG_CANAL_ID
from utils.json_utils import load_json_async, save_json_async

VOTACOES_FILE = ".bancos/votacoes.json"

# =========================
# MAPAS ARK ROTATIVOS
# =========================
MAPAS_ARK = [
	"The Island",
	"The Center",
	"Scorched Earth",
	"Ragnarok",
	"Aberration",
	"Extinction",
	"Valguero",
	"Genesis: Part 1",
	"Crystal Isles",
	"Lost Island",
	"Fjordur",
]


# =========================
# LOCK GLOBAL DE ESCRITA
# =========================
SAVE_LOCK = asyncio.Lock()


# =========================
# MODAL EDIÇÃO
# =========================
class EditarVotacaoModal(ui.Modal):
	def __init__(self, bot, votacao):
		super().__init__(title="Editar Votação")
		self.bot = bot
		self.vid = votacao["id"]

		self.titulo = ui.TextInput(label="Título", default=votacao["titulo"])
		self.detalhes = ui.TextInput(label="Detalhes", required=False, default=votacao.get("detalhes") or "", style=discord.TextStyle.paragraph)
		self.tempo_extra = ui.TextInput(label="Adicionar tempo (horas, ex: 2)", required=False, placeholder="Deixe vazio para não alterar")

		self.add_item(self.titulo)
		self.add_item(self.detalhes)
		self.add_item(self.tempo_extra)

	async def on_submit(self, interaction: Interaction):
		data = await load_json_async(VOTACOES_FILE, default={"votacoes": []})
		votacoes = data.get("votacoes", [])
		votacao = next((v for v in votacoes if v["id"] == self.vid), None)

		if not votacao or votacao.get("encerrada"):
			return await interaction.response.send_message("Votação não encontrada ou já encerrada.", ephemeral=True)

		votacao["titulo"] = self.titulo.value.strip()
		votacao["detalhes"] = self.detalhes.value.strip()

		if self.tempo_extra.value.strip():
			try:
				extra = float(self.tempo_extra.value.strip()) * 3600
				votacao["duracao"] += int(extra)
			except ValueError:
				return await interaction.response.send_message("Tempo inválido. Use um número (ex: 2).", ephemeral=True)

		async with SAVE_LOCK:
			await save_json_async(VOTACOES_FILE, {"votacoes": votacoes})

		await self.bot.get_cog("Voting").atualizar_painel_votacao(votacao)
		await interaction.response.send_message(f"✅ Votação **{votacao['titulo']}** atualizada!", ephemeral=True)


# =========================
# VIEW GERENCIAMENTO
# =========================
class GerenciarVotacaoView(ui.View):
	def __init__(self, bot, votacao):
		super().__init__(timeout=60)
		self.bot = bot
		self.votacao = votacao

	@ui.button(label="✏️ Editar", style=ButtonStyle.primary)
	async def editar(self, interaction: Interaction, button: ui.Button):
		await interaction.response.send_modal(EditarVotacaoModal(self.bot, self.votacao))

	@ui.button(label="🛑 Encerrar Agora", style=ButtonStyle.danger)
	async def encerrar(self, interaction: Interaction, button: ui.Button):
		data = await load_json_async(VOTACOES_FILE, default={"votacoes": [], "historico_mapas": []})
		votacoes = data.get("votacoes", [])
		votacao = next((v for v in votacoes if v["id"] == self.votacao["id"]), None)

		if not votacao or votacao.get("encerrada"):
			return await interaction.response.send_message("Já encerrada.", ephemeral=True)

		votacao["encerrada"] = True
		voting_cog = self.bot.get_cog("Voting")
		if voting_cog:
			await voting_cog._registrar_vencedor_mapa(votacao, data)
		async with SAVE_LOCK:
			await save_json_async(VOTACOES_FILE, data)

		if voting_cog:
			await voting_cog.atualizar_painel_votacao(votacao)
		for item in self.children:
			item.disabled = True
		await interaction.response.edit_message(content=f"🛑 Votação **{votacao['titulo']}** encerrada!", view=self)


# =========================
# SELECT GERENCIAMENTO
# =========================
class GerenciarSelectView(ui.View):
	def __init__(self, bot, abertas):
		super().__init__(timeout=60)
		self.bot = bot
		self.add_item(GerenciarSelect(bot, abertas))


class GerenciarSelect(ui.Select):
	def __init__(self, bot, abertas):
		self.abertas = {v["id"]: v for v in abertas}
		options = [
			discord.SelectOption(label=v["titulo"][:100], value=v["id"])
			for v in abertas
		]
		super().__init__(placeholder="Selecione uma votação para gerenciar...", options=options)
		self.bot = bot

	async def callback(self, interaction: Interaction):
		votacao = self.abertas.get(self.values[0])
		if not votacao:
			return await interaction.response.send_message("Votação não encontrada.", ephemeral=True)

		now = time.time()
		fim = votacao["criada_em"] + votacao["duracao"]
		restante = max(0, int(fim - now))
		horas = restante // 3600
		minutos = (restante % 3600) // 60
		tempo_str = f"{horas}h {minutos}m" if horas > 0 else f"{minutos}m {restante % 60}s"

		votos = votacao.get("votos", {})
		total = len(votos)
		cont = Counter(votos.values())
		opcoes = votacao.get("opcoes", [])
		linhas = "".join(
			f"`{'█' * (int((cont.get(i,0)/total)*10) if total else 0)}{'░' * (10 - (int((cont.get(i,0)/total)*10) if total else 0))}` **{op}** — {cont.get(i,0)} ({int((cont.get(i,0)/total)*100) if total else 0}%)\n"
			for i, op in enumerate(opcoes)
		)

		embed = discord.Embed(
			title=f"⚙️ Gerenciar: {votacao['titulo']}",
			description=(votacao.get("detalhes") or "") + ("\n\n" if votacao.get("detalhes") else "") + linhas,
			color=discord.Color.orange()
		)
		embed.add_field(name="⏱️ Tempo restante", value=tempo_str, inline=True)
		embed.add_field(name="🗳️ Votos", value=str(total), inline=True)

		await interaction.response.send_message(
			embed=embed,
			view=GerenciarVotacaoView(self.bot, votacao),
			ephemeral=True
		)


# =========================
# PAINEL CONFIG
# =========================
class VotingConfigView(ui.View):
	def __init__(self, bot):
		super().__init__(timeout=None)
		self.bot = bot

	@ui.button(label="Gerenciar Votações", style=ButtonStyle.danger, custom_id="voting:forceclose")
	async def encerrar(self, interaction: Interaction, button: ui.Button):
		data = await load_json_async(VOTACOES_FILE, default={"votacoes": []})
		abertas = [v for v in data.get("votacoes", []) if not v.get("encerrada")]

		if not abertas:
			return await interaction.response.send_message("Não há votações ativas.", ephemeral=True)

		await interaction.response.send_message(
			"Selecione a votação para gerenciar:",
			view=GerenciarSelectView(self.bot, abertas),
			ephemeral=True
		)

	@ui.button(label="Nova Votação", style=ButtonStyle.success, custom_id="voting:new")
	async def nova(self, interaction: Interaction, button: ui.Button):
		await interaction.response.send_modal(NewVotingModal(self.bot))

	@ui.button(label="Ver Votações Ativas", style=ButtonStyle.primary, custom_id="voting:list")
	async def listar(self, interaction: Interaction, button: ui.Button):
		data = await load_json_async(VOTACOES_FILE, default={"votacoes": []})
		abertas = [v for v in data.get("votacoes", []) if not v.get("encerrada") and v.get("tipo") != "mapa"]

		if not abertas:
			return await interaction.response.send_message("Nenhuma votação ativa no momento.", ephemeral=True)

		embeds = []
		for v in abertas:
			now = time.time()
			fim = v["criada_em"] + v["duracao"]
			restante = max(0, int(fim - now))
			horas = restante // 3600
			minutos = (restante % 3600) // 60
			segundos = restante % 60
			if horas > 0:
				tempo_str = f"{horas}h {minutos}m"
			elif minutos > 0:
				tempo_str = f"{minutos}m {segundos}s"
			else:
				tempo_str = f"{segundos}s"

			votos = v.get("votos", {})
			opcoes = v.get("opcoes", [])
			cont = Counter(votos.values())
			total = len(votos)

			linhas_opcoes = ""
			for i, op in enumerate(opcoes):
				qtd = cont.get(i, 0)
				pct = int((qtd / total) * 100) if total > 0 else 0
				barra = "█" * (pct // 10) + "░" * (10 - pct // 10)
				linhas_opcoes += f"`{barra}` **{op}** — {qtd} voto(s) ({pct}%)\n"

			embed = discord.Embed(
				title=f"📊 {v['titulo']}",
				description=(v.get("detalhes") or "") + ("\n\n" if v.get("detalhes") else "") + linhas_opcoes,
				color=discord.Color.blurple()
			)
			embed.add_field(name="⏱️ Tempo restante", value=tempo_str, inline=True)
			embed.add_field(name="🗳️ Total de votos", value=str(total), inline=True)
			embeds.append(embed)

		await interaction.response.send_message(embeds=embeds, ephemeral=True)


# =========================
# PAINEL MAPA ROTATIVO
# =========================
class MapaConfigView(ui.View):
	def __init__(self, bot):
		super().__init__(timeout=None)
		self.bot = bot

	@ui.button(label="▶️ Iniciar Agora", style=ButtonStyle.success, custom_id="mapa:iniciar")
	async def iniciar(self, interaction: Interaction, button: ui.Button):
		data = await load_json_async(VOTACOES_FILE, default={"votacoes": [], "historico_mapas": []})
		ativa = next((v for v in data.get("votacoes", []) if not v.get("encerrada") and v.get("tipo") == "mapa"), None)
		if ativa:
			return await interaction.response.send_message("⚠️ Já há uma votação de mapa ativa!", ephemeral=True)
		await interaction.response.defer(ephemeral=True)
		await self.bot.get_cog("Voting")._criar_votacao_mapa_automatica(data)
		await interaction.followup.send("✅ Votação de mapa iniciada!", ephemeral=True)

	@ui.button(label="🛑 Encerrar Agora", style=ButtonStyle.danger, custom_id="mapa:encerrar")
	async def encerrar(self, interaction: Interaction, button: ui.Button):
		data = await load_json_async(VOTACOES_FILE, default={"votacoes": [], "historico_mapas": []})
		ativa = next((v for v in data.get("votacoes", []) if not v.get("encerrada") and v.get("tipo") == "mapa"), None)
		if not ativa:
			return await interaction.response.send_message("Nenhuma votação de mapa ativa.", ephemeral=True)
		ativa["encerrada"] = True
		voting_cog = self.bot.get_cog("Voting")
		if voting_cog:
			await voting_cog._registrar_vencedor_mapa(ativa, data)
		async with SAVE_LOCK:
			await save_json_async(VOTACOES_FILE, data)
		if voting_cog:
			await voting_cog.atualizar_painel_votacao(ativa)
			await voting_cog._atualizar_painel_config_mapa(data)
		await interaction.response.send_message("🛑 Votação de mapa encerrada!", ephemeral=True)

	@ui.button(label="📊 Status", style=ButtonStyle.primary, custom_id="mapa:status")
	async def status(self, interaction: Interaction, button: ui.Button):
		data = await load_json_async(VOTACOES_FILE, default={"votacoes": [], "historico_mapas": []})
		ativa = next((v for v in data.get("votacoes", []) if not v.get("encerrada") and v.get("tipo") == "mapa"), None)
		if not ativa:
			return await interaction.response.send_message("Nenhuma votação de mapa ativa no momento.", ephemeral=True)
		embed = self.bot.get_cog("Voting").criar_embed(ativa)
		await interaction.response.send_message(embed=embed, ephemeral=True)

	@ui.button(label="🗑️ Limpar Bloqueios", style=ButtonStyle.secondary, custom_id="mapa:limpar")
	async def limpar(self, interaction: Interaction, button: ui.Button):
		data = await load_json_async(VOTACOES_FILE, default={"votacoes": [], "historico_mapas": []})
		data["historico_mapas"] = []
		async with SAVE_LOCK:
			await save_json_async(VOTACOES_FILE, data)
		voting_cog = self.bot.get_cog("Voting")
		if voting_cog:
			await voting_cog._atualizar_painel_config_mapa(data)
		await interaction.response.send_message("✅ Histórico de bloqueios limpo! Todos os mapas estão disponíveis.", ephemeral=True)


# =========================
# MODAL CRIAÇÃO
# =========================
class NewVotingModal(ui.Modal):
	def __init__(self, bot):
		super().__init__(title="Nova Votação")
		self.bot = bot

		self.titulo = ui.TextInput(label="Título")
		self.detalhes = ui.TextInput(label="Detalhes", required=False)
		self.opcoes = ui.TextInput(label="Opções (uma por linha)", style=discord.TextStyle.paragraph)
		self.tempo = ui.TextInput(label="Tempo (horas)", required=False)

		self.add_item(self.titulo)
		self.add_item(self.detalhes)
		self.add_item(self.opcoes)
		self.add_item(self.tempo)

	async def on_submit(self, interaction: Interaction):
		import datetime

		titulo = self.titulo.value.strip()
		opcoes = [o.strip() for o in self.opcoes.value.splitlines() if o.strip()]

		if not titulo or len(opcoes) < 2:
			return await interaction.response.send_message(
				"Título e 2 opções são obrigatórios.",
				ephemeral=True
			)

		if self.tempo.value.strip():
			duracao = int(float(self.tempo.value) * 3600)
		else:
			duracao = 86400  # 24h padrão

		votacao = {
			"id": str(uuid.uuid4()),
			"titulo": titulo,
			"detalhes": self.detalhes.value,
			"opcoes": opcoes,
			"votos": {},
			"criada_em": time.time(),
			"duracao": duracao,
			"encerrada": False,
			"mensagem_id": None
		}

		data = await load_json_async(VOTACOES_FILE, default={"votacoes": []})
		data["votacoes"].append(votacao)

		async with SAVE_LOCK:
			await save_json_async(VOTACOES_FILE, data)

		await interaction.response.send_message("Criada!", ephemeral=True)
		await self.bot.get_cog("Voting").publicar_votacao(votacao)


# =========================
# COG PRINCIPAL
# =========================

class Voting(commands.Cog):
	async def setup_config(self):
		"""Limpa o canal de config e envia os dois painéis frescos."""
		print(f"[VOTING] 🔍 Procurando canal de config: {VOTACAO_CONFIG_CANAL_ID}")
		canal = self.bot.get_channel(VOTACAO_CONFIG_CANAL_ID)
		if not canal:
			print(f"[VOTING] ❌ Canal de config não encontrado (ID: {VOTACAO_CONFIG_CANAL_ID})")
			return
		print(f"[VOTING] ✅ Canal encontrado: {canal.name}")

		self.bot.add_view(VotingConfigView(self.bot))
		self.bot.add_view(MapaConfigView(self.bot))

		data = await load_json_async(VOTACOES_FILE, default={"votacoes": [], "historico_mapas": [], "mapa_corrente": "Extinction"})
		if "mapa_corrente" not in data:
			data["mapa_corrente"] = "Extinction"

		# Limpa o canal e envia painéis novos
		try:
			await canal.purge(limit=None)
			print("[VOTING] 🗑️ Canal de config limpo.")
		except Exception as e:
			print(f"[VOTING] ⚠️ Erro ao limpar canal: {e}")

		# --- Painel Geral ---
		msg_geral = await canal.send(
			"**⚙️ Painel de Votações**\nCrie e gerencie votações personalizadas do servidor.",
			view=VotingConfigView(self.bot)
		)
		data["config_geral_msg_id"] = msg_geral.id
		print("[VOTING] ✅ Painel geral enviado!")

		# --- Painel Mapa ---
		msg_mapa = await canal.send(
			embed=self._embed_painel_mapa(data),
			view=MapaConfigView(self.bot)
		)
		data["config_mapa_msg_id"] = msg_mapa.id
		print("[VOTING] ✅ Painel de mapa enviado!")

		async with SAVE_LOCK:
			await save_json_async(VOTACOES_FILE, data)

	def __init__(self, bot):
		self.bot = bot
		self.bot.loop.create_task(self.startup())
		self.bot.loop.create_task(self.updater())
		self.bot.loop.create_task(self.mapa_scheduler())

	async def startup(self):
		try:
			await self.bot.wait_until_ready()
			print("[VOTING] ⏳ Bot pronto! Iniciando startup...")
			data = await load_json_async(VOTACOES_FILE, default={"votacoes": []})
			votacoes_ativas = [v for v in data.get("votacoes", []) if not v.get("encerrada")]
			for v in votacoes_ativas:
				self.bot.add_view(VotingPanelView(self.bot, v["id"], v["opcoes"]))
			print(f"[VOTING] 🔄 {len(votacoes_ativas)} votação(ões) ativa(s) restaurada(s).")
			await self.setup_config()
		except Exception as e:
			print(f"[VOTING] ❌ Erro no startup: {e}")
			import traceback; traceback.print_exc()

	# -------------------------
	# LOOP
	# -------------------------
	async def updater(self):
		await self.bot.wait_until_ready()

		while True:
			try:
				data = await load_json_async(VOTACOES_FILE, default={"votacoes": [], "historico_mapas": []})
				votacoes = data.get("votacoes", [])
				now = time.time()
				changed = False

				for v in votacoes:
					if v.get("encerrada"):
						continue
					fim = v["criada_em"] + v["duracao"]
					if now >= fim:
						v["encerrada"] = True
						changed = True
						await self._registrar_vencedor_mapa(v, data)
					await self.atualizar_painel_votacao(v)

				if changed:
					async with SAVE_LOCK:
						await save_json_async(VOTACOES_FILE, data)
					await self._atualizar_painel_config_mapa(data)
			except Exception as e:
				print(f"[VOTING] ❌ Erro no updater: {e}")

			await asyncio.sleep(60)

	# -------------------------
	# SCHEDULER MAPA
	# -------------------------
	async def mapa_scheduler(self):
		await self.bot.wait_until_ready()
		import datetime
		while True:
			try:
				now_brt = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
				weekday = now_brt.weekday()  # 0=Segunda, 6=Domingo

				if weekday == 0:  # Segunda-feira
					data = await load_json_async(VOTACOES_FILE, default={"votacoes": [], "historico_mapas": []})
					has_active = any(v for v in data.get("votacoes", []) if not v.get("encerrada") and v.get("tipo") == "mapa")
					if not has_active:
						# Verifica se já foi criada esta semana
						monday_midnight_brt = now_brt.replace(hour=0, minute=0, second=0, microsecond=0)
						monday_ts = (monday_midnight_brt + datetime.timedelta(hours=3)).timestamp()
						map_votes = [v for v in data.get("votacoes", []) if v.get("tipo") == "mapa"]
						last_vote = max(map_votes, key=lambda v: v["criada_em"], default=None)
						if not last_vote or last_vote["criada_em"] < monday_ts:
							print("[VOTING] 📅 Segunda-feira detectada — criando votação de mapa automática...")
							await self._criar_votacao_mapa_automatica(data)
			except Exception as e:
				print(f"[VOTING] ❌ Erro no mapa_scheduler: {e}")
			await asyncio.sleep(60)

	# -------------------------
	# CRIAÇÃO AUTOMÁTICA MAPA
	# -------------------------
	async def _criar_votacao_mapa_automatica(self, data=None):
		import datetime
		if data is None:
			data = await load_json_async(VOTACOES_FILE, default={"votacoes": [], "historico_mapas": []})
		historico = data.get("historico_mapas", [])
		mapa_atual = data.get("mapa_corrente") or (historico[-1] if historico else "Extinction")
		bloqueados = set(historico[-2:])
		# O mapa atual é sempre incluído; sorteamos 4 extras entre os demais disponíveis
		disponiveis = [m for m in MAPAS_ARK if m not in bloqueados and m != mapa_atual]
		sorteados_extras = random.sample(disponiveis, min(4, len(disponiveis)))
		sorteados = [mapa_atual] + sorteados_extras

		# Duração até domingo 00:00 BRT
		now_brt = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
		days_until_sunday = (6 - now_brt.weekday()) % 7 or 7
		sunday_midnight_brt = (now_brt + datetime.timedelta(days=days_until_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)
		sunday_ts = (sunday_midnight_brt + datetime.timedelta(hours=3)).timestamp()
		duracao = max(int(sunday_ts - time.time()), 3600)

		votacao = {
			"id": str(uuid.uuid4()),
			"tipo": "mapa",
			"titulo": "🗺️ Vote no Próximo Mapa Rotativo!",
			"detalhes": (
				"🤖 **Bot no comando** — nenhum adm precisa fazer nada, isso rola sozinho toda semana.\n\n"
				"**As regras do jogo:**\n"
				"📌 O bot sorteia **4 mapas** aleatórios toda segunda + o mapa atual, que sempre entra na lista\n"
				"🗺️ O **mapa atual tá sempre disponível** pra voto — se a galera quiser manter, é só votar nele\n"
				"🚫 O **mapa anterior** fica fora do sorteio essa semana pra não ficar repetindo\n"
				"🗳️ Votação aberta de **segunda a sábado** — cada membro tem direito a **1 voto**\n"
				"🌙 No **domingo**, os votos fecham e o vencedor vai pro servidor\n"
				"🔁 Semana seguinte, o ciclo se repete\n"
				"⭐ **Votar dá +1.000 XP no ranking — vale a pena aparecer!**\n\n"
				f"🗺️ **No ar agora:** {mapa_atual}\n"
				f"🚫 **Fora do sorteio essa semana:** {next(iter(bloqueados - {mapa_atual}), 'nenhum')}\n\n"
				f"⚠️ Semana sem voto? {mapa_atual} segura o trôno."
			),
			"opcoes": sorteados,
			"votos": {},
			"criada_em": time.time(),
			"duracao": duracao,
			"encerrada": False,
			"mensagem_id": None
		}
		data.setdefault("votacoes", []).append(votacao)
		async with SAVE_LOCK:
			await save_json_async(VOTACOES_FILE, data)
		await self.publicar_votacao(votacao)
		await self._atualizar_painel_config_mapa(data)
		print(f"[VOTING] 🗺️ Votação de mapa criada: {', '.join(sorteados)}")

	# -------------------------
	# ATUALIZA PAINEL MAPA
	# -------------------------
	async def _atualizar_painel_config_mapa(self, data=None):
		if data is None:
			data = await load_json_async(VOTACOES_FILE, default={"votacoes": [], "historico_mapas": []})
		canal = self.bot.get_channel(VOTACAO_CONFIG_CANAL_ID)
		if not canal or not data.get("config_mapa_msg_id"):
			return
		try:
			msg = await canal.fetch_message(data["config_mapa_msg_id"])
			await msg.edit(embed=self._embed_painel_mapa(data))
		except discord.NotFound:
			pass

	# -------------------------
	# EMBED PAINEL MAPA
	# -------------------------
	def _embed_painel_mapa(self, data):
		import datetime
		historico = data.get("historico_mapas", [])
		bloqueados = historico[-2:] if len(historico) >= 2 else historico
		ativa = next((v for v in data.get("votacoes", []) if not v.get("encerrada") and v.get("tipo") == "mapa"), None)

		now_brt = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
		dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
		meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
		data_str = f"{dias_semana[now_brt.weekday()]}, {now_brt.day} de {meses[now_brt.month - 1]}. de {now_brt.year}"
		hora_str = now_brt.strftime("%H:%M")

		embed = discord.Embed(
			title="🗺️ Mapa Rotativo Semanal",
			description=(
				"Todo **domingo à meia-noite**, o servidor troca de mapa — e quem decide isso é a **comunidade**."
				" Simples assim.\n\n"
				"**Como o ciclo funciona:**\n"
				"• Na **segunda-feira**, o bot acorda e já sorteia **4 mapas** pra briga + o mapa atual, que sempre tá na lista\n"
				"• O mapa anterior fica bloqueado do sorteio pra garantir que não fique repetindo\n"
				"• A galera vota de **segunda a sábado** — 1 voto por pessoa, sem segunda chance\n"
				"• **Domingo é dia de aplicar** o vencedor no servidor. Votou, ganhou, entrou\n"
				"• Aí já era, semana que vem começa tudo de novo\n\n"
				"⚙️ *O bot gerencia tudo sozinho. Os botões aqui são pra adm usar só quando necessário.*"
			),
			color=discord.Color.dark_green()
		)
		embed.set_footer(text=f"Votação: Segunda → Sábado  •  Domingo: aplicação no servidor  •  Atualizado às {hora_str}")

		if ativa:
			now_ts = time.time()
			fim = ativa["criada_em"] + ativa["duracao"]
			restante = max(0, int(fim - now_ts))
			h = restante // 3600
			m = (restante % 3600) // 60
			total_votos = len(ativa.get("votos", {}))
			embed.add_field(name="🟢 Status", value="Votação ativa", inline=True)
			embed.add_field(name="📅 Hoje", value=data_str, inline=True)
			embed.add_field(name="⏱️ Encerra em", value=f"{h}h {m}m", inline=True)
			embed.add_field(name="🗳️ Votos registrados", value=str(total_votos), inline=True)
			embed.add_field(name="🕐 Última atualização", value=hora_str, inline=True)
			embed.add_field(name="\u200b", value="\u200b", inline=True)
			embed.add_field(name="🗺️ Mapas em disputa", value="\n".join(f"• {op}" for op in ativa["opcoes"]), inline=False)
		else:
			embed.add_field(name="🔴 Status", value="Sem votação ativa", inline=True)
			embed.add_field(name="📅 Hoje", value=data_str, inline=True)
			embed.add_field(name="🕐 Última atualização", value=hora_str, inline=True)
			embed.add_field(name="🚫 Bloqueados (próx. sorteio)", value="\n".join(f"• {m}" for m in bloqueados) if bloqueados else "Nenhum", inline=False)

		if historico:
			embed.add_field(
				name="🏆 Últimos vencedores",
				value="\n".join(f"`{i+1}.` {m}" for i, m in enumerate(reversed(historico[-5:]))),
				inline=False
			)

			contagem = Counter(historico)
			top3 = contagem.most_common(3)
			if top3:
				destaque_idx = random.randint(0, len(top3) - 1)
				medalhas = ["🥇", "🥈", "🥉"]
				linhas_top3 = "\n".join(
					f"{medalhas[i]} **{m}** — {c} vitória(s)" + (" ✨ *Destaque*" if i == destaque_idx else "")
					for i, (m, c) in enumerate(top3)
				)
				embed.add_field(name="⭐ Top 3 Favoritos da Comunidade", value=linhas_top3, inline=False)
		return embed

	# -------------------------
	# VENCEDOR MAPA
	# -------------------------
	async def _registrar_vencedor_mapa(self, votacao, data):
		"""Se for votação de mapa, salva o vencedor no histórico."""
		if votacao.get("tipo") != "mapa":
			return
		votos = votacao.get("votos", {})
		opcoes = votacao.get("opcoes", [])
		if not votos or not opcoes:
			return
		cont = Counter(votos.values())
		idx_vencedor = cont.most_common(1)[0][0]
		vencedor = opcoes[idx_vencedor]
		historico = data.setdefault("historico_mapas", [])
		historico.append(vencedor)
		# Mantém histórico dos últimos 10 para não crescer indefinidamente
		data["historico_mapas"] = historico[-10:]
		data["mapa_corrente"] = vencedor
		print(f"[VOTING] 🗺️ Mapa vencedor registrado no histórico: {vencedor}")

	# -------------------------
	# PUBLICAÇÃO
	# -------------------------
	async def publicar_votacao(self, votacao):
		canal = self.bot.get_channel(VOTACAO_CANAL_ID)
		if not canal:
			return

		msg = await canal.send(
			embed=self.criar_embed(votacao),
			view=VotingPanelView(self.bot, votacao["id"], votacao["opcoes"])
		)

		data = await load_json_async(VOTACOES_FILE, {"votacoes": []})

		for v in data["votacoes"]:
			if v["id"] == votacao["id"]:
				v["mensagem_id"] = msg.id

		async with SAVE_LOCK:
			await save_json_async(VOTACOES_FILE, data)

	# -------------------------
	# UPDATE
	# -------------------------
	async def atualizar_painel_votacao(self, votacao):
		if not votacao.get("mensagem_id"):
			return

		canal = self.bot.get_channel(VOTACAO_CANAL_ID)
		if not canal:
			return

		encerrada = votacao.get("encerrada") or (time.time() >= votacao["criada_em"] + votacao["duracao"])

		msg = None
		if votacao.get("mensagem_id"):
			try:
				msg = await canal.fetch_message(votacao["mensagem_id"])
			except discord.NotFound:
				msg = None  # Mensagem foi deletada — vai repostar abaixo

		if msg is None and not encerrada:
			# Repost: canal foi limpo ou mensagem deletada
			msg = await canal.send(
				embed=self.criar_embed(votacao),
				view=VotingPanelView(self.bot, votacao["id"], votacao["opcoes"])
			)
			# Atualiza o mensagem_id no JSON
			data = await load_json_async(VOTACOES_FILE, {"votacoes": []})
			for v in data["votacoes"]:
				if v["id"] == votacao["id"]:
					v["mensagem_id"] = msg.id
					votacao["mensagem_id"] = msg.id
			async with SAVE_LOCK:
				await save_json_async(VOTACOES_FILE, data)
			return

		if msg:
			await msg.edit(
				embed=self.criar_embed(votacao),
				view=None if encerrada else VotingPanelView(self.bot, votacao["id"], votacao["opcoes"])
			)

	# -------------------------
	# EMBED
	# -------------------------
	def criar_embed(self, v):
		now = time.time()
		fim = v["criada_em"] + v["duracao"]
		restante = max(0, int(fim - now))

		votos = v.get("votos", {})
		opcoes = v.get("opcoes", [])
		total = len(votos)
		cont = Counter(votos.values())

		encerrada = v.get("encerrada") or restante <= 0

		if encerrada:
			# Embed de resultado final
			linhas = ""
			for i, op in enumerate(opcoes):
				qtd = cont.get(i, 0)
				pct = int((qtd / total) * 100) if total > 0 else 0
				barra = "█" * (pct // 10) + "░" * (10 - pct // 10)
				vencedor = cont and cont.most_common(1)[0][0] == i and total > 0
				prefixo = "🏆 " if vencedor else "▫️ "
				linhas += f"{prefixo}**{op}**\n`{barra}` {qtd} voto(s) — {pct}%\n\n"

			ganhador = opcoes[cont.most_common(1)[0][0]] if cont and total > 0 else None

			embed = discord.Embed(
				title=f"🏁 {v['titulo']}",
				description=linhas or "Nenhum voto registrado.",
				color=discord.Color.red()
			)
			if v.get("detalhes"):
				embed.add_field(name="📋 Detalhes", value=v["detalhes"], inline=False)
			embed.add_field(name="🏆 Vencedor", value=ganhador or "Sem votos", inline=True)
			embed.add_field(name="🗳️ Total de votos", value=str(total), inline=True)
			embed.set_footer(text="Votação encerrada")
			return embed

		# Embed de votação ativa
		horas = restante // 3600
		minutos = (restante % 3600) // 60
		segundos = restante % 60
		if horas > 0:
			tempo_str = f"{horas}h {minutos}m"
		elif minutos > 0:
			tempo_str = f"{minutos}m {segundos}s"
		else:
			tempo_str = f"{segundos}s"

		linhas = ""
		for i, op in enumerate(opcoes):
			qtd = cont.get(i, 0)
			pct = int((qtd / total) * 100) if total > 0 else 0
			barra = "█" * (pct // 10) + "░" * (10 - pct // 10)
			linhas += f"**{op}**\n`{barra}` {qtd} voto(s) — {pct}%\n\n"

		embed = discord.Embed(
			title=f"📊 {v['titulo']}",
			description=linhas,
			color=discord.Color.green()
		)
		if v.get("detalhes"):
			embed.add_field(name="📋 Detalhes", value=v["detalhes"], inline=False)
		embed.add_field(name="⏱️ Tempo restante", value=tempo_str, inline=True)
		embed.add_field(name="🗳️ Total de votos", value=str(total), inline=True)
		embed.set_footer(text="Clique em um botão abaixo para votar • Apenas 1 voto por pessoa")
		return embed


# =========================
# VIEWS VOTO
# =========================
class VotingPanelView(ui.View):
	def __init__(self, bot, vid, opcoes):
		super().__init__(timeout=None)
		self.bot = bot

		for i, o in enumerate(opcoes):
			self.add_item(VoteButton(bot, vid, i, o))


class VoteButton(ui.Button):
	def __init__(self, bot, vid, idx, label):
		super().__init__(label=label, style=ButtonStyle.secondary, custom_id=f"vote:{vid}:{idx}")
		self.bot = bot
		self.vid = vid
		self.idx = idx

	async def callback(self, interaction: Interaction):
		data = await load_json_async(VOTACOES_FILE, {"votacoes": []})
		votacao = next((v for v in data["votacoes"] if v["id"] == self.vid), None)

		if not votacao or votacao.get("encerrada"):
			return await interaction.response.send_message("Encerrada.", ephemeral=True)

		# Bloqueia votos de mapa no domingo (dia de aplicação)
		if votacao.get("tipo") == "mapa":
			import datetime
			now_brt = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
			if now_brt.weekday() == 6:
				return await interaction.response.send_message(
					"🗓️ Domingo é o dia de aplicação do mapa no servidor!\nA votação está encerrada hoje. Volte na próxima segunda-feira.",
					ephemeral=True
				)

		if str(interaction.user.id) in votacao["votos"]:
			return await interaction.response.send_message("Já votou.", ephemeral=True)

		votacao["votos"][str(interaction.user.id)] = self.idx

		async with SAVE_LOCK:
			await save_json_async(VOTACOES_FILE, data)

		# Concede XP simbólico por participar da votação
		xp_cog = self.bot.get_cog("XPCog")
		if xp_cog and interaction.guild:
			member = interaction.guild.get_member(interaction.user.id)
			if member:
				try:
					await xp_cog.add_xp_and_check_level(member, 1000, source="vote")
				except Exception:
					pass

		await interaction.response.send_message("✅ Voto registrado! (+1.000 XP)", ephemeral=True)
		await self.bot.get_cog("Voting").atualizar_painel_votacao(votacao)


async def setup(bot):
	await bot.add_cog(Voting(bot))