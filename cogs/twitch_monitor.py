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

import config
from nicknameUpdater import update_member_nickname

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
        self.panels_created = False  # Flag para evitar recriação múltipla
        
        logger.info("[TWITCH] 🔧 TwitchMonitorCog inicializando...")
        print(f"[TWITCH] 📡 Carregando dados...")
        
        self.load_data()
        
        # Inicia monitor de streams apenas se credenciais estão configuradas
        if config.TWITCH_CLIENT_ID and config.TWITCH_ACCESS_TOKEN:
            try:
                print(f"[TWITCH] ✅ Credenciais encontradas, iniciando monitor...")
                self.check_streams.start()
                logger.info(f"[TWITCH] ✅ Monitor iniciado. {len(self.approved_channels)} canal(is)")
            except Exception as e:
                print(f"[TWITCH] ❌ Erro ao iniciar monitor: {e}")
                logger.error(f"[TWITCH] ❌ Erro ao iniciar monitor: {e}")
        else:
            print(f"[TWITCH] ⚠️ Credenciais não configuradas - Monitor desativado (painéis funcionam normalmente)")
            logger.warning("[TWITCH] ⚠️ Credenciais não configuradas - Monitor desativado (painéis funcionam normalmente)")
        
        print(f"[TWITCH] ✅ TwitchMonitorCog pronto!")
        logger.info("[TWITCH] ✅ TwitchMonitorCog pronto!")
    
    def cog_unload(self):
        if hasattr(self, 'check_streams') and self.check_streams.is_running():
            self.check_streams.cancel()
        logger.info("[TWITCH] Monitor cancelado")
    
    # ─────────────────────────────────────────────────────────────
    # INICIALIZAÇÃO AUTOMÁTICA
    # ─────────────────────────────────────────────────────────────
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Cria os painéis automaticamente ao iniciar o bot."""
        print(f"[TWITCH] 🚨 on_ready() CHAMADO!")
        logger.warning("[TWITCH] 🚨 on_ready() CHAMADO!")  # DEBUG
        
        # Evita recriação múltipla (on_ready pode ser chamado várias vezes)
        if self.panels_created:
            print(f"[TWITCH] ⏭️  Painéis já foram criados nesta sessão")
            logger.info("[TWITCH] Painéis já foram criados nesta sessão")
            return
        
        await self._create_panels_internal()
    
    async def force_create_panels(self):
        """Força recriação dos painéis (mesmo se já foram criados)."""
        print(f"[TWITCH] 💪 force_create_panels() chamado!")
        logger.info("[TWITCH] 💪 force_create_panels() chamado - ignorando flag")
        self.panels_created = False  # Reseta flag
        await self._create_panels_internal()
    
    async def _create_panels_internal(self):
        """Um interno que faz o trabalho de criar painéis."""
        print(f"[TWITCH] 🔍 Verificando canais...")
        print(f"[TWITCH]   • REQUEST ({CHANNEL_REQUEST}): {self.bot.get_channel(CHANNEL_REQUEST)}")
        print(f"[TWITCH]   • APPROVAL ({CHANNEL_APPROVAL}): {self.bot.get_channel(CHANNEL_APPROVAL)}")
        print(f"[TWITCH]   • NOTIF ({CHANNEL_NOTIF}): {self.bot.get_channel(CHANNEL_NOTIF)}")
        
        self.panels_created = True
        
        print(f"[TWITCH] 🔄 Bot ready! Recriando painéis automáticos...")
        logger.info("[TWITCH] 🔄 Bot ready! Recriando painéis automáticos...")
        await asyncio.sleep(1)  # Aguarda um pouco para garantir que canais estão prontos
        
        try:
            print(f"[TWITCH] 📝 Etapa 1: Criando painel de solicitação...")
            logger.info("[TWITCH] 📝 Etapa 1: Criando painel de solicitação...")
            await self._create_request_panel()
            print(f"[TWITCH] ✅ Painel de solicitação criado!")
            logger.info("[TWITCH] ✅ Painel de solicitação criado!")
            
            await asyncio.sleep(1)
            
            print(f"[TWITCH] 📋 Etapa 2: Atualizando painel de aprovação...")
            logger.info("[TWITCH] 📋 Etapa 2: Atualizando painel de aprovação...")
            await self._update_approval_panel()
            print(f"[TWITCH] ✅ Painel de aprovação atualizado!")
            logger.info("[TWITCH] ✅ Painel de aprovação atualizado!")
            
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
            os.makedirs("data", exist_ok=True)
            
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
            os.makedirs("data", exist_ok=True)
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
        """Headers para API Twitch (agora opcional - pode estar vazio)."""
        return {
            "Client-ID": config.TWITCH_CLIENT_ID or "unknown",
            "Authorization": f"Bearer {config.TWITCH_ACCESS_TOKEN}" if config.TWITCH_ACCESS_TOKEN else "Bearer unknown"
        }
    
    def _validate_channel_exists(self, username: str) -> bool:
        """
        Valida se o canal Twitch existe (versão simplificada).
        Tenta acessar o URL do canal e verifica se é válido.
        """
        if not username or len(username) < 3:
            return False
        
        # Valida characters válidos em username Twitch (alfanumérico + underscore)
        if not re.match(r"^[a-zA-Z0-9_]{3,25}$", username):
            logger.warning(f"[TWITCH] Username inválido (formato): {username}")
            return False
        
        try:
            # Tenta acessar a página do canal no site da Twitch
            url = f"https://www.twitch.tv/{username}"
            response = requests.head(url, timeout=TIMEOUT_REQUEST, allow_redirects=True)
            
            # Se conseguiu acessar e não foi redirecionado para 404, o canal existe
            if response.status_code in [200, 302]:
                logger.info(f"[TWITCH] ✅ Canal {username} validado (URL acessível)")
                return True
            else:
                logger.warning(f"[TWITCH] ❌ Canal {username} não encontrado (Status: {response.status_code})")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"[TWITCH] ⏱️ Timeout ao validar {username}")
            return False
        except Exception as e:
            logger.error(f"[TWITCH] Erro ao validar canal {username}: {e}")
            return False
    
    def _get_user_id(self, username: str) -> Optional[str]:
        """DESCONTINUADO - mantido para compatibilidade."""
        # Agora só valida via URL, não precisa de token
        if self._validate_channel_exists(username):
            return username  # Retorna o username como ID (simplificado)
        return None
    
    def _get_stream_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            url = f"{TWITCH_API_BASE}/streams"
            params = {"user_id": user_id}
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=TIMEOUT_REQUEST)
            response.raise_for_status()
            data = response.json()
            if data.get("data"):
                return data["data"][0]
        except Exception as e:
            logger.error(f"[TWITCH] Erro ao obter stream: {e}")
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
            twitch_id = self._get_user_id(username)
            if not twitch_id:
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
                    await update_member_nickname(member)
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
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3670/3670147.png")
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
                msg = await channel.send(embed=embed)
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
                
                embed.add_field(
                    name=f"#{idx} - {username.upper()}",
                    value=f"👤 De: {user_name}\n⏰ Solicitado em: {req_time[:10]}\n\n🔑 ID: `{req_id}`",
                    inline=False
                )
            
            embed.set_footer(text="Monitor Twitch 📺 • Clique em Aprovar ou Rejeitar • Criado automaticamente ao iniciar o bot")
            
            print(f"[TWITCH]     - Enviando painel...")
            for req_id, data in self.pending_requests.items():
                msg = await channel.send(embed=embed, view=ApprovalButtonView(self, req_id, data.get("username", "?")))
                logger.info(f"[TWITCH] 📤 Painel de aprovação enviado! Mensagem ID: {msg.id}")
                break
            
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
                twitch_id = self._get_user_id(username)
                if not twitch_id:
                    continue
                
                stream_info = self._get_stream_info(twitch_id)
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
    
    async def _send_live_notification(self, stream_info: Dict[str, Any], user_id_discord: int):
        """Envia notificação quando alguém entra ao vivo."""
        try:
            channel = cast(discord.TextChannel, self.bot.get_channel(CHANNEL_NOTIF))
            if not channel:
                return
            
            username = stream_info.get("user_name", "?")
            title = stream_info.get("title", "Sem título")
            game = stream_info.get("game_name", "Jogo misterioso")
            viewers = stream_info.get("viewer_count", 0)
            thumbnail = stream_info.get("thumbnail_url", "")
            
            # Mensagens bem-humoradas
            mensagens_humor = [
                f"🚨 ALERTA VERMELHO! {username.upper()} COMEÇOU A TRANSMITIR! 🚨",
                f"🎮 SAIAM DO BURACO! {username} está ao vivo na Twitch!",
                f"📢 ATENÇÃO CIDADÃOS! Temos uma transmissão ao vivo de {username}!",
                f"🔴 TRANSMISSÃO ATIVA! {username} está dominando a Twitch!",
                f"⚡ CHOQUE! {username} apareceu na Twitch! Todos os olhos em cima!",
                f"🎬 LIVE DETECTADA! {username} está tirando a galera do soco!",
            ]
            
            import random
            mensagem = random.choice(mensagens_humor)
            
            embed = discord.Embed(
                title=f"🔴 {username}",
                description=f"**{title}**",
                color=discord.Color.from_rgb(145, 70, 255),
                url=f"https://www.twitch.tv/{username}"
            )
            embed.add_field(name="🎮 Jogo", value=game, inline=True)
            embed.add_field(name="👥 Espectadores", value=f"{viewers:,}", inline=True)
            
            if thumbnail:
                thumb = thumbnail.replace("{width}", "320").replace("{height}", "180")
                embed.set_thumbnail(url=thumb)
            
            embed.timestamp = datetime.now(timezone.utc)
            embed.set_footer(text="Monitor Twitch 📺 • Clique no botão para ir à live!")
            
            mention = f"<@{user_id_discord}>" if user_id_discord else username
            
            await channel.send(
                f"{mention} 👋",
                embed=embed,
                view=LiveButtonView(username)
            )
            
            logger.info(f"[TWITCH] 🔴 Notificação ao vivo: {username}")
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
        """[TODOS] Ver status dos canais."""
        try:
            if not self.approved_channels:
                embed = discord.Embed(
                    title="📺 Status dos Canais",
                    description="Nenhum canal monitorado ainda!",
                    color=discord.Color.red()
                )
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
                
                if is_live:
                    title = state.get("title", "Sem título")
                    game = state.get("game", "?")
                    viewers = state.get("viewers", 0)
                    value = f"🔴 **AO VIVO**\n{title}\nJogo: {game}\nEspectadores: {viewers:,}"
                else:
                    value = "⚫ Offline"
                
                embed.add_field(name=f"{username.upper()}", value=value, inline=False)
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Erro: {e}")


async def setup(bot):
    print(f"[TWITCH] 🚀 setup() chamado")
    cog = TwitchMonitorCog(bot)
    await bot.add_cog(cog)
    print(f"[TWITCH] ✅ TwitchMonitorCog adicionado ao bot!")
    logger.info("[TWITCH] ✅ TwitchMonitorCog adicionado ao bot!")
