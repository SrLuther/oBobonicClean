# cogs/twitch_monitor.py
# Sistema de monitoring Twitch com PAINÉIS E BOTÕES
# Solicitação → Aprovação → Notificação ao Vivo

import discord
from discord.ext import commands, tasks
import requests
import json
import os
import logging
import re
import asyncio
from typing import Dict, Any, Optional, cast
from datetime import datetime, timezone
from functools import partial

import config
# from nicknameUpdater import update_member_nickname  # ❌ DESABILITADO: módulo removido

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────────────────────

APPROVED_FILE = ".bancos/twitch_approved.json"
PENDING_FILE = ".bancos/twitch_pending.json"
STATE_FILE = ".bancos/twitch_monitor_state.json"

TWITCH_API_BASE = "https://api.twitch.tv/helix"
TIMEOUT_REQUEST = 10

# Canais especiais (carregados de config.py)
CHANNEL_REQUEST = config.TWITCH_CHANNEL_REQUEST      # Onde membros solicitam
CHANNEL_APPROVAL = config.TWITCH_CHANNEL_APPROVAL     # Onde admins aprovam
CHANNEL_NOTIF = config.TWITCH_CHANNEL_NOTIF          # Notificação ao vivo

print(f"[TWITCH] 🔌 IDs do Twitch carregados:")
print(f"[TWITCH]   • REQUEST:  {CHANNEL_REQUEST}")
print(f"[TWITCH]   • APPROVAL: {CHANNEL_APPROVAL}")
print(f"[TWITCH]   • NOTIF:    {CHANNEL_NOTIF}")

# Cargo para Streamers Twitch aprovados
TWITCH_ROLE_ID = 1492687604418740315


# ─────────────────────────────────────────────────────────────
# VIEWS (BOTÕES)
# ─────────────────────────────────────────────────────────────

class RequestButtonView(discord.ui.View):
    """Botão de solicitação para membros."""
    
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
    
    @discord.ui.button(label="📌 Solicitar Adição de Canal", style=discord.ButtonStyle.primary, custom_id="twitch_request_btn")
    async def request_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Abre modal de solicitação."""
        await interaction.response.send_modal(TwitchRequestModal(self.cog))


class TwitchRequestModal(discord.ui.Modal, title="Adicionar Canal Twitch"):
    """Modal para solicitar adição de canal."""
    
    channel = discord.ui.TextInput(
        label="Link ou Username da Twitch",
        placeholder="https://twitch.tv/seu_canal ou seu_username",
        required=True,
        min_length=3,
        max_length=100
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
    
    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.process_request(interaction, self.channel.value)


class ApprovalButtonView(discord.ui.View):
    """Botões de aprovação para admins."""
    
    def __init__(self, cog, request_id: str, username: str):
        super().__init__(timeout=None)
        self.cog = cog
        self.request_id = request_id
        self.username = username
    
    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.green)
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_approval(interaction, self.request_id, True)
    
    @discord.ui.button(label="❌ Rejeitar", style=discord.ButtonStyle.red)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_approval(interaction, self.request_id, False)


class LiveButtonView(discord.ui.View):
    """Botão para ir à live."""
    
    def __init__(self, username: str):
        super().__init__(timeout=None)
        self.username = username
        # Adiciona botão de link dinamicamente
        self.add_item(discord.ui.Button(
            label="🎬 Ir para a Live",
            style=discord.ButtonStyle.link,
            url=f"https://www.twitch.tv/{username}"
        ))


# ─────────────────────────────────────────────────────────────
# COG PRINCIPAL
# ─────────────────────────────────────────────────────────────

class TwitchMonitorCog(commands.Cog):
    """Sistema de monitoring Twitch com painéis e botões."""
    
    def __init__(self, bot: commands.Bot):
        print(f"[TWITCH] 🔧 TwitchMonitorCog.__init__() CHAMADO")
        self.bot = bot
        self.approved_channels: Dict[str, int] = {}
        self.pending_requests: Dict[str, Dict] = {}
        self.stream_state: Dict[str, Dict[str, Any]] = {}
        self._access_token: str = config.TWITCH_ACCESS_TOKEN
        self._startup_task: Optional[asyncio.Task] = None

        logger.info("[TWITCH] 🔧 TwitchMonitorCog inicializando...")
        print(f"[TWITCH] 📡 Carregando dados...")
        self.load_data()

        print(f"[TWITCH] ✅ TwitchMonitorCog pronto!")
        logger.info("[TWITCH] ✅ TwitchMonitorCog pronto!")

    async def cog_load(self) -> None:
        """Inicia startup ao cog ser carregado."""
        self._startup_task = asyncio.create_task(self._startup())
        print("[TWITCH] 🚀 Task de startup criada.")

    def cog_unload(self):
        if self._startup_task and not self._startup_task.done():
            self._startup_task.cancel()
        if hasattr(self, 'check_streams') and self.check_streams.is_running():
            self.check_streams.cancel()
        logger.info("[TWITCH] Monitor cancelado")
    
    # ─────────────────────────────────────────────────────────────
    # INICIALIZAÇÃO AUTOMÁTICA
    # ─────────────────────────────────────────────────────────────

    async def _startup(self) -> None:
        """Aguarda bot pronto, renova token se possível e cria painéis."""
        try:
            await self.bot.wait_until_ready()
            print("[TWITCH] ⏳ Bot pronto! Iniciando startup...")

            # Tenta renovar o token se client_secret estiver configurado
            if config.TWITCH_CLIENT_ID and config.TWITCH_CLIENT_SECRET:
                await self._refresh_token()
            else:
                print("[TWITCH] ⚠️ Credenciais incompletas (CLIENT_ID ou CLIENT_SECRET vazios)")
                logger.warning("[TWITCH] ⚠️ Credenciais incompletas")

            # Limpa o estado salvo para que o primeiro ciclo detecte lives ativas e notifique
            self.stream_state = {}
            self.save_data()
            print("[TWITCH] 🔄 Estado resetado - lives ativas serão notificadas na primeira varredura")

            # Inicia monitor SEMPRE que houver canais aprovados (independente do token)
            # _get_stream_info trata token inválido internamente
            if not self.check_streams.is_running():
                self.check_streams.start()
                logger.info(f"[TWITCH] ✅ Monitor iniciado. {len(self.approved_channels)} canal(is) aprovado(s)")

            # Cria painéis
            await self._create_panels_internal()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[TWITCH] ❌ Erro no startup: {e}")
            logger.error(f"[TWITCH] ❌ Erro no startup: {e}")
            import traceback
            traceback.print_exc()

    async def force_create_panels(self):
        """Força recriação dos painéis."""
        print(f"[TWITCH] 💪 force_create_panels() chamado!")
        logger.info("[TWITCH] 💪 force_create_panels() chamado")
        await self._create_panels_internal()

    async def _create_panels_internal(self):
        """Cria os painéis de solicitação e aprovação."""
        print(f"[TWITCH] 🔍 Verificando canais...")
        print(f"[TWITCH]   • REQUEST ({CHANNEL_REQUEST}): {self.bot.get_channel(CHANNEL_REQUEST)}")
        print(f"[TWITCH]   • APPROVAL ({CHANNEL_APPROVAL}): {self.bot.get_channel(CHANNEL_APPROVAL)}")
        print(f"[TWITCH]   • NOTIF ({CHANNEL_NOTIF}): {self.bot.get_channel(CHANNEL_NOTIF)}")

        print(f"[TWITCH] 🔄 Recriando painéis automáticos...")
        logger.info("[TWITCH] 🔄 Recriando painéis automáticos...")

        try:
            print(f"[TWITCH] 📝 Etapa 1: Criando painel de solicitação...")
            await self._create_request_panel()
            print(f"[TWITCH] ✅ Painel de solicitação criado!")

            await asyncio.sleep(1)

            print(f"[TWITCH] 📋 Etapa 2: Atualizando painel de aprovação...")
            await self._update_approval_panel()
            print(f"[TWITCH] ✅ Painel de aprovação atualizado!")

            print(f"[TWITCH] 🎉 PAINÉIS CRIADOS COM SUCESSO!")
            logger.info("[TWITCH] 🎉 PAINÉIS CRIADOS COM SUCESSO!")
        except Exception as e:
            print(f"[TWITCH] ❌ ERRO ao criar painéis: {e}")
            logger.error(f"[TWITCH] ❌ ERRO ao criar painéis: {e}")
            import traceback
            traceback.print_exc()
    
    # ─────────────────────────────────────────────────────────────
    # PERSISTÊNCIA
    # ─────────────────────────────────────────────────────────────
    
    def load_data(self):
        try:
            os.makedirs(".bancos", exist_ok=True)
            
            if os.path.exists(APPROVED_FILE):
                with open(APPROVED_FILE, 'r', encoding='utf-8') as f:
                    self.approved_channels = json.load(f)
            
            if os.path.exists(PENDING_FILE):
                with open(PENDING_FILE, 'r', encoding='utf-8') as f:
                    self.pending_requests = json.load(f)
            
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    self.stream_state = json.load(f)
        except Exception as e:
            logger.error(f"[TWITCH] Erro ao carregar: {e}")
    
    def save_data(self):
        try:
            os.makedirs(".bancos", exist_ok=True)
            with open(APPROVED_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.approved_channels, f, indent=4, ensure_ascii=False)
            with open(PENDING_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.pending_requests, f, indent=4, ensure_ascii=False)
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.stream_state, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[TWITCH] Erro ao salvar: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # UTILITÁRIOS
    # ─────────────────────────────────────────────────────────────
    
    def _extract_username(self, url_or_username: str) -> str:
        if "twitch.tv/" in url_or_username:
            match = re.search(r'twitch\.tv/([a-zA-Z0-9_-]+)', url_or_username)
            if match:
                return match.group(1).lower()
        return url_or_username.lower()
    
    def _get_headers(self) -> Dict[str, str]:
        """Headers para API Twitch."""
        return {
            "Client-ID": config.TWITCH_CLIENT_ID or "",
            "Authorization": f"Bearer {self._access_token}" if self._access_token else ""
        }

    async def _refresh_token(self) -> None:
        """Renova o access token via Client Credentials."""
        try:
            loop = asyncio.get_event_loop()
            def _do_request():
                return requests.post(
                    "https://id.twitch.tv/oauth2/token",
                    params={
                        "client_id": config.TWITCH_CLIENT_ID,
                        "client_secret": config.TWITCH_CLIENT_SECRET,
                        "grant_type": "client_credentials",
                    },
                    timeout=TIMEOUT_REQUEST,
                )
            response = await loop.run_in_executor(None, _do_request)
            response.raise_for_status()
            data = response.json()
            self._access_token = data["access_token"]
            expires_in = data.get("expires_in", 0)
            print(f"[TWITCH] ✅ Token renovado! Expira em {expires_in // 3600}h")
            logger.info(f"[TWITCH] ✅ Token renovado. Expira em {expires_in // 3600}h")
        except Exception as e:
            print(f"[TWITCH] ⚠️ Falha ao renovar token: {e} — usando token atual")
            logger.warning(f"[TWITCH] Falha ao renovar token: {e}")
    
    async def _validate_channel_exists(self, username: str) -> bool:
        """
        Valida se o canal Twitch existe via API Helix (users endpoint).
        Requer credenciais válidas; se não houver, valida apenas o formato.
        """
        if not username or len(username) < 3:
            return False

        # Valida formato do username Twitch
        if not re.match(r"^[a-zA-Z0-9_]{3,25}$", username):
            logger.warning(f"[TWITCH] Username inválido (formato): {username}")
            return False

        if not config.TWITCH_CLIENT_ID or not self._access_token:
            # Sem credenciais: aceita se formato for válido
            logger.warning(f"[TWITCH] Sem credenciais para validar {username} — aceito por formato")
            return True

        try:
            loop = asyncio.get_event_loop()
            headers = self._get_headers()
            def _do_request():
                return requests.get(
                    f"{TWITCH_API_BASE}/users",
                    headers=headers,
                    params={"login": username},
                    timeout=TIMEOUT_REQUEST,
                )
            response = await loop.run_in_executor(None, _do_request)
            if response.status_code == 401:
                # Token expirado — tenta renovar e repete uma vez
                await self._refresh_token()
                headers = self._get_headers()
                def _do_retry():
                    return requests.get(
                        f"{TWITCH_API_BASE}/users",
                        headers=headers,
                        params={"login": username},
                        timeout=TIMEOUT_REQUEST,
                    )
                response = await loop.run_in_executor(None, _do_retry)
            response.raise_for_status()
            data = response.json()
            if data.get("data"):
                logger.info(f"[TWITCH] ✅ Canal {username} validado via API")
                return True
            logger.warning(f"[TWITCH] ❌ Canal {username} não encontrado na API")
            return False
        except requests.exceptions.Timeout:
            logger.error(f"[TWITCH] ⏱️ Timeout ao validar {username}")
            return False
        except Exception as e:
            logger.error(f"[TWITCH] Erro ao validar canal {username}: {e}")
            return False
    
    async def _get_stream_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Retorna informações da stream ao vivo do canal, ou None se offline."""
        try:
            loop = asyncio.get_event_loop()
            headers = self._get_headers()
            def _do_request():
                return requests.get(
                    f"{TWITCH_API_BASE}/streams",
                    headers=headers,
                    params={"user_login": username},
                    timeout=TIMEOUT_REQUEST,
                )
            response = await loop.run_in_executor(None, _do_request)
            if response.status_code == 401:
                await self._refresh_token()
                headers = self._get_headers()
                def _do_retry():
                    return requests.get(
                        f"{TWITCH_API_BASE}/streams",
                        headers=headers,
                        params={"user_login": username},
                        timeout=TIMEOUT_REQUEST,
                    )
                response = await loop.run_in_executor(None, _do_retry)
            response.raise_for_status()
            data = response.json()
            if data.get("data"):
                return data["data"][0]
        except Exception as e:
            logger.error(f"[TWITCH] Erro ao obter stream de {username}: {e}")
        return None
    
    # ─────────────────────────────────────────────────────────────
    # LÓGICA DE SOLICITAÇÃO
    # ─────────────────────────────────────────────────────────────
    
    async def process_request(self, interaction: discord.Interaction, input_text: str):
        """Processa solicitação de adição de canal."""
        await interaction.response.defer(thinking=True)
        
        try:
            username = self._extract_username(input_text.strip()).lower()
            
            # Validações
            if not username or len(username) < 3:
                await interaction.followup.send(
                    "❌ **Username inválido!**\n"
                    "Digite um link (https://twitch.tv/seu_canal) ou username válido.",
                    ephemeral=True
                )
                return
            
            if username in self.approved_channels:
                await interaction.followup.send(
                    f"⚠️ Canal `{username}` já está monitorado!",
                    ephemeral=True
                )
                return
            
            for req in self.pending_requests.values():
                if req.get("username") == username:
                    await interaction.followup.send(
                        f"⏳ Canal `{username}` já tem solicitação pendente!",
                        ephemeral=True
                    )
                    return
            
            # Valida existência na Twitch
            channel_exists = await self._validate_channel_exists(username)
            if not channel_exists:
                await interaction.followup.send(
                    f"❌ Canal `{username}` não encontrado na Twitch!\n"
                    "Verifique o nome e tente novamente.",
                    ephemeral=True
                )
                return
            
            # Cria solicitação
            request_id = f"{interaction.user.id}_{username}_{datetime.now().timestamp()}"
            self.pending_requests[request_id] = {
                "username": username,
                "user_id": interaction.user.id,
                "user_name": str(interaction.user),
                "user_avatar": interaction.user.display_avatar.url,
                "requested_at": datetime.now(timezone.utc).isoformat()
            }
            self.save_data()
            
            # Responde ao membro
            embed_user = discord.Embed(
                title="✅ Solicitação Enviada!",
                description=f"Seu canal `{username}` foi enviado para aprovação.",
                color=discord.Color.green()
            )
            embed_user.add_field(name="Canal", value=f"`{username}`", inline=True)
            embed_user.add_field(name="Status", value="⏳ Aguardando aprovação", inline=True)
            embed_user.set_footer(text="Um admin analisará sua solicitação em breve!")
            
            await interaction.followup.send(embed=embed_user, ephemeral=True)
            
            # Notifica admins no painel
            await self._update_approval_panel()
            
            logger.info(f"[TWITCH] Solicitação de {interaction.user}: {username}")
            
        except Exception as e:
            logger.error(f"[TWITCH] Erro na solicitação: {e}")
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)
    
    async def handle_approval(self, interaction: discord.Interaction, request_id: str, approve: bool):
        """Processa aprovação ou rejeição."""
        await interaction.response.defer(thinking=True)
        
        # Verifica permissão
        if not isinstance(interaction.user, discord.Member):
            await interaction.followup.send("❌ Erro ao verificar permissões!", ephemeral=True)
            return
        
        if not any(role.id in config.MOD_ROLE_IDS for role in interaction.user.roles):
            await interaction.followup.send("❌ Você não tem permissão!", ephemeral=True)
            return
        
        if request_id not in self.pending_requests:
            await interaction.followup.send("❌ Solicitação não encontrada!", ephemeral=True)
            return
        
        req_data = self.pending_requests[request_id]
        username = req_data.get("username", "?")
        user_id = req_data.get("user_id", 0)
        
        if approve:
            # Aprova
            self.approved_channels[username] = user_id
            del self.pending_requests[request_id]
            self.save_data()
            
            if not self.check_streams.is_running():
                self.check_streams.start()
            
            await interaction.followup.send(
                f"✅ Canal `{username}` **aprovado** e adicionado ao monitoramento!",
                ephemeral=True
            )
            
            # Tenta dar o cargo e atualizar nickname
            try:
                guild = interaction.guild
                member = guild.get_member(user_id)
                
                if member:
                    # Adiciona cargo
                    role = guild.get_role(TWITCH_ROLE_ID)
                    if role:
                        await member.add_roles(role)
                        logger.info(f"[TWITCH] Cargo 🔴 adicionado a {member}")
                    
                    # Atualiza nickname
                    # await update_member_nickname(member)  # ❌ DESABILITADO: módulo removido
                    logger.info(f"[TWITCH] Nickname atualizado para {member}")
            except Exception as e:
                logger.warning(f"[TWITCH] Erro ao adicionar cargo/nickname: {e}")
            
            # DM ao membro
            try:
                member = await self.bot.fetch_user(user_id)
                embed_dm = discord.Embed(
                    title="✅ Canal Aprovado!",
                    description=f"Seu canal Twitch `{username}` foi **aprovado**! 🎉",
                    color=discord.Color.green()
                )
                embed_dm.add_field(
                    name="O que acontece agora?",
                    value=f"✨ Você recebeu o cargo 🔴 Streamer!\n\nQuando você iniciar uma transmissão, o servidor será notificado em <#{CHANNEL_NOTIF}>!",
                    inline=False
                )
                embed_dm.set_footer(text="Divirta-se transmitindo!")
                await member.send(embed=embed_dm)
            except:
                pass
            
            logger.info(f"[TWITCH] {interaction.user} aprovou: {username}")
        
        else:
            # Rejeita
            del self.pending_requests[request_id]
            self.save_data()
            
            await interaction.followup.send(
                f"❌ Solicitação de `{username}` **rejeitada**!",
                ephemeral=True
            )
            
            # DM ao membro
            try:
                member = await self.bot.fetch_user(user_id)
                embed_dm = discord.Embed(
                    title="❌ Solicitação Rejeitada",
                    description=f"Sua solicitação para `{username}` foi rejeitada.",
                    color=discord.Color.red()
                )
                embed_dm.add_field(
                    name="Próximos passos",
                    value="Você pode tentar solicitar novamente ou entrar em contato com um admin.",
                    inline=False
                )
                await member.send(embed=embed_dm)
            except:
                pass
            
            logger.info(f"[TWITCH] {interaction.user} rejeitou: {username}")
        
        # Atualiza painel
        await self._update_approval_panel()
    
    # ─────────────────────────────────────────────────────────────
    # PAINÉIS
    # ─────────────────────────────────────────────────────────────
    
    async def _create_request_panel(self):
        """Cria o painel de solicitação no canal designado."""
        print(f"[TWITCH]     → _create_request_panel() chamado")
        try:
            print(f"[TWITCH]     - Procurando canal REQUEST: {CHANNEL_REQUEST}")
            channel = cast(discord.TextChannel, self.bot.get_channel(CHANNEL_REQUEST))
            print(f"[TWITCH]     - Resultado: {channel}")
            
            if not channel:
                print(f"[TWITCH]     ❌ CANAL NÃO ENCONTRADO!")
                logger.error(f"[TWITCH] ❌ CANAL {CHANNEL_REQUEST} NÃO ENCONTRADO!")
                logger.warning("[TWITCH] Verifique:")
                logger.warning(f"  • ID no config.py: TWITCH_CHANNEL_REQUEST = {CHANNEL_REQUEST}")
                logger.warning("  • Se o canal existe no Discord")
                logger.warning("  • Se o bot tem acesso ao canal")
                print(f"[TWITCH]     - Canais disponíveis no bot:")
                for guild in self.bot.guilds:
                    for ch in guild.channels:
                        if hasattr(ch, 'name'):
                            print(f"[TWITCH]       - {ch.id}: {ch.name} ({type(ch).__name__})")
                return
            
            print(f"[TWITCH]     ✅ Canal encontrado: {channel.name} ({channel.id})")
            logger.info(f"[TWITCH] ✅ Canal encontrado: {channel.name} ({channel.id})")
            
            # LIMPA MENSAGENS ANTIGAS
            print(f"[TWITCH]     - Limpando mensagens antigas...")
            logger.info("[TWITCH] 🧹 Limpando mensagens antigas...")
            deleted_count = 0
            try:
                async for msg in channel.history(limit=100):
                    if msg.author == self.bot.user:
                        try:
                            await msg.delete()
                            deleted_count += 1
                            logger.debug(f"[TWITCH] Deletada mensagem: {msg.id}")
                        except Exception as e:
                            logger.warning(f"[TWITCH] Não pude deletar mensagem {msg.id}: {e}")
            except Exception as e:
                logger.warning(f"[TWITCH] Erro ao limpar historico: {e}")
            
            print(f"[TWITCH]     ✓ {deleted_count} mensagens antigas removidas")
            logger.info(f"[TWITCH] 🗑️  {deleted_count} mensagens antigas removidas")
            
            # CRIA NOVO PAINEL
            print(f"[TWITCH]     - Criando embed do painel...")
            embed = discord.Embed(
                title="📺 Solicitar Adição de Canal Twitch",
                description="Quer que seu canal seja monitorado e notificado quando você estiver ao vivo?\n\n"
                           "🎬 **Como funciona:**\n"
                           "1. Clique no botão abaixo\n"
                           "2. Insira o link ou username do seu canal\n"
                           "3. Um admin analisará e aprovará\n"
                           "4. Quando você estiver ao vivo, o servidor será notificado!\n\n"
                           "✨ **Benefícios:**\n"
                           "• A comunidade sabe quando você está transmitindo\n"
                           "• Notificação no canal dedicado\n"
                           "• Aumenta o engajamento\n"
                           "• 100% seguro e verificado",
                color=discord.Color.from_rgb(145, 70, 255)
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/5968/5968819.png")
            embed.set_footer(text="Monitor Twitch 📺 • Criado automaticamente ao iniciar o bot")
            
            print(f"[TWITCH]     - Enviando painel...")
            msg = await channel.send(embed=embed, view=RequestButtonView(self))
            print(f"[TWITCH]     ✅ Painel enviado! ID: {msg.id}")
            logger.info(f"[TWITCH] 📤 Painel de solicitação enviado! Mensagem ID: {msg.id}")
            
        except Exception as e:
            print(f"[TWITCH]     ❌ ERRO: {e}")
            logger.error(f"[TWITCH] ❌ ERRO AO CRIAR PAINEL DE SOLICITAÇÃO: {e}")
            import traceback
            traceback.print_exc()
    
    async def _update_approval_panel(self):
        """Atualiza o painel de aprovação."""
        print(f"[TWITCH]     → _update_approval_panel() chamado")
        try:
            print(f"[TWITCH]     - Procurando canal APPROVAL: {CHANNEL_APPROVAL}")
            channel = cast(discord.TextChannel, self.bot.get_channel(CHANNEL_APPROVAL))
            print(f"[TWITCH]     - Resultado: {channel}")
            
            if not channel:
                print(f"[TWITCH]     ❌ CANAL NÃO ENCONTRADO!")
                logger.error(f"[TWITCH] ❌ CANAL {CHANNEL_APPROVAL} NÃO ENCONTRADO!")
                logger.warning("[TWITCH] Verifique:")
                logger.warning(f"  • ID no config.py: TWITCH_CHANNEL_APPROVAL = {CHANNEL_APPROVAL}")
                logger.warning("  • Se o canal existe no Discord")
                logger.warning("  • Se o bot tem acesso ao canal")
                return
            
            print(f"[TWITCH]     ✅ Canal encontrado: {channel.name} ({channel.id})")
            logger.info(f"[TWITCH] ✅ Canal encontrado: {channel.name} ({channel.id})")
            
            # LIMPA MENSAGENS ANTIGAS
            print(f"[TWITCH]     - Limpando mensagens antigas...")
            logger.info("[TWITCH] 🧹 Limpando mensagens antigas...")
            deleted_count = 0
            try:
                async for msg in channel.history(limit=100):
                    if msg.author == self.bot.user:
                        try:
                            await msg.delete()
                            deleted_count += 1
                        except Exception as e:
                            logger.warning(f"[TWITCH] Não pude deletar mensagem: {e}")
            except Exception as e:
                logger.warning(f"[TWITCH] Erro ao limpar histórico: {e}")
            
            print(f"[TWITCH]     ✓ {deleted_count} mensagens antigas removidas")
            logger.info(f"[TWITCH] 🗑️  {deleted_count} mensagens antigas removidas")
            
            # CRIA OU ATUALIZA PAINEL
            if not self.pending_requests:
                print(f"[TWITCH]     - Nenhuma solicitação pendente, criando painel vazio...")
                logger.info("[TWITCH] Nenhuma solicitação pendente, criando painel vazio...")
                embed = discord.Embed(
                    title="📋 Painel de Aprovação",
                    description="✅ Nenhuma solicitação pendente!",
                    color=discord.Color.green()
                )
                embed.set_footer(text="Monitor Twitch 📺 • Criado automaticamente ao iniciar o bot")
                msg = await channel.send(embed=embed, view=TwitchManagePanelView(self))
                print(f"[TWITCH]     ✅ Painel enviado! ID: {msg.id}")
                logger.info(f"[TWITCH] 📤 Painel de aprovação (vazio) enviado! Mensagem ID: {msg.id}")
                return
            
            # Se houver solicitações
            print(f"[TWITCH]     - {len(self.pending_requests)} solicitação(ões) pendente(es)")
            logger.info(f"[TWITCH] {len(self.pending_requests)} solicitação(ões) pendente(es)")
            
            embed = discord.Embed(
                title="📋 Painel de Aprovação de Canais Twitch",
                description=f"**Total:** {len(self.pending_requests)} solicitação(ões)",
                color=discord.Color.blue()
            )
            
            for idx, (req_id, data) in enumerate(self.pending_requests.items(), 1):
                username = data.get("username", "?")
                user_name = data.get("user_name", "?")
                req_time = data.get("requested_at", "?")
                channel_url = f"https://www.twitch.tv/{username}"

                embed.add_field(
                    name=f"#{idx} - {username.upper()}",
                    value=(
                        f"👤 De: {user_name}\n"
                        f"⏰ Solicitado em: {req_time[:10]}\n"
                        f"🔗 Canal: [twitch.tv/{username}]({channel_url})\n\n"
                        f"🔑 ID: `{req_id}`"
                    ),
                    inline=False
                )
            
            embed.set_footer(text="Monitor Twitch 📺 • Clique em Aprovar ou Rejeitar • Criado automaticamente ao iniciar o bot")
            
            print(f"[TWITCH]     - Enviando painel...")
            for req_id, data in self.pending_requests.items():
                msg = await channel.send(embed=embed, view=ApprovalButtonView(self, req_id, data.get("username", "?")))
                logger.info(f"[TWITCH] 📤 Painel de aprovação enviado! Mensagem ID: {msg.id}")
                break
            # Botão de gerenciamento separado (sem interferir nos botões de aprovação)
            await channel.send(view=TwitchManagePanelView(self))
            
        except Exception as e:
            logger.error(f"[TWITCH] ❌ ERRO AO ATUALIZAR PAINEL: {e}")
            import traceback
            traceback.print_exc()
    
    # ─────────────────────────────────────────────────────────────
    # MONITORAMENTO DE STREAMS
    # ─────────────────────────────────────────────────────────────
    
    @tasks.loop(minutes=5)
    async def check_streams(self):
        """Verifica streams a cada 5 minutos."""
        try:
            if not self.approved_channels:
                return

            for username, user_id_discord in self.approved_channels.items():
                stream_info = await self._get_stream_info(username)
                is_live = stream_info is not None
                was_live = self.stream_state.get(username, {}).get("is_live", False)
                
                # offline → online
                if is_live and not was_live:
                    await self._send_live_notification(stream_info, user_id_discord)
                
                # Atualiza estado
                if is_live:
                    self.stream_state[username] = {
                        "is_live": True,
                        "title": stream_info.get("title", ""),
                        "game": stream_info.get("game_name", ""),
                        "viewers": stream_info.get("viewer_count", 0),
                        "last_checked": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    self.stream_state[username] = {
                        "is_live": False,
                        "last_checked": datetime.now(timezone.utc).isoformat()
                    }
            
            self.save_data()
        except Exception as e:
            logger.error(f"[TWITCH] Erro no loop: {e}")
    
    @check_streams.before_loop
    async def before_check_streams(self):
        await self.bot.wait_until_ready()
        logger.info("[TWITCH] Monitor de streams ativo!")
    
    # Plataformas suportadas — descomente e expanda ao adicionar YouTube/Kick
    PLATFORM_CONFIG = {
        "twitch": {
            "label":  "Twitch",
            "color":  (145, 70, 255),
            "url":    "https://www.twitch.tv/{username}",
            "icon":   "https://static.twitchcdn.net/assets/favicon-32-e29e246c157142c1.png",
            "footer": "Twitch • Monitor de Lives",
        },
        # "youtube": {
        #     "label":  "YouTube",
        #     "color":  (255, 0, 0),
        #     "url":    "https://www.youtube.com/@{username}/live",
        #     "icon":   "https://www.youtube.com/favicon.ico",
        #     "footer": "YouTube • Monitor de Lives",
        # },
        # "kick": {
        #     "label":  "Kick",
        #     "color":  (83, 252, 31),
        #     "url":    "https://kick.com/{username}",
        #     "icon":   "https://kick.com/favicon.ico",
        #     "footer": "Kick • Monitor de Lives",
        # },
    }

    FRASES_LIVE = [
        "largou tudo e foi transmitir. Cola lá antes que acabe!",
        "está ao vivo. Não adianta fingir que não viu.",
        "ligou a câmera agora mesmo. Bora assistir?",
        "entrou ao vivo — precisa de audiência, e você sabe disso.",
        "abriu a transmissão. O chat tá esperando reforço.",
        "está transmitindo neste exato momento. Vai perder?",
        "colocou o 'ao vivo' pra funcionar. Passa lá depois desse missão.",
        "acabou de iniciar uma live. Dá uma chance, pode ser épico.",
        "tá ao vivo e o servidor inteiro foi avisado. Agora é com você.",
        "iniciou a transmissão — o botão tá logo ali embaixo.",
    ]

    async def _send_live_notification(
        self,
        stream_info: Dict[str, Any],
        user_id_discord: int,
        platform: str = "twitch"
    ):
        """Envia notificação quando alguém entra ao vivo."""
        try:
            channel = cast(discord.TextChannel, self.bot.get_channel(CHANNEL_NOTIF))
            if not channel:
                return

            username = stream_info.get("user_name", "?")
            title = stream_info.get("title", "Sem título")
            game = stream_info.get("game_name", "Sem categoria")
            viewers = stream_info.get("viewer_count", 0)
            thumbnail = stream_info.get("thumbnail_url", "")

            import random

            plat = self.PLATFORM_CONFIG.get(platform, self.PLATFORM_CONFIG["twitch"])
            stream_url = plat["url"].format(username=username)
            frase = random.choice(self.FRASES_LIVE)

            r, g, b = plat["color"]
            embed = discord.Embed(
                description=(
                    f"### 🔴 Ao Vivo na {plat['label']}\n"
                    f"**{username}** {frase}\n\n"
                    f"*{title}*"
                ),
                color=discord.Color.from_rgb(r, g, b),
                url=stream_url,
                timestamp=datetime.now(timezone.utc)
            )

            embed.set_author(
                name=f"{username}  •  {plat['label']}",
                url=stream_url,
                icon_url=plat["icon"]
            )

            # Calcula tempo ao vivo a partir de started_at (formato ISO 8601 da Twitch)
            started_at_raw = stream_info.get("started_at", "")
            if started_at_raw:
                try:
                    started_dt = datetime.fromisoformat(started_at_raw.replace("Z", "+00:00"))
                    elapsed = datetime.now(timezone.utc) - started_dt
                    mins = int(elapsed.total_seconds() // 60)
                    if mins < 60:
                        tempo_live = f"`{mins} min`"
                    else:
                        h, m = divmod(mins, 60)
                        tempo_live = f"`{h}h {m}min`"
                except Exception:
                    tempo_live = "`—`"
            else:
                tempo_live = "`—`"

            embed.add_field(name="🎮 Jogando",      value=f"`{game}`",    inline=True)
            embed.add_field(name="👥 Espectadores", value=f"`{viewers:,}`", inline=True)
            embed.add_field(name="⏱️ Ao vivo há",   value=tempo_live,     inline=True)

            if thumbnail:
                thumb = thumbnail.replace("{width}", "1280").replace("{height}", "720")
                embed.set_image(url=f"{thumb}?t={int(datetime.now().timestamp())}")

            embed.set_footer(text=plat["footer"])

            mention = f"<@{user_id_discord}>" if user_id_discord else f"**{username}**"

            await channel.send(
                content=f"{mention} está **ao vivo** agora! 🔴",
                embed=embed,
                view=LiveButtonView(username)
            )

            logger.info(f"[TWITCH] 🔴 Notificação ao vivo: {username} ({plat['label']})")
        except Exception as e:
            logger.error(f"[TWITCH] Erro ao notificar: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # COMANDOS ADMIN EXTREMOS (APENAS PARA USOS RAROS)
    # ─────────────────────────────────────────────────────────────
    
    @commands.command(name="twitch_rebuild_panels")
    @commands.has_any_role(*config.MOD_ROLE_IDS)
    async def twitch_rebuild_panels(self, ctx: commands.Context):
        """[ADMIN EXTREMO] Reconstrói os painéis do zero."""
        try:
            await ctx.send("🔄 Reconstruindo painéis...")
            await self._create_request_panel()
            await self._update_approval_panel()
            await ctx.send("✅ Painéis reconstruídos com sucesso!")
        except Exception as e:
            logger.error(f"[TWITCH] Erro: {e}")
            await ctx.send(f"❌ Erro: {e}")
    
    @commands.command(name="twitch_status")
    async def twitch_status(self, ctx: commands.Context):
        """[TODOS] Ver status dos canais e diagnóstico do monitor."""
        try:
            loop_running = self.check_streams.is_running()
            loop_status = "🟢 Rodando" if loop_running else "🔴 PARADO"
            token_ok = bool(self._access_token)
            creds_ok = bool(config.TWITCH_CLIENT_ID and config.TWITCH_CLIENT_SECRET)

            if not self.approved_channels:
                embed = discord.Embed(
                    title="📺 Status dos Canais",
                    description="Nenhum canal monitorado ainda!",
                    color=discord.Color.red()
                )
                embed.add_field(name="⚙️ Monitor", value=loop_status, inline=True)
                embed.add_field(name="🔑 Credenciais", value="✅" if creds_ok else "❌", inline=True)
                await ctx.send(embed=embed)
                return

            embed = discord.Embed(
                title="📺 Status dos Canais Twitch",
                description=f"Total: {len(self.approved_channels)} canal(is)",
                color=discord.Color.from_rgb(145, 70, 255)
            )

            for username in self.approved_channels.keys():
                state = self.stream_state.get(username, {})
                is_live = state.get("is_live", False)
                last_checked = state.get("last_checked", "Nunca verificado")
                if last_checked != "Nunca verificado":
                    last_checked = last_checked[:19].replace("T", " ") + " UTC"

                if is_live:
                    title = state.get("title", "Sem título")
                    game = state.get("game", "?")
                    viewers = state.get("viewers", 0)
                    value = f"🔴 **AO VIVO**\n{title}\nJogo: {game}\nEspectadores: {viewers:,}\n🕐 {last_checked}"
                else:
                    value = f"⚫ Offline\n🕐 {last_checked}"

                embed.add_field(name=f"{username.upper()}", value=value, inline=False)

            embed.add_field(name="⚙️ Loop monitor", value=loop_status, inline=True)
            embed.add_field(name="🔑 Credenciais", value="✅" if creds_ok else "❌ Faltando", inline=True)
            embed.add_field(name="🪙 Token", value="✅" if token_ok else "❌ Vazio", inline=True)
            embed.set_footer(text="Use !twitch_force_check para verificar agora")

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Erro: {e}")

    @commands.command(name="twitch_gerenciar")
    @commands.has_any_role(*config.MOD_ROLE_IDS)
    async def twitch_gerenciar(self, ctx: commands.Context):
        """[ADMIN] Gerenciar canais Twitch aprovados (remover, editar)."""
        if not self.approved_channels:
            await ctx.send("⚠️ Nenhum canal aprovado para gerenciar.")
            return

        embed = discord.Embed(
            title="⚙️ Gerenciar Canais Twitch",
            description=f"**{len(self.approved_channels)}** canal(is) aprovado(s).\nSelecione um canal no menu abaixo:",
            color=discord.Color.from_rgb(145, 70, 255)
        )
        for username, user_id in self.approved_channels.items():
            state = self.stream_state.get(username, {})
            is_live = state.get("is_live", False)
            status = "🔴 Ao vivo" if is_live else "⚫ Offline"
            embed.add_field(
                name=username,
                value=f"{status}\n[twitch.tv/{username}](https://www.twitch.tv/{username})\n👤 <@{user_id}>",
                inline=True
            )
        embed.set_footer(text="Selecione um canal e escolha Remover ou Editar Username")
        await ctx.send(embed=embed, view=TwitchManageView(self))

    @commands.command(name="twitch_force_check")
    @commands.has_any_role(*config.MOD_ROLE_IDS)
    async def twitch_force_check(self, ctx: commands.Context):
        """[ADMIN] Força verificação imediata de todas as streams."""
        await ctx.send("🔍 Verificando streams agora...")
        try:
            if not self.approved_channels:
                await ctx.send("⚠️ Nenhum canal aprovado para verificar.")
                return

            # Renova token antes de verificar
            if config.TWITCH_CLIENT_ID and config.TWITCH_CLIENT_SECRET:
                await self._refresh_token()

            resultados = []
            for username, user_id_discord in self.approved_channels.items():
                stream_info = await self._get_stream_info(username)
                is_live = stream_info is not None
                was_live = self.stream_state.get(username, {}).get("is_live", False)

                if is_live and not was_live:
                    await self._send_live_notification(stream_info, user_id_discord)
                    resultados.append(f"🔴 **{username}** — AO VIVO (notificação enviada!)")
                elif is_live:
                    resultados.append(f"🔴 **{username}** — ao vivo (já notificado antes)")
                else:
                    resultados.append(f"⚫ **{username}** — offline")

                self.stream_state[username] = {
                    "is_live": is_live,
                    "title": stream_info.get("title", "") if stream_info else "",
                    "game": stream_info.get("game_name", "") if stream_info else "",
                    "viewers": stream_info.get("viewer_count", 0) if stream_info else 0,
                    "last_checked": datetime.now(timezone.utc).isoformat()
                }

            self.save_data()

            if not self.check_streams.is_running():
                self.check_streams.start()
                resultados.append("\n✅ Loop do monitor reiniciado!")

            embed = discord.Embed(
                title="✅ Verificação Manual Concluída",
                description="\n".join(resultados),
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"[TWITCH] Erro no force_check: {e}")
            await ctx.send(f"❌ Erro: {e}")


# ─────────────────────────────────────────────────────────────
# VIEWS DE GERENCIAMENTO
# ─────────────────────────────────────────────────────────────

class TwitchManagePanelView(discord.ui.View):
    """Botão persistente no painel de aprovação que abre a interface de gerenciamento."""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="⚙️ Gerenciar Canais",
        style=discord.ButtonStyle.secondary,
        custom_id="twitch_manage_panel_btn"
    )
    async def manage_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or \
                not any(r.id in config.MOD_ROLE_IDS for r in interaction.user.roles):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        if not self.cog.approved_channels:
            await interaction.response.send_message("⚠️ Nenhum canal aprovado para gerenciar.", ephemeral=True)
            return
        embed = discord.Embed(
            title="⚙️ Gerenciar Canais Twitch",
            description=f"**{len(self.cog.approved_channels)}** canal(is) aprovado(s). Selecione um canal:",
            color=discord.Color.from_rgb(145, 70, 255)
        )
        for username, user_id in self.cog.approved_channels.items():
            state = self.cog.stream_state.get(username, {})
            is_live = state.get("is_live", False)
            status = "🔴 Ao vivo" if is_live else "⚫ Offline"
            embed.add_field(
                name=username,
                value=f"{status}\n[twitch.tv/{username}](https://www.twitch.tv/{username})\n👤 <@{user_id}>",
                inline=True
            )
        await interaction.response.send_message(embed=embed, view=TwitchManageView(self.cog), ephemeral=True)


class TwitchManageView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=120)
        self.cog = cog
        self.selected: str | None = None

        options = [
            discord.SelectOption(label=username, value=username,
                                 description=f"ID Discord: {user_id}")
            for username, user_id in list(cog.approved_channels.items())[:25]
        ]
        self.select = discord.ui.Select(placeholder="Selecione um canal...", options=options)
        self.select.callback = self.on_select
        self.add_item(self.select)

        self.btn_remove = discord.ui.Button(label="🗑️ Remover", style=discord.ButtonStyle.red, disabled=True)
        self.btn_remove.callback = self.on_remove
        self.add_item(self.btn_remove)

        self.btn_edit = discord.ui.Button(label="✏️ Editar Username", style=discord.ButtonStyle.secondary, disabled=True)
        self.btn_edit.callback = self.on_edit
        self.add_item(self.btn_edit)

    async def on_select(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or \
                not any(r.id in config.MOD_ROLE_IDS for r in interaction.user.roles):
            await interaction.response.send_message("❌ Você não tem permissão!", ephemeral=True)
            return
        self.selected = self.select.values[0]
        self.btn_remove.disabled = False
        self.btn_edit.disabled = False
        await interaction.response.edit_message(
            content=f"Canal **`{self.selected}`** selecionado. Escolha uma ação:",
            view=self
        )

    async def on_remove(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or \
                not any(r.id in config.MOD_ROLE_IDS for r in interaction.user.roles):
            await interaction.response.send_message("❌ Você não tem permissão!", ephemeral=True)
            return
        if not self.selected or self.selected not in self.cog.approved_channels:
            await interaction.response.send_message("Canal não encontrado!", ephemeral=True)
            return
        del self.cog.approved_channels[self.selected]
        self.cog.stream_state.pop(self.selected, None)
        self.cog.save_data()
        await interaction.response.edit_message(
            content=f"✅ Canal `{self.selected}` **removido** do monitoramento Twitch!",
            view=None
        )
        self.stop()

    async def on_edit(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or \
                not any(r.id in config.MOD_ROLE_IDS for r in interaction.user.roles):
            await interaction.response.send_message("❌ Você não tem permissão!", ephemeral=True)
            return
        if not self.selected:
            await interaction.response.send_message("Selecione um canal primeiro!", ephemeral=True)
            return
        await interaction.response.send_modal(TwitchEditModal(self.cog, self.selected))


class TwitchEditModal(discord.ui.Modal, title="Editar Canal Twitch"):
    novo_username = discord.ui.TextInput(
        label="Novo username da Twitch",
        placeholder="novo_usuario (sem @ e sem URL)",
        min_length=2,
        max_length=50
    )

    def __init__(self, cog, old_username: str):
        super().__init__()
        self.cog = cog
        self.old_username = old_username

    async def on_submit(self, interaction: discord.Interaction):
        novo = self.novo_username.value.strip().lower()
        if "twitch.tv/" in novo:
            m = re.search(r'twitch\.tv/([a-zA-Z0-9_]+)', novo)
            if m:
                novo = m.group(1).lower()
        novo = novo.lstrip("@")

        if novo == self.old_username:
            await interaction.response.send_message("Nenhuma alteração feita.", ephemeral=True)
            return
        if novo in self.cog.approved_channels:
            await interaction.response.send_message(f"Canal `{novo}` já existe!", ephemeral=True)
            return

        user_id = self.cog.approved_channels.pop(self.old_username)
        self.cog.approved_channels[novo] = user_id
        state = self.cog.stream_state.pop(self.old_username, {})
        self.cog.stream_state[novo] = state
        self.cog.save_data()
        await interaction.response.send_message(
            f"✅ Canal atualizado: `{self.old_username}` → `{novo}` | [twitch.tv/{novo}](https://www.twitch.tv/{novo})"
        )


async def setup(bot):
    print(f"[TWITCH] 🚀 setup() chamado")
    cog = TwitchMonitorCog(bot)
    await bot.add_cog(cog)
    print(f"[TWITCH] ✅ TwitchMonitorCog adicionado ao bot!")
    logger.info("[TWITCH] ✅ TwitchMonitorCog adicionado ao bot!")
