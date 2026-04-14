# cogs/ark.py - REFATORADO
# Integração RCON + controle de serviços para ARK: Survival Evolved
# Versão simplificada e funcional

import asyncio
import discord
import os
import json
import random
import string
import re
from discord.ext import commands
from datetime import datetime
from typing import Optional

import config
from utils import get_monitor, parse_rcon_listplayers, get_ark_state

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────────────────────

TIMEOUT_RCON = 20  # ⚡ Timeout curto - detecta bloqueios rápido
TIMEOUT_SYSTEMCTL = 30
CONFIRM_TIMEOUT = 30
RCON_MAX_RETRIES = 2
CRASH_DETECTION_TIMEOUT = 300  # 5 minutos sem resposta RCON = crash
MONITOR_CYCLE_SECONDS = 30  # Verifica presença a cada 30s

LINKS_DB = os.path.join(os.path.dirname(__file__), "..", "ark_links.json")
PAINEL_DB = os.path.join(os.path.dirname(__file__), "..", "painel_links.json")

# Cache para evitar carga repetida de JSON
_links_cache = None
_painel_cache = None

# ─────────────────────────────────────────────────────────────
# GERENCIAMENTO DE JSON COM CACHE
# ─────────────────────────────────────────────────────────────

def _ensure_dir(filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

def load_links():
    global _links_cache
    if _links_cache is not None:
        return _links_cache
    
    try:
        with open(LINKS_DB, "r", encoding="utf-8") as f:
            _links_cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _links_cache = {}
    return _links_cache

def save_links(links=None):
    global _links_cache
    if links is None:
        links = _links_cache or {}
    _links_cache = links
    _ensure_dir(LINKS_DB)
    with open(LINKS_DB, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)

def clear_links_cache():
    global _links_cache
    _links_cache = None

def load_painel():
    global _painel_cache
    if _painel_cache is not None:
        return _painel_cache
    
    try:
        with open(PAINEL_DB, "r", encoding="utf-8") as f:
            _painel_cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _painel_cache = {}
    return _painel_cache

def save_painel(data=None):
    global _painel_cache
    if data is None:
        data = _painel_cache or {}
    _painel_cache = data
    _ensure_dir(PAINEL_DB)
    with open(PAINEL_DB, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def generate_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def resolve_map(name_input: str) -> dict | None:
    """Encontra mapa por nome ou alias."""
    key = name_input.lower()
    if key in config.ARK_MAPS:
        return config.ARK_MAPS[key]
    for k, v in config.ARK_MAPS.items():
        if key in k or key in v.get("aliases", []):
            return v
    return None

def get_map_list_text() -> str:
    """Lista de mapas disponíveis em formato legível."""
    if not config.ARK_MAPS:
        return "_Nenhum mapa configurado_"
    return ", ".join(f"`{v['name']}`" for v in config.ARK_MAPS.values())

async def rcon_run(host: str, port: int, password: str, cmd: str, retry: int = RCON_MAX_RETRIES) -> str:
    """Executa comando RCON via rcon.source.Client."""
    from rcon.source import Client

    socket_timeout = 15
    last_error: Exception | None = None

    for attempt in range(1, retry + 2):
        try:
            print(f"[RCON] Tentando {host}:{port} (tentativa {attempt})")

            def _execute_rcon(h=host, p=port, pw=password, c=cmd, t=socket_timeout):
                try:
                    with Client(host=h, port=p, passwd=pw, timeout=t) as client:
                        print(f"[RCON]   ✅ Conectado! Enviando: {c}")
                        response = client.run(c)
                        print(f"[RCON]   ✅ Sucesso! {len(response)} bytes")
                        return response
                except Exception as e:
                    print(f"[RCON]   ❌ {type(e).__name__}: {str(e)[:100]}")
                    raise

            result = await asyncio.wait_for(
                asyncio.to_thread(_execute_rcon),
                timeout=socket_timeout + 5
            )
            return result

        except asyncio.TimeoutError:
            print(f"[RCON] ⏱️ Timeout em {host}:{port}")
            last_error = TimeoutError(f"Timeout em {host}:{port}")
            await asyncio.sleep(1)

        except Exception as e:
            print(f"[RCON] ❌ Erro: {str(e)[:100]}")
            last_error = e
            await asyncio.sleep(1)

    raise last_error or Exception(f"RCON falhou em {host}:{port}")

async def systemctl_run(action: str, service: str) -> tuple[int, str, str]:
    """Executa systemctl comando."""
    proc = await asyncio.create_subprocess_exec(
        "systemctl", action, service,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SYSTEMCTL)
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", "Timeout"
    return proc.returncode or 0, stdout.decode().strip(), stderr.decode().strip()

def format_player_name(raw_line: str) -> str:
    """Converte linha RCON do jogador para nome e SteamID."""
    links = load_links()
    
    match = re.search(r"SteamID:\s*(\d+)", raw_line)
    if not match:
        return raw_line
    
    steam_id = match.group(1)
    
    # Busca personagem vinculado
    for link_data in links.values():
        if link_data.get("steam_id") == steam_id and link_data.get("personagem"):
            return f"**{link_data['personagem']}** (SteamID: {steam_id})"
    
    # Fallback: extrai nome Steam
    name_match = re.search(r"Name:\s*([^,]+)", raw_line)
    return f"{name_match.group(1).strip()} (SteamID: {steam_id})" if name_match else raw_line

# ─────────────────────────────────────────────────────────────
# HELPERS PARA STEAM
# ─────────────────────────────────────────────────────────────

def extract_steamid_from_url(url: str) -> str | None:
    """Extrai SteamID64 de uma URL Steam.
    
    Exemplos:
    - https://steamcommunity.com/profiles/76561198123456789 → 76561198123456789
    - https://steamcommunity.com/id/mynickname → Não funciona (precisa de perfil numérico)
    """
    # Busca padrão: /profiles/XXXXX  
    match = re.search(r"/profiles/(\d{17})", url)
    return match.group(1) if match else None

def validate_steamid(steamid: str) -> bool:
    """Valida se é um SteamID válido (17 dígitos)."""
    return len(steamid) == 17 and steamid.isdigit()

# ─────────────────────────────────────────────────────────────
# VIEWS (UI) - MODAIS + BOTÕES
# ─────────────────────────────────────────────────────────────

class VincularModal(discord.ui.Modal, title="🔗 Vincular ao Discord"):
    """Modal simples pedindo apenas o Steam URL ou SteamID."""
    
    steam_input = discord.ui.TextInput(
        label="🔗 Cole aqui seu link Steam",
        placeholder="https://steamcommunity.com/profiles/76561198123456789",
        style=discord.TextStyle.short,
        required=True,
    )
    
    personagem_input = discord.ui.TextInput(
        label="🦕 Nome do Personagem (opcional)",
        placeholder="Meu Rex",
        style=discord.TextStyle.short,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        steam_input = self.steam_input.value.strip()
        personagem = self.personagem_input.value.strip() or None
        
        # Tenta extrair SteamID da URL
        steamid = extract_steamid_from_url(steam_input) or (
            steam_input if validate_steamid(steam_input) else None
        )
        
        if not steamid or not validate_steamid(steamid):
            await interaction.response.send_message(
                f"❌ SteamID inválido!\n\n"
                f"**Cole um dos formatos:**\n"
                f"• Link completo: `https://steamcommunity.com/profiles/76561198123456789`\n"
                f"• Apenas o ID: `76561198123456789` (17 dígitos)",
                ephemeral=True
            )
            return
        
        # Carrega vinculações existentes
        links = load_links()
        discord_id = str(interaction.user.id)
        
        # NOVO: Verifica se JÁ está vinculado
        if discord_id in links:
            vínculo_anterior = links[discord_id]
            await interaction.response.send_message(
                f"⚠️ **Você já está vinculado!**\n\n"
                f"**Vínculo atual:**\n"
                f"🎮 SteamID: `{vínculo_anterior['steam_id']}`\n"
                f"🦕 Personagem: {vínculo_anterior.get('personagem', 'Não informado')}\n\n"
                f"**Para trocar de conta, contate um administrador.**",
                ephemeral=True
            )
            return
        
        # Cria nova vinculação (somente se não existe)
        links[discord_id] = {
            "discord_id": discord_id,
            "discord_name": interaction.user.name,
            "steam_id": steamid,
            "personagem": personagem,
            "timestamp": str(datetime.now())
        }
        save_links(links)
        
        # Resposta de sucesso
        embed = discord.Embed(
            title="✅ Vinculado com Sucesso!",
            description=f"Você agora está vinculado ao ARK",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Discord", value=f"<@{interaction.user.id}>", inline=True)
        embed.add_field(name="🎮 SteamID", value=f"`{steamid}`", inline=True)
        if personagem:
            embed.add_field(name="🦕 Personagem", value=personagem, inline=True)
        embed.set_footer(text="Você pode jogar agora!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ConfirmView(discord.ui.View):
    def __init__(self, author: discord.abc.User, *, timeout: float = CONFIRM_TIMEOUT):
        super().__init__(timeout=timeout)
        self.author = author
        self.confirmed = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ Somente você pode confirmar.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self.stop()
        await interaction.response.defer()


class PainelVincularView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🔗 Vincular Agora", style=discord.ButtonStyle.green, custom_id="painel_vincular_btn")
    async def vincular_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Abre o modal ao invés de gerar código
        await interaction.response.send_modal(VincularModal())

    @discord.ui.button(label="❓ Ajuda", style=discord.ButtonStyle.primary, custom_id="painel_ajuda_btn")
    async def ajuda_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❓ Como Funciona?",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="1️⃣ Clique em 'Vincular Agora'",
            value="Um formulário irá aparecer",
            inline=False
        )
        embed.add_field(
            name="2️⃣ Cole seu Link Steam",
            value="Copie de: https://steamcommunity.com/profiles/XXXX",
            inline=False
        )
        embed.add_field(
            name="3️⃣ (Opcional) Seu Personagem",
            value="Digite o nome do seu dino/personagem no jogo",
            inline=False
        )
        embed.add_field(
            name="4️⃣ Pronto!",
            value="Você está vinculado e pode jogar!",
            inline=False
        )
        embed.set_footer(text="Processo simples e rápido!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ─────────────────────────────────────────────────────────────
# PAINEL DE CONTROLE (NOVO)
# ─────────────────────────────────────────────────────────────

class ServidorSelect(discord.ui.Select):
    """Dropdown para selecionar servidor"""
    
    def __init__(self):
        options = []
        for key, info in config.ARK_MAPS.items():
            options.append(
                discord.SelectOption(
                    label=info["name"],
                    value=key,
                    emoji="🗺️"
                )
            )
        
        super().__init__(
            placeholder="Selecione um servidor...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="servidor_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Apenas para selecionar, a ação é feita pelos botões
        await interaction.response.defer()


class PainelControlView(discord.ui.View):
    """Painel principal de controle com dropdown + botões de ação"""
    
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.selected_server = None
        
        # Adiciona o dropdown
        self.add_item(ServidorSelect())
    
    def _get_selected_server(self, interaction: discord.Interaction) -> Optional[dict]:
        """Extrai servidor selecionado do dropdown"""
        for item in self.children:
            if isinstance(item, ServidorSelect):
                if item.values:
                    server_key = item.values[0]
                    return config.ARK_MAPS.get(server_key)
        return None
    
    @discord.ui.button(label="⚡ Ligar", style=discord.ButtonStyle.green, custom_id="painel_start")
    async def start_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        
        info = self._get_selected_server(interaction)
        if not info:
            await interaction.followup.send("❌ Selecione um servidor primeiro!", ephemeral=True)
            return
        
        msg = await interaction.followup.send("🔄 Iniciando servidor...")
        if not msg:
            return
        
        rc, out, err = await systemctl_run("start", info["service"])
        
        embed = discord.Embed(
            title=f"⚡ {info['name']} — {'OK' if rc == 0 else 'ERRO'}",
            description=f"Serviço: `{info['service']}`",
            color=discord.Color.green() if rc == 0 else discord.Color.red(),
            timestamp=datetime.now()
        )
        
        if rc != 0:
            embed.add_field(name="Erro", value=f"```{(err or out or 'Desconhecido')[:500]}```", inline=False)
        else:
            embed.add_field(name="Status", value="✅ Servidor iniciado com sucesso!", inline=False)
        
        embed.set_footer(text=f"Por {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await msg.edit(embed=embed)  # type: ignore
    
    @discord.ui.button(label="🔴 Desligar", style=discord.ButtonStyle.red, custom_id="painel_stop")
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        info = self._get_selected_server(interaction)
        if not info:
            await interaction.response.send_message("❌ Selecione um servidor primeiro!", ephemeral=True)
            return
        
        # Confirmação
        embed = discord.Embed(
            title="⚠️ Confirmar Desligamento",
            description=f"Desligar **{info['name']}**?\n(será feito save antes)",
            color=discord.Color.red()
        )
        
        view = ConfirmView(interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        await view.wait()
        
        if not view.confirmed:
            return
        
        # Executa
        try:
            await rcon_run(info["host"], info["port"], info["password"], "SaveWorld")
            await asyncio.sleep(2)
        except:
            pass
        
        msg = await interaction.followup.send("🔄 Desligando...")
        if not msg:
            return
        rc, out, err = await systemctl_run("stop", info["service"])
        
        embed = discord.Embed(
            title=f"🔴 {info['name']} — {'OK' if rc == 0 else 'ERRO'}",
            color=discord.Color.red() if rc == 0 else discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Status", value="✅ Servidor desligado!" if rc == 0 else f"⚠️ Erro: {err[:200]}", inline=False)
        
        await msg.edit(embed=embed)  # type: ignore
    
    @discord.ui.button(label="🔁 Reiniciar", style=discord.ButtonStyle.primary, custom_id="painel_restart")
    async def restart_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        info = self._get_selected_server(interaction)
        if not info:
            await interaction.response.send_message("❌ Selecione um servidor primeiro!", ephemeral=True)
            return
        
        # Confirmação
        embed = discord.Embed(
            title="⚠️ Confirmar Reinicialização",
            description=f"Reiniciar **{info['name']}**?",
            color=discord.Color.orange()
        )
        
        view = ConfirmView(interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        await view.wait()
        
        if not view.confirmed:
            return
        
        # Executa
        try:
            await rcon_run(info["host"], info["port"], info["password"], "broadcast RESTART")
            await asyncio.sleep(3)
        except:
            pass
        
        msg = await interaction.followup.send("🔄 Reiniciando...")
        if not msg:
            return
        rc, out, err = await systemctl_run("restart", info["service"])
        
        embed = discord.Embed(
            title=f"🔁 {info['name']} — {'OK' if rc == 0 else 'ERRO'}",
            color=discord.Color.green() if rc == 0 else discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Status", value="✅ Servidor reiniciado!" if rc == 0 else f"⚠️ Erro: {err[:200]}", inline=False)
        
        await msg.edit(embed=embed)  # type: ignore
    
    @discord.ui.button(label="👁️ Status", style=discord.ButtonStyle.blurple, custom_id="painel_status")
    async def status_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        
        info = self._get_selected_server(interaction)
        if not info:
            await interaction.followup.send("❌ Selecione um servidor primeiro!", ephemeral=True)
            return
        
        msg_initial = await interaction.followup.send("🔄 Consultando status...")
        assert msg_initial is not None, "followup.send() retornou None"
        
        try:
            response = await asyncio.wait_for(
                rcon_run(info["host"], info["port"], info["password"], "listplayers"),
                timeout=TIMEOUT_RCON
            )
        except asyncio.TimeoutError:
            await msg_initial.edit(content=f"⏱️ Timeout — {info['name']} pode estar offline")  # type: ignore
            return
        except Exception as e:
            await msg_initial.edit(content=f"❌ Erro: {e}")  # type: ignore
            return
        
        embed = discord.Embed(
            title=f"👁️ {info['name']}",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        raw = response.strip()
        if not raw or "No Players" in raw:
            raw_players = "0"
            player_info = "_Ninguém online_"
        else:
            lines = [l.strip() for l in raw.splitlines() if l.strip()]
            raw_players = str(len(lines))
            player_info = "\n".join(f"• {format_player_name(l)}" for l in lines[:10])  # Máx 10
            if len(lines) > 10:
                player_info += f"\n... e +{len(lines) - 10} outros"
        
        embed.add_field(name="👥 Jogadores Online", value=f"**{raw_players}**", inline=True)
        embed.add_field(name="📋 Lista", value=player_info, inline=False)
        
        await msg_initial.edit(embed=embed)  # type: ignore
    
    @discord.ui.button(label="👥 Jogadores", style=discord.ButtonStyle.secondary, custom_id="painel_players")
    async def players_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        
        info = self._get_selected_server(interaction)
        if not info:
            await interaction.followup.send("❌ Selecione um servidor primeiro!", ephemeral=True)
            return
        
        msg_initial = await interaction.followup.send("🔄 Consultando jogadores...")
        assert msg_initial is not None, "followup.send() retornou None"
        
        try:
            response = await asyncio.wait_for(
                rcon_run(info["host"], info["port"], info["password"], "listplayers"),
                timeout=TIMEOUT_RCON
            )
        except asyncio.TimeoutError:
            await msg_initial.edit(content=f"⏱️ Timeout")  # type: ignore
            return
        except Exception as e:
            await msg_initial.edit(content=f"❌ Erro: {e}")  # type: ignore
            return
        
        embed = discord.Embed(
            title=f"👥 Jogadores - {info['name']}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        raw = response.strip()
        if not raw or "No Players" in raw:
            embed.description = "_Ninguém online_"
        else:
            lines = [l.strip() for l in raw.splitlines() if l.strip()]
            embed.description = "\n".join(f"• {format_player_name(l)}" for l in lines)
            embed.set_author(name=f"{len(lines)} jogador(es) online")
        
        await msg_initial.edit(embed=embed)  # type: ignore

class PainelStatusView(discord.ui.View):
    """Painel menor só com botões de status"""
    
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="🔄 Atualizar Status", style=discord.ButtonStyle.blurple, custom_id="painel_status_all")
    async def status_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        
        msg = await interaction.followup.send("🔄 Verificando todos os servidores... (até 30s)")
        if msg is None:
            return
        
        embed = discord.Embed(title="🦕 Status ARK", color=discord.Color.green(), timestamp=datetime.now())
        
        async def check_map(info):
            try:
                response = await asyncio.wait_for(
                    rcon_run(info["host"], info["port"], info["password"], "listplayers"),
                    timeout=TIMEOUT_RCON
                )
                return info["name"], True, response.strip(), None
            except asyncio.TimeoutError:
                return info["name"], False, "", "⏱️ Timeout"
            except Exception as e:
                return info["name"], False, "", f"❌ Erro"
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[check_map(t) for t in config.ARK_MAPS.values()], return_exceptions=False),
                timeout=300
            )
        except asyncio.TimeoutError:
            results = [(info["name"], False, "", "⏱️ Timeout global") for info in config.ARK_MAPS.values()]
        
        for name, online, data, error in results:
            if online:
                if "No Players" in data or not data:
                    num = "0"
                else:
                    num = str(len([l for l in data.splitlines() if l.strip()]))
                embed.add_field(name=f"🟢 {name}", value=f"**Online** ({num} 👥)", inline=False)
            else:
                embed.add_field(name=f"🔴 {name}", value=error or "**Offline**", inline=False)
        
        if any(not ok for _, ok, _, _ in results):
            embed.color = discord.Color.orange() if any(ok for _, ok, _, _ in results) else discord.Color.red()
        
        await msg.edit(embed=embed)  # type: ignore

# ─────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────

class ArkCog(commands.Cog, name="ARK RCON"):
    """Controle de Servidores ARK via RCON + Systemctl"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.monitor = get_monitor()  # Inicializa monitor
        self.ark_state = get_ark_state()  # Estado compartilhado com rcon_monitor
        self.monitor_task = None  # Task de monitoramento contínuo
        self._monitoring_active = False

    async def cog_load(self) -> None:
        """Chamado quando o cog é carregado"""
        # Inicia monitoramento contínuo
        if not self._monitoring_active:
            self._monitoring_active = True
            self.monitor_task = asyncio.create_task(self._monitor_players_loop())
            print("[ARK] 🔍 Monitor de jogadores iniciado!")

    async def _monitor_players_loop(self):
        """
        Background task que monitora presença de jogadores continuamente.
        Executa a cada MONITOR_CYCLE_SECONDS segundos.
        """
        print("[Monitor] 🚀 Loop de monitoramento iniciado")
        await asyncio.sleep(5)  # Aguarda boot completo
        
        while self._monitoring_active:
            try:
                for map_key, info in config.ARK_MAPS.items():
                    try:
                        # Tenta consultar listplayers
                        response = await asyncio.wait_for(
                            rcon_run(info["host"], info["port"], info["password"], "listplayers"),
                            timeout=TIMEOUT_RCON
                        )
                        
                        # Parse e atualiza monitor
                        players = parse_rcon_listplayers(response)
                        player_names = [name for _, name in players]
                        
                        # Marca como online
                        for steam_id, name in players:
                            self.monitor.update_player_presence(steam_id, info["name"], online=True)
                        
                        # Detecta crashes (players que sumiram)
                        crashed = self.monitor.get_crashed_players(info["name"], CRASH_DETECTION_TIMEOUT)
                        if crashed:
                            print(f"[Monitor] ⚠️ {len(crashed)} crash(es) detectado(s) em {info['name']}")
                        
                        # Atualiza estado compartilhado com rcon_monitor
                        self.ark_state.update_server_status(
                            info["name"], is_online=True,
                            player_count=len(players), online_players=player_names
                        )
                        print(f"[Monitor] ✅ {info['name']}: {len(players)} online")
                        
                    except asyncio.TimeoutError:
                        print(f"[Monitor] ⏱️ Timeout em {info['name']} - RCON provavelmente offline")
                        self.ark_state.update_server_status(info["name"], is_online=False)
                    except Exception as e:
                        print(f"[Monitor] ❌ Erro em {info['name']}: {str(e)[:100]}")
                        self.ark_state.update_server_status(info["name"], is_online=False)
                
                # Aguarda até próximo ciclo
                await asyncio.sleep(MONITOR_CYCLE_SECONDS)
                
            except Exception as e:
                print(f"[Monitor] ❌ Erro no loop: {e}")
                await asyncio.sleep(5)

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(PainelVincularView(self.bot))

    async def cog_check(self, ctx: commands.Context) -> bool:
        """Bloqueia comandos fora do canal ARK, exceto: setup*, finaliza*, buscar*, consultar*"""
        allowed_anywhere = [
            "setuppainel", "finalizavinculo", "buscarsteamid", "buscarvinculo",
            "consultarvinculo", "removervinculo", "editarvinculo", "listarvincculos"
        ]
        
        if ctx.command and ctx.command.name in allowed_anywhere:
            return True
        
        if ctx.channel.id != config.ARK_CANAL_RCON_ID:
            try:
                await ctx.message.delete()
            except:
                pass
            canal = ctx.guild and ctx.guild.get_channel(config.ARK_CANAL_RCON_ID)
            mencao = canal.mention if canal else f"<#{config.ARK_CANAL_RCON_ID}>"
            await ctx.send(f"🔒 Use {mencao}", delete_after=8)
            return False

        if not ctx.author.guild_permissions.administrator:  # type: ignore
            try:
                await ctx.message.delete()
            except:
                pass
            await ctx.send("🔒 Admin only", delete_after=8)
            return False

        return True

    # ───────────────────────────────────────────────────────────
    # VINCULAÇÃO
    # ───────────────────────────────────────────────────────────

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setuppainel(self, ctx: commands.Context, channel_id: Optional[int] = None):
        """Cria painel de vinculação."""
        if channel_id is None:
            channel_id = ctx.channel.id  # type: ignore
        
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            await ctx.send("❌ Canal inválido")
            return
        
        embed = discord.Embed(
            title="🔗 Painel de Vinculação ARK",
            description="Clique para vincular sua conta Discord com o ARK/Steam em **segundos**",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="✨ Processo Rápido",
            value=(
                "1. 🔗 Clique em **Vincular Agora**\n"
                "2. 📋 Cole seu Link Steam\n"
                "3. ✅ Pronto! Está vinculado!"
            ),
            inline=False
        )
        embed.set_footer(text="Leva menos de 30 segundos")
        
        msg = await channel.send(embed=embed, view=PainelVincularView(self.bot))
        
        painel = load_painel()
        painel["channel_id"] = channel_id
        painel["message_id"] = msg.id
        save_painel(painel)
        
        await ctx.send(f"✅ Painel criado em {channel.mention}")

    @commands.command()
    async def vincular(self, ctx: commands.Context, steam_link: Optional[str] = None):
        """Vincula sua conta Steam ao Discord.
        
        ⚡ Uso rápido:
            !vincular https://steamcommunity.com/profiles/76561198123456789
            !vincular 76561198123456789 (apenas o ID)
        
        Ou use o botão no painel para formulário interativo.
        """
        if steam_link is None:
            # Se não tiver link, mostra o modal
            await ctx.send(
                "📝 Abrindo formulário...",
                view=discord.ui.View().add_item(
                    discord.ui.Button(
                        label="Abrir Modal",
                        style=discord.ButtonStyle.blurple,
                        disabled=True
                    )
                )
            )
            await ctx.interaction.response.send_modal(VincularModal())  # type: ignore
            return
        
        # Parseia o link/ID
        steam_link = steam_link.strip()
        steamid = extract_steamid_from_url(steam_link) or (
            steam_link if validate_steamid(steam_link) else None
        )
        
        if not steamid or not validate_steamid(steamid):
            await ctx.send(
                f"❌ SteamID inválido!\n\n"
                f"**Cole um dos formatos:**\n"
                f"• Link completo: `https://steamcommunity.com/profiles/76561198123456789`\n"
                f"• Apenas o ID: `76561198123456789` (17 dígitos)",
                delete_after=15
            )
            return
        
        # Salva
        links = load_links()
        discord_id = str(ctx.author.id)
        links[discord_id] = {
            "discord_id": discord_id,
            "discord_name": ctx.author.name,
            "steam_id": steamid,
            "personagem": None,
            "timestamp": str(datetime.now())
        }
        save_links(links)
        
        embed = discord.Embed(
            title="✅ Vinculado!",
            description="Sua conta Steam está vinculada ao Discord",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Discord", value=f"<@{ctx.author.id}>", inline=True)
        embed.add_field(name="🎮 SteamID", value=f"`{steamid}`", inline=True)
        embed.set_footer(text="Você pode jogar agora!")
        
        await ctx.send(embed=embed, delete_after=30)

    @commands.command()
    async def meuvínculo(self, ctx: commands.Context):
        """Mostra suas informações de vinculação."""
        links = load_links()
        discord_id = str(ctx.author.id)
        
        if discord_id not in links:
            await ctx.send(
                "❌ Você ainda não está vinculado.\n"
                "Use o painel ou `!vincular SEU_STEAM_LINK` para vincular!",
                delete_after=15
            )
            return
        
        v = links[discord_id]
        embed = discord.Embed(title="🔗 Suas Informações", color=discord.Color.blue())
        embed.add_field(name="👤 Discord", value=f"<@{ctx.author.id}>")
        embed.add_field(name="🎮 SteamID", value=f"`{v.get('steam_id')}`")
        
        if v.get("personagem"):
            embed.add_field(name="🦕 Personagem", value=v.get("personagem"))
        
        if v.get("timestamp"):
            embed.add_field(name="📅 Vinculado em", value=v.get("timestamp"))
        
        await ctx.send(embed=embed, delete_after=30)

    @commands.command()
    async def atualizarpersonagem(self, ctx: commands.Context, *, nome_personagem: str):
        """Atualiza o nome do seu personagem no jogo."""
        links = load_links()
        discord_id = str(ctx.author.id)
        
        if discord_id not in links:
            await ctx.send("❌ Você não está vinculado primeiro!", delete_after=10)
            return
        
        links[discord_id]["personagem"] = nome_personagem
        save_links(links)
        
        await ctx.send(f"✅ Personagem atualizado para: **{nome_personagem}**", delete_after=20)

    @commands.command()
    async def removervinculo(self, ctx: commands.Context):
        """Remove sua vinculação."""
        links = load_links()
        discord_id = str(ctx.author.id)
        
        if discord_id not in links:
            await ctx.send("❌ Você não está vinculado", delete_after=10)
            return
        
        del links[discord_id]
        save_links(links)
        await ctx.send("✅ Vinculação removida", delete_after=10)

    # ───────────────────────────────────────────────────────────
    # SERVIDORES
    # ───────────────────────────────────────────────────────────

    @commands.command(aliases=["arkmaps", "arkservers"])
    @commands.has_permissions(administrator=True)
    async def arkmapas(self, ctx: commands.Context):
        """Lista mapas configurados."""
        if not config.ARK_MAPS:
            await ctx.send("❌ Nenhum mapa configurado")
            return

        embed = discord.Embed(title="🗺️ Mapas ARK", color=discord.Color.og_blurple())
        for _, info in config.ARK_MAPS.items():
            service_txt = f"`{info['service']}`" if info.get("service") else "_N/A_"
            embed.add_field(
                name=info["name"],
                value=(
                    f"→ `{info['host']}:{info['port']}`\n"
                    f"→ Serviço: {service_txt}"
                ),
                inline=True,
            )
        await ctx.send(embed=embed)

    async def _status_action(self, ctx: commands.Context, mapa_info: dict, action: str):
        """Helper genérico para ligar/desligar/reiniciar."""
        if not mapa_info.get("service"):
            await ctx.send(f"❌ Mapa não tem `service` configurado no `.env`")
            return

        # Confirmação para desligar/reiniciar
        if action in ["stop", "restart"]:
            colors = {"stop": discord.Color.red(), "restart": discord.Color.orange()}
            msgs = {
                "stop": "Desligar? (salvará o mundo antes)",
                "restart": "Reiniciar? (aviso + salvar + reiniciar)"
            }
            
            embed_confirm = discord.Embed(
                title=f"⚠️ {msgs[action]}",
                description=f"**{mapa_info['name']}** - `{mapa_info['service']}`",
                color=colors[action]
            )
            view = ConfirmView(ctx.author)
            msg = await ctx.send(embed=embed_confirm, view=view)
            
            await view.wait()
            for item in view.children:
                item.disabled = True  # type: ignore
            if not view.confirmed:
                await msg.edit(embed=discord.Embed(title="🚫 Cancelado", color=discord.Color.greyple()), view=view)
                return
        
        # Preparação (aviso + save para restart/stop)
        if action in ["stop", "restart"]:
            try:
                await asyncio.wait_for(
                    rcon_run(mapa_info["host"], mapa_info["port"], mapa_info["password"],
                             f"broadcast {action.upper()}" if action == "restart" else "SaveWorld"),
                    timeout=TIMEOUT_RCON + 2,
                )
                await asyncio.sleep(3)
            except:
                pass

        # Executa systemctl
        msg = await ctx.send(f"🔄 Processando **{mapa_info['name']}**...")
        rc, out, err = await systemctl_run(action, mapa_info["service"])

        colors = {"start": discord.Color.green(), "stop": discord.Color.red(), "restart": discord.Color.green()}
        icons = {"start": "⚡", "stop": "🔴", "restart": "🔁"}
        
        embed = discord.Embed(
            title=f"{icons[action]} {mapa_info['name']} — {'OK' if rc == 0 else 'ERRO'}",
            description=f"Serviço: `{mapa_info['service']}`",
            color=colors[action],
            timestamp=datetime.now()
        )
        
        if rc != 0:
            embed.add_field(name="Erro", value=f"```{(err or out or 'Desconhecido')[:500]}```", inline=False)
        
        embed.set_footer(text=f"Por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await msg.edit(content=None, embed=embed)

    @commands.command(aliases=["arkstart"])
    @commands.has_permissions(administrator=True)
    async def arkligar(self, ctx: commands.Context, *, mapa: str):
        """Liga um servidor. Ex: !arkligar fjordur"""
        info = resolve_map(mapa)
        if not info:
            await ctx.send(f"❌ Mapa `{mapa}` não encontrado. Opções: {get_map_list_text()}")
            return
        await self._status_action(ctx, info, "start")

    @commands.command(aliases=["arkstop", "arkparar"])
    @commands.has_permissions(administrator=True)
    async def arkdesligar(self, ctx: commands.Context, *, mapa: str):
        """Desliga um servidor. Ex: !arkdesligar fjordur"""
        info = resolve_map(mapa)
        if not info:
            await ctx.send(f"❌ Mapa `{mapa}` não encontrado. Opções: {get_map_list_text()}")
            return
        await self._status_action(ctx, info, "stop")

    @commands.command(aliases=["arkrestart", "arkreboot"])
    @commands.has_permissions(administrator=True)
    async def arkreinicia(self, ctx: commands.Context, *, mapa: str):
        """Reinicia um servidor. Ex: !arkreinicia fjordur"""
        info = resolve_map(mapa)
        if not info:
            await ctx.send(f"❌ Mapa `{mapa}` não encontrado. Opções: {get_map_list_text()}")
            return
        await self._status_action(ctx, info, "restart")

    @commands.command(aliases=["arkserver", "arkinfo"])
    async def arkstatus(self, ctx: commands.Context, mapa: Optional[str] = None):
        """Status de um ou todos os mapas. Ex: !arkstatus fjordur"""
        if not config.ARK_MAPS:
            await ctx.send("❌ Nenhum mapa configurado")
            return

        targets = [resolve_map(mapa)] if mapa else list(config.ARK_MAPS.values())
        if mapa and not targets[0]:
            await ctx.send(f"❌ Mapa não encontrado. Opções: {get_map_list_text()}")
            return

        msg = await ctx.send("🔄 Verificando servidores... (isso pode levar até 30 segundos)")
        embed = discord.Embed(title="🦕 Status ARK", color=discord.Color.green(), timestamp=datetime.now())

        async def check_map(info):
            """Checa status de um mapa"""
            try:
                # Timeout generoso para quando usuário pede manualmente
                response = await rcon_run(info["host"], info["port"], info["password"], "listplayers")
                return info["name"], True, response.strip(), None
            except asyncio.TimeoutError:
                return info["name"], False, "", f"⏱️ Timeout (servidor pode estar offline/sobrecarregado)"
            except Exception as e:
                error_msg = str(e)
                if any(x in error_msg for x in ["Connection refused", "refused", "connection"]):
                    return info["name"], False, "", "🔴 Servidor offline ou porta incorreta"
                elif "timeout" in error_msg.lower():
                    return info["name"], False, "", "⏱️ Timeout na conexão"
                else:
                    return info["name"], False, "", f"❌ {error_msg[:80]}"

        # Timeout GLOBAL para todo o gather (5 min para dar tempo)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[check_map(t) for t in targets], return_exceptions=False),
                timeout=300  # 5 minutos para TODOS os servidores
            )
        except asyncio.TimeoutError:
            results = [(info["name"], False, "", "⏱️ Verificação expirou (RCON offline?)") for info in targets]  # type: ignore

        for name, online, data, error in results:
            if online:
                if "No Players" in data or not data:
                    player_info = "_Sem jogadores_"
                    num = "0"
                else:
                    lines = [l.strip() for l in data.splitlines() if l.strip()]
                    player_info = "\n".join(f"• {format_player_name(l)}" for l in lines)
                    num = str(len(lines))
                embed.add_field(
                    name=f"🟢 {name}",
                    value=f"**Online** ({num} jogadores)\n{player_info}",
                    inline=False,
                )
            else:
                embed.add_field(name=f"🔴 {name}", value=error or "**Offline**", inline=False)

        if any(not ok for _, ok, _, _ in results):
            embed.color = discord.Color.orange() if any(ok for _, ok, _, _ in results) else discord.Color.red()

        await msg.edit(content=None, embed=embed)

    @commands.command(aliases=["arkjogadores", "arkwho"])
    @commands.has_permissions(administrator=True)
    async def arkplayers(self, ctx: commands.Context, *, mapa: str):
        """Lista jogadores conectados. Ex: !arkplayers fjordur"""
        info = resolve_map(mapa)
        if not info:
            await ctx.send(f"❌ Mapa não encontrado. Opções: {get_map_list_text()}")
            return

        msg = await ctx.send(f"🔄 Consultando {info['name']}...")

        try:
            response = await asyncio.wait_for(
                rcon_run(info["host"], info["port"], info["password"], "listplayers"),
                timeout=TIMEOUT_RCON + 2,
            )
        except asyncio.TimeoutError:
            await msg.edit(content=f"⏱️ Timeout — {info['name']} pode estar offline")
            return
        except Exception as e:
            await msg.edit(content=f"❌ Erro: `{e}`")
            return

        embed = discord.Embed(title=f"👥 {info['name']}", color=discord.Color.blue(), timestamp=datetime.now())

        raw = response.strip()
        if not raw or "No Players" in raw:
            embed.description = "_Ninguém online_"
        else:
            lines = [l.strip() for l in raw.splitlines() if l.strip()]
            embed.description = "\n".join(f"• {format_player_name(l)}" for l in lines)
            embed.set_author(name=f"{len(lines)} jogador(es)")

        await msg.edit(content=None, embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def rcon(self, ctx: commands.Context, mapa: str, *, comando: str):
        """Envia comando RCON. Ex: !rcon fjordur broadcast Olá!"""
        info = resolve_map(mapa)
        if not info:
            await ctx.send(f"❌ Mapa não encontrado. Opções: {get_map_list_text()}")
            return

        msg = await ctx.send(f"📡 Enviando para {info['name']}...")

        try:
            response = await asyncio.wait_for(
                rcon_run(info["host"], info["port"], info["password"], comando),
                timeout=TIMEOUT_RCON + 2,
            )
        except asyncio.TimeoutError:
            await msg.edit(content=f"⏱️ Timeout")
            return
        except Exception as e:
            await msg.edit(content=f"❌ Erro: `{e}`")
            return

        embed = discord.Embed(
            title=f"📟 RCON → {info['name']}",
            color=discord.Color.teal(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Comando", value=f"```{comando}```", inline=False)
        resposta = response.strip() if response.strip() else "_Sem resposta_"
        if len(resposta) > 1024:
            resposta = resposta[:1000] + "..."
        embed.add_field(name="Resposta", value=f"```{resposta}```", inline=False)
        await msg.edit(content=None, embed=embed)

    @commands.command(aliases=["arkhelp", "arkcomandos"])
    @commands.has_permissions(administrator=True)
    async def arkajuda(self, ctx: commands.Context):
        """Mostra todos os comandos."""
        p = ctx.prefix or "!"
        embed = discord.Embed(
            title="🦕 Guia ARK",
            color=discord.Color.og_blurple(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="⚙️ Controle de Servidores",
            value=(
                f"`{p}arkligar <mapa>` - ⚡ Liga\n"
                f"`{p}arkdesligar <mapa>` - 🔴 Desliga *(pede confirmação)*\n"
                f"`{p}arkreinicia <mapa>` - 🔁 Reinicia *(pede confirmação)*\n"
                f"`{p}arkstatus [mapa]` - Verifica online/offline\n"
                f"`{p}arkplayers <mapa>` - Lista conectados\n"
                f"`{p}rcon <mapa> <cmd>` - Comando RCON livre\n"
                f"`{p}arkmapas` - Lista mapas"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔗 Vinculação (NOVO - Super Simples!)",
            value=(
                f"`{p}vincular <URL_STEAM>` - 🚀 Vincula em 1 clique\n"
                f"`{p}meuvínculo` - Ver minhas informações\n"
                f"`{p}atualizarpersonagem <nome>` - Muda seu personagem\n"
                f"`{p}setuppainel` - Cria painel com botão"
            ),
            inline=False
        )
        
        embed.add_field(
            name="� Gerenciamento de Jogadores",
            value=(
                f"`{p}arkkick @user [motivo]` - 🔴 Kick em TODOS os servidores\n"
                f"`{p}arkhistorico @user` - 📜 Mostra ações anteriores\n"
                f"`{p}arkatualizar` - 🔄 Força atualização do monitor"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📝 Exemplos",
            value=(
                f"`{p}vincular https://steamcommunity.com/profiles/76561198123456789`\n"
                f"`{p}arkkick @Ciano Crash suspect`\n"
                f"`{p}arkhistorico @Ciano`"
            ),
            inline=False
        )
        
        embed.set_footer(text="Vinculação agora é SUPER FÁCIL! Leva 30 segundos")
        await ctx.send(embed=embed)

    # ───────────────────────────────────────────────────────────
    # GERENCIAMENTO DE JOGADORES (NOVO)
    # ───────────────────────────────────────────────────────────

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def arkkick(self, ctx: commands.Context, user: discord.User, *, reason: str = "Sem motivo especificado"):
        """
        Faz kick de um jogador em TODOS os servidores.
        Busca pelo Discord vinculado e envia comando RCON para todos os mapas.
        
        Uso: !arkkick @Ciano Crash suspect
        """
        links = load_links()
        discord_id = str(user.id)
        
        # Busca vinculação
        if discord_id not in links:
            await ctx.send(
                f"❌ Usuário `{user.name}` não está vinculado ao ARK.\n"
                "Use `!meuvínculo` ou o painel para vincular primeiro.",
                delete_after=15
            )
            return
        
        steam_id = links[discord_id]["steam_id"]
        player_name = links[discord_id].get("personagem") or links[discord_id].get("discord_name", "Unknown")
        
        # Confirmação
        embed_confirm = discord.Embed(
            title="⚠️ Confirmar Kick",
            description=f"Kickar **{player_name}** de **TODOS** os servidores?",
            color=discord.Color.orange()
        )
        embed_confirm.add_field(name="👤 Discord", value=f"<@{user.id}>", inline=True)
        embed_confirm.add_field(name="🎮 SteamID", value=f"`{steam_id}`", inline=True)
        embed_confirm.add_field(name="📋 Motivo", value=reason, inline=False)
        embed_confirm.add_field(name="🗺️ Servidores Afetados", value=f"`{len(config.ARK_MAPS)}` mapas", inline=False)
        
        view = ConfirmView(ctx.author)
        msg = await ctx.send(embed=embed_confirm, view=view)
        
        await view.wait()
        
        if not view.confirmed:
            embed_cancel = discord.Embed(title="🚫 Cancelado", color=discord.Color.greyple())
            for item in view.children:
                item.disabled = True  # type: ignore
            await msg.edit(embed=embed_cancel, view=view)
            return
        
        # Executa kick em todos os servidores
        msg_progress = await ctx.send("🔄 Processando kicks... isto pode levar até 1 minuto")
        
        results = {}
        kick_command = f"KickPlayer {steam_id}"
        
        for map_key, info in config.ARK_MAPS.items():
            try:
                response = await asyncio.wait_for(
                    rcon_run(info["host"], info["port"], info["password"], kick_command),
                    timeout=TIMEOUT_RCON
                )
                results[info["name"]] = {"status": "✅", "response": response.strip()[:100]}
                print(f"[ARK] ✅ Kick em {info['name']}: {steam_id}")
                
            except asyncio.TimeoutError:
                results[info["name"]] = {"status": "⏱️", "response": "Timeout"}
                print(f"[ARK] ⏱️ Timeout em {info['name']}")
                
            except Exception as e:
                results[info["name"]] = {"status": "❌", "response": str(e)[:100]}
                print(f"[ARK] ❌ Erro em {info['name']}: {e}")
        
        # Log de ação
        self.monitor.log_action(
            steam_id=steam_id,
            action="kick",
            reason=reason,
            admin_id=ctx.author.id,
            extra={
                "discord_user": f"{user.name}#{user.discriminator}",
                "servers_targeted": list(config.ARK_MAPS.keys()),
                "results": results
            }
        )
        
        # Relatório final
        embed_result = discord.Embed(
            title="👊 Kick Executado",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed_result.add_field(name="👤 Alvo", value=f"{player_name} ({steam_id})", inline=False)
        embed_result.add_field(name="📋 Motivo", value=reason, inline=False)
        embed_result.add_field(name="👮 Admin", value=f"<@{ctx.author.id}>", inline=False)
        
        # Status por servidor
        status_text = ""
        for srv_name, result in results.items():
            status_text += f"{result['status']} {srv_name}\n"
        
        embed_result.add_field(name="🗺️ Servidores", value=status_text, inline=False)
        embed_result.set_footer(text="Ação registrada no histórico")
        
        await msg_progress.edit(content=None, embed=embed_result)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def arkhistorico(self, ctx: commands.Context, user: discord.User, limit: int = 10):
        """
        Mostra histórico de ações (kicks, warnings, etc) de um jogador.
        
        Uso: !arkhistorico @Ciano 20
        """
        links = load_links()
        discord_id = str(user.id)
        
        if discord_id not in links:
            await ctx.send(
                f"❌ Usuário `{user.name}` não está vinculado.",
                delete_after=10
            )
            return
        
        steam_id = links[discord_id]["steam_id"]
        player_name = links[discord_id].get("personagem") or links[discord_id].get("discord_name", "Unknown")
        
        history = self.monitor.get_player_history(steam_id, limit=limit)
        
        if not history:
            await ctx.send(
                f"📜 **{player_name}** - Sem histórico de ações",
                delete_after=15
            )
            return
        
        embed = discord.Embed(
            title=f"📜 Histórico: {player_name}",
            description=f"SteamID: `{steam_id}`",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for action in reversed(history[-10:]):  # Últimas 10
            try:
                action_time = datetime.fromisoformat(action["timestamp"])
                time_str = action_time.strftime("%d/%m %H:%M")
            except:
                time_str = "?"
            
            admin_mention = f"<@{action['admin_id']}>" if action.get("admin_id") else "🤖 Auto"
            
            embed.add_field(
                name=f"{action['action'].upper()} - {time_str}",
                value=f"**Motivo:** {action['reason']}\n**Admin:** {admin_mention}",
                inline=False
            )
        
        embed.set_footer(text=f"Total: {len(history)} ação(ões)")
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def arkatualizar(self, ctx: commands.Context):
        """Força atualização imediata do monitor de jogadores."""
        await ctx.send("🔄 Atualizando monitor... *aguarde*")
        
        # Executa um ciclo de monitor imediatamente
        try:
            logged_players = set()
            for map_key, info in config.ARK_MAPS.items():
                try:
                    response = await asyncio.wait_for(
                        rcon_run(info["host"], info["port"], info["password"], "listplayers"),
                        timeout=TIMEOUT_RCON
                    )
                    
                    players = parse_rcon_listplayers(response)
                    
                    for steam_id, name in players:
                        self.monitor.update_player_presence(steam_id, info["name"], online=True)
                        logged_players.add(steam_id)
                    
                    print(f"[Update] ✅ {info['name']}: {len(players)} online")
                    
                except Exception as e:
                    print(f"[Update] ❌ {info['name']}: {str(e)[:100]}")
            
            stats = self.monitor.get_stats()
            
            embed = discord.Embed(
                title="✅ Monitor Atualizado",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="👥 Online Agora", value=stats["online_now"], inline=True)
            embed.add_field(name="⚠️ Crash Suspeitos", value=stats["crash_suspected"], inline=True)
            embed.add_field(name="📊 Total Rastreado", value=stats["total_players_tracked"], inline=True)
            embed.add_field(name="📜 Ações Registradas", value=stats["total_actions_logged"], inline=True)
            
            await ctx.send(embed=embed)
        
        except Exception as e:
            await ctx.send(f"❌ Erro ao atualizar: {e}")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def arkmonitor(self, ctx: commands.Context):
        """Mostra estatísticas do monitor de jogadores."""
        stats = self.monitor.get_stats()
        
        embed = discord.Embed(
            title="📊 Monitor de Jogadores ARK",
            color=discord.Color.teal(),
            timestamp=datetime.now()
        )
        embed.add_field(
            name="👥 Online",
            value=stats["online_now"],
            inline=True
        )
        embed.add_field(
            name="⚠️ Crash",
            value=stats["crash_suspected"],
            inline=True
        )
        embed.add_field(
            name="🔴 Offline",
            value=stats["offline"],
            inline=True
        )
        embed.add_field(
            name="📊 Total Rastreado",
            value=stats["total_players_tracked"],
            inline=True
        )
        embed.add_field(
            name="📜 Ações",
            value=stats["total_actions_logged"],
            inline=True
        )
        embed.set_footer(text="Atualizado automaticamente a cada 30s")
        
        await ctx.send(embed=embed)

    # ───────────────────────────────────────────────────────────
    # TRATAMENTO DE ERROS
    # ───────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🔒 Sem permissão", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"⚠️ Argumento faltando. Use `{ctx.prefix}arkajuda`", delete_after=10)


# ─────────────────────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────────────────────

async def setup(bot: commands.Bot):
    await bot.add_cog(ArkCog(bot))
