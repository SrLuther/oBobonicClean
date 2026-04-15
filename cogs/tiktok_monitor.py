# cogs/tiktok_monitor.py
# Sistema de monitoramento TikTok com painéis e botões
# Solicitação → Aprovação → Notificação ao Vivo
#
# Usa TikTokLive (lib não-oficial via websocket reverso)
# pip install TikTokLive

import discord
from discord.ext import commands, tasks
import json
import os
import logging
import re
import asyncio
from typing import Dict, Any, Optional, cast
from datetime import datetime, timezone

import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────────────────────

APPROVED_FILE = ".bancos/tiktok_approved.json"
PENDING_FILE  = ".bancos/tiktok_pending.json"
STATE_FILE    = ".bancos/tiktok_monitor_state.json"

CHANNEL_REQUEST  = config.TIKTOK_CHANNEL_REQUEST
CHANNEL_APPROVAL = config.TIKTOK_CHANNEL_APPROVAL
CHANNEL_NOTIF    = config.TIKTOK_CHANNEL_NOTIF

TIKTOK_ROLE_ID = 1492687604418740315   # mesmo cargo do Twitch (Streamer) — ajuste se quiser separar

print(f"[TIKTOK] 🔌 IDs do TikTok carregados:")
print(f"[TIKTOK]   • REQUEST:  {CHANNEL_REQUEST}")
print(f"[TIKTOK]   • APPROVAL: {CHANNEL_APPROVAL}")
print(f"[TIKTOK]   • NOTIF:    {CHANNEL_NOTIF}")


# ─────────────────────────────────────────────────────────────
# VIEWS (BOTÕES)
# ─────────────────────────────────────────────────────────────

class TikTokRequestButtonView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="📌 Solicitar Adição de Canal",
        style=discord.ButtonStyle.primary,
        custom_id="tiktok_request_btn"
    )
    async def request_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TikTokRequestModal(self.cog))


class TikTokRequestModal(discord.ui.Modal, title="Adicionar Canal TikTok"):
    channel = discord.ui.TextInput(
        label="Username do TikTok",
        placeholder="@seu_usuario ou seu_usuario",
        required=True,
        min_length=2,
        max_length=50
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.process_request(interaction, self.channel.value)


class TikTokApprovalButtonView(discord.ui.View):
    def __init__(self, cog, request_id: str):
        super().__init__(timeout=None)
        self.cog = cog
        self.request_id = request_id

    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.green)
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_approval(interaction, self.request_id, True)

    @discord.ui.button(label="❌ Rejeitar", style=discord.ButtonStyle.red)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_approval(interaction, self.request_id, False)


class TikTokLiveButtonView(discord.ui.View):
    def __init__(self, username: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="🎬 Ir para a Live",
            style=discord.ButtonStyle.link,
            url=f"https://www.tiktok.com/@{username}/live"
        ))


# ─────────────────────────────────────────────────────────────
# COG PRINCIPAL
# ─────────────────────────────────────────────────────────────

class TikTokMonitorCog(commands.Cog):
    """Sistema de monitoramento TikTok com painéis e botões."""

    FRASES_LIVE = [
        "largou tudo e foi transmitir no TikTok. Cola lá antes que acabe!",
        "está ao vivo no TikTok. Não adianta fingir que não viu.",
        "ligou a câmera agora mesmo. Bora assistir?",
        "entrou ao vivo — precisa de audiência, e você sabe disso.",
        "abriu a transmissão. O chat tá esperando reforço.",
        "está transmitindo neste exato momento. Vai perder?",
        "colocou o 'ao vivo' pra funcionar. Passa lá depois desse missão.",
        "acabou de iniciar uma live. Dá uma chance, pode ser épico.",
        "tá ao vivo e o servidor inteiro foi avisado. Agora é com você.",
        "iniciou a transmissão — o botão tá logo ali embaixo.",
    ]

    def __init__(self, bot: commands.Bot):
        print("[TIKTOK] 🔧 TikTokMonitorCog.__init__() CHAMADO")
        self.bot = bot
        self.approved_channels: Dict[str, int] = {}   # username → discord_user_id
        self.pending_requests: Dict[str, Dict] = {}
        self.stream_state: Dict[str, bool] = {}        # username → is_live bool
        self._startup_task: Optional[asyncio.Task] = None
        self.load_data()
        print("[TIKTOK] ✅ TikTokMonitorCog pronto!")

    # ─── lifecycle ────────────────────────────────────────────

    async def cog_load(self) -> None:
        self._startup_task = asyncio.create_task(self._startup())
        print("[TIKTOK] 🚀 Task de startup criada.")

    def cog_unload(self):
        if self._startup_task and not self._startup_task.done():
            self._startup_task.cancel()
        if self.check_streams.is_running():
            self.check_streams.cancel()
        logger.info("[TIKTOK] Monitor cancelado")

    # ─── startup ──────────────────────────────────────────────

    async def _startup(self) -> None:
        try:
            await self.bot.wait_until_ready()
            print("[TIKTOK] ⏳ Bot pronto! Iniciando startup...")

            # Zera estado para garantir que lives ativas sejam notificadas
            self.stream_state = {}
            self.save_data()
            print("[TIKTOK] 🔄 Estado resetado — lives ativas serão notificadas na primeira varredura")

            if not self.check_streams.is_running():
                self.check_streams.start()
                logger.info(f"[TIKTOK] ✅ Monitor iniciado. {len(self.approved_channels)} canal(is) aprovado(s)")

            await self._create_panels_internal()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[TIKTOK] ❌ Erro no startup: {e}")
            logger.error(f"[TIKTOK] ❌ Erro no startup: {e}")
            import traceback
            traceback.print_exc()

    # ─── persistência ─────────────────────────────────────────

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
            logger.error(f"[TIKTOK] Erro ao carregar: {e}")

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
            logger.error(f"[TIKTOK] Erro ao salvar: {e}")

    # ─── utilitários ──────────────────────────────────────────

    def _extract_username(self, raw: str) -> str:
        """Normaliza username: remove @, espaços e URLs."""
        raw = raw.strip()
        if "tiktok.com/@" in raw:
            match = re.search(r'tiktok\.com/@([a-zA-Z0-9_.]+)', raw)
            if match:
                return match.group(1).lower()
        return raw.lstrip("@").lower()

    async def _is_live(self, username: str) -> bool:
        """Verifica se o canal está ao vivo via TikTokLive."""
        try:
            from TikTokLive import TikTokLiveClient
            client = TikTokLiveClient(unique_id=username)
            result = await asyncio.wait_for(client.is_live(), timeout=15)
            print(f"[TIKTOK]   is_live(@{username}) → {result}")
            return bool(result)
        except asyncio.TimeoutError:
            print(f"[TIKTOK]   ⏱️ Timeout ao checar @{username}")
            logger.warning(f"[TIKTOK] Timeout ao checar live de {username}")
            return False
        except Exception as e:
            print(f"[TIKTOK]   ❌ Erro ao checar @{username}: {e}")
            logger.warning(f"[TIKTOK] Erro ao checar live de {username}: {e}")
            return False

    async def _user_exists(self, username: str) -> bool:
        """Valida se o username existe no TikTok (tenta checar live — se não der erro 404, existe)."""
        try:
            from TikTokLive import TikTokLiveClient
            client = TikTokLiveClient(unique_id=username)
            await asyncio.wait_for(client.is_live(), timeout=15)
            return True
        except asyncio.TimeoutError:
            return True   # timeout ≠ inexistente
        except Exception as e:
            err = str(e).lower()
            if "not found" in err or "404" in err or "invalid" in err:
                return False
            return True   # erro de rede, assume que existe

    # ─── solicitações ─────────────────────────────────────────

    async def process_request(self, interaction: discord.Interaction, input_text: str):
        await interaction.response.defer(thinking=True)
        try:
            username = self._extract_username(input_text)

            if not re.match(r'^[a-zA-Z0-9_.]{2,50}$', username):
                await interaction.followup.send(
                    "❌ **Username inválido!**\nUse apenas letras, números, `_` e `.`",
                    ephemeral=True
                )
                return

            if username in self.approved_channels:
                await interaction.followup.send(
                    f"⚠️ Canal `@{username}` já está monitorado!", ephemeral=True
                )
                return

            for req in self.pending_requests.values():
                if req.get("username") == username:
                    await interaction.followup.send(
                        f"⏳ Canal `@{username}` já tem solicitação pendente!", ephemeral=True
                    )
                    return

            exists = await self._user_exists(username)
            if not exists:
                await interaction.followup.send(
                    f"❌ Canal `@{username}` não encontrado no TikTok!\nVerifique o username e tente novamente.",
                    ephemeral=True
                )
                return

            request_id = f"{interaction.user.id}_{username}_{datetime.now().timestamp()}"
            self.pending_requests[request_id] = {
                "username": username,
                "user_id": interaction.user.id,
                "user_name": str(interaction.user),
                "user_avatar": interaction.user.display_avatar.url,
                "requested_at": datetime.now(timezone.utc).isoformat()
            }
            self.save_data()

            embed = discord.Embed(
                title="✅ Solicitação Enviada!",
                description=f"Seu canal `@{username}` foi enviado para aprovação.",
                color=discord.Color.green()
            )
            embed.add_field(name="Canal", value=f"`@{username}`", inline=True)
            embed.add_field(name="Status", value="⏳ Aguardando aprovação", inline=True)
            embed.set_footer(text="Um admin analisará sua solicitação em breve!")
            await interaction.followup.send(embed=embed, ephemeral=True)

            await self._update_approval_panel()
            logger.info(f"[TIKTOK] Solicitação de {interaction.user}: @{username}")

        except Exception as e:
            logger.error(f"[TIKTOK] Erro na solicitação: {e}")
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

    async def handle_approval(self, interaction: discord.Interaction, request_id: str, approve: bool):
        await interaction.response.defer(thinking=True)

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
        user_id  = req_data.get("user_id", 0)

        if approve:
            self.approved_channels[username] = user_id
            del self.pending_requests[request_id]
            self.save_data()

            if not self.check_streams.is_running():
                self.check_streams.start()

            await interaction.followup.send(
                f"✅ Canal `@{username}` **aprovado** e adicionado ao monitoramento!",
                ephemeral=True
            )

            # Cargo
            try:
                guild  = interaction.guild
                member = guild.get_member(user_id)
                if member:
                    role = guild.get_role(TIKTOK_ROLE_ID)
                    if role:
                        await member.add_roles(role)
            except Exception as e:
                logger.warning(f"[TIKTOK] Erro ao adicionar cargo: {e}")

            # DM
            try:
                member = await self.bot.fetch_user(user_id)
                embed_dm = discord.Embed(
                    title="✅ Canal Aprovado!",
                    description=f"Seu canal TikTok `@{username}` foi **aprovado**! 🎉",
                    color=discord.Color.green()
                )
                embed_dm.add_field(
                    name="O que acontece agora?",
                    value=f"Quando você iniciar uma transmissão, o servidor será notificado em <#{CHANNEL_NOTIF}>!",
                    inline=False
                )
                await member.send(embed=embed_dm)
            except Exception:
                pass

            logger.info(f"[TIKTOK] {interaction.user} aprovou: @{username}")

        else:
            del self.pending_requests[request_id]
            self.save_data()

            await interaction.followup.send(
                f"❌ Solicitação de `@{username}` **rejeitada**!", ephemeral=True
            )

            try:
                member = await self.bot.fetch_user(user_id)
                embed_dm = discord.Embed(
                    title="❌ Solicitação Rejeitada",
                    description=f"Sua solicitação para `@{username}` foi rejeitada.",
                    color=discord.Color.red()
                )
                await member.send(embed=embed_dm)
            except Exception:
                pass

            logger.info(f"[TIKTOK] {interaction.user} rejeitou: @{username}")

        await self._update_approval_panel()

    # ─── painéis ──────────────────────────────────────────────

    async def _create_panels_internal(self):
        print("[TIKTOK] 🔄 Recriando painéis...")
        try:
            await self._create_request_panel()
            await asyncio.sleep(1)
            await self._update_approval_panel()
            print("[TIKTOK] 🎉 Painéis criados com sucesso!")
        except Exception as e:
            logger.error(f"[TIKTOK] Erro ao criar painéis: {e}")
            import traceback
            traceback.print_exc()

    async def _create_request_panel(self):
        channel = cast(discord.TextChannel, self.bot.get_channel(CHANNEL_REQUEST))
        if not channel:
            logger.error(f"[TIKTOK] Canal REQUEST {CHANNEL_REQUEST} não encontrado!")
            return

        async for msg in channel.history(limit=100):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception:
                    pass

        embed = discord.Embed(
            title="🎵 Solicitar Adição de Canal TikTok",
            description=(
                "Quer que sua live no TikTok seja anunciada aqui no servidor?\n\n"
                "🎬 **Como funciona:**\n"
                "1. Clique no botão abaixo\n"
                "2. Insira seu username do TikTok\n"
                "3. Um admin analisará e aprovará\n"
                "4. Quando você estiver ao vivo, o servidor será notificado!\n\n"
                "✨ **Benefícios:**\n"
                "• A comunidade sabe quando você está transmitindo\n"
                "• Notificação automática no canal dedicado\n"
                "• Aumenta seu engajamento"
            ),
            color=discord.Color.from_rgb(238, 29, 82)   # rosa TikTok
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3046/3046121.png")
        embed.set_footer(text="Monitor TikTok 🎵 • Criado automaticamente ao iniciar o bot")

        await channel.send(embed=embed, view=TikTokRequestButtonView(self))
        logger.info("[TIKTOK] Painel de solicitação criado!")

    async def _update_approval_panel(self):
        channel = cast(discord.TextChannel, self.bot.get_channel(CHANNEL_APPROVAL))
        if not channel:
            logger.error(f"[TIKTOK] Canal APPROVAL {CHANNEL_APPROVAL} não encontrado!")
            return

        async for msg in channel.history(limit=100):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception:
                    pass

        if not self.pending_requests:
            embed = discord.Embed(
                title="📋 Aprovação TikTok",
                description="✅ Nenhuma solicitação pendente!",
                color=discord.Color.green()
            )
            embed.set_footer(text="Monitor TikTok 🎵")
            await channel.send(embed=embed, view=TikTokManagePanelView(self))
            return

        embed = discord.Embed(
            title="📋 Aprovação de Canais TikTok",
            description=f"**Total:** {len(self.pending_requests)} solicitação(ões)",
            color=discord.Color.blue()
        )

        for idx, (req_id, data) in enumerate(self.pending_requests.items(), 1):
            username = data.get("username", "?")
            user_name = data.get("user_name", "?")
            req_time = data.get("requested_at", "?")[:10]
            profile_url = f"https://www.tiktok.com/@{username}"
            embed.add_field(
                name=f"#{idx} — @{username}",
                value=(
                    f"👤 De: {user_name}\n"
                    f"⏰ Em: {req_time}\n"
                    f"🔗 Perfil: [tiktok.com/@{username}]({profile_url})\n\n"
                    f"🔑 ID: `{req_id}`"
                ),
                inline=False
            )

        embed.set_footer(text="Monitor TikTok 🎵 • Clique em Aprovar ou Rejeitar")

        for req_id in self.pending_requests:
            await channel.send(embed=embed, view=TikTokApprovalButtonView(self, req_id))
            break
        # Botão de gerenciamento separado
        await channel.send(view=TikTokManagePanelView(self))

    # ─── loop de monitoramento ────────────────────────────────

    @tasks.loop(minutes=5)
    async def check_streams(self):
        """Verifica lives TikTok a cada 5 minutos."""
        if not self.approved_channels:
            print("[TIKTOK] ⏭️ check_streams: nenhum canal aprovado, pulando...")
            return

        print(f"[TIKTOK] 🔍 check_streams: verificando {len(self.approved_channels)} canal(is)...")
        changed = False
        for username, user_id_discord in list(self.approved_channels.items()):
            is_live  = await self._is_live(username)
            was_live = self.stream_state.get(username, False)
            print(f"[TIKTOK]   @{username}: live={is_live}, was_live={was_live}")

            if is_live and not was_live:
                print(f"[TIKTOK] 🔴 NOVA LIVE DETECTADA: @{username} — enviando notificação...")
                await self._send_live_notification(username, user_id_discord)

            self.stream_state[username] = is_live
            changed = True

        if changed:
            self.save_data()
        print("[TIKTOK] ✅ check_streams concluído.")

    @check_streams.before_loop
    async def before_check_streams(self):
        await self.bot.wait_until_ready()

    # ─── notificação ──────────────────────────────────────────

    async def _send_live_notification(self, username: str, user_id_discord: int):
        try:
            channel = cast(discord.TextChannel, self.bot.get_channel(CHANNEL_NOTIF))
            if not channel:
                return

            import random
            frase = random.choice(self.FRASES_LIVE)
            stream_url = f"https://www.tiktok.com/@{username}/live"

            embed = discord.Embed(
                description=(
                    f"### 🔴 Ao Vivo no TikTok\n"
                    f"**{username}** {frase}\n"
                ),
                color=discord.Color.from_rgb(238, 29, 82),
                url=stream_url,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(
                name=f"{username}  •  TikTok",
                url=stream_url,
                icon_url="https://cdn-icons-png.flaticon.com/512/3046/3046121.png"
            )
            embed.set_footer(text="TikTok • Monitor de Lives")

            mention = f"<@{user_id_discord}>" if user_id_discord else f"**{username}**"

            await channel.send(
                content=f"{mention} está **ao vivo** no TikTok agora! 🔴",
                embed=embed,
                view=TikTokLiveButtonView(username)
            )

            logger.info(f"[TIKTOK] 🔴 Notificação ao vivo: @{username}")
        except Exception as e:
            logger.error(f"[TIKTOK] Erro ao notificar: {e}")

    # ─── comandos ─────────────────────────────────────────────

    @commands.command(name="tiktok_status")
    async def tiktok_status(self, ctx: commands.Context):
        """[TODOS] Ver status dos canais TikTok monitorados."""
        loop_status = "🟢 Rodando" if self.check_streams.is_running() else "🔴 PARADO"

        if not self.approved_channels:
            embed = discord.Embed(
                title="🎵 Status TikTok",
                description="Nenhum canal monitorado ainda!",
                color=discord.Color.red()
            )
            embed.add_field(name="⚙️ Monitor", value=loop_status, inline=True)
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="🎵 Status dos Canais TikTok",
            description=f"Total: {len(self.approved_channels)} canal(is)",
            color=discord.Color.from_rgb(238, 29, 82)
        )

        for username in self.approved_channels:
            is_live = self.stream_state.get(username, False)
            value = "🔴 **AO VIVO**" if is_live else "⚫ Offline"
            embed.add_field(name=f"@{username}", value=value, inline=False)

        embed.add_field(name="⚙️ Loop monitor", value=loop_status, inline=True)
        embed.set_footer(text="Use !tiktok_force_check para verificar agora")
        await ctx.send(embed=embed)

    @commands.command(name="tiktok_force_check")
    @commands.has_any_role(*config.MOD_ROLE_IDS)
    async def tiktok_force_check(self, ctx: commands.Context):
        """[ADMIN] Força verificação imediata de todas as lives TikTok."""
        await ctx.send("🔍 Verificando lives TikTok agora...")

        if not self.approved_channels:
            await ctx.send("⚠️ Nenhum canal aprovado.")
            return

        resultados = []
        for username, user_id_discord in list(self.approved_channels.items()):
            is_live  = await self._is_live(username)
            was_live = self.stream_state.get(username, False)

            if is_live and not was_live:
                await self._send_live_notification(username, user_id_discord)
                resultados.append(f"🔴 **@{username}** — AO VIVO (notificação enviada!)")
            elif is_live:
                resultados.append(f"🔴 **@{username}** — ao vivo (já notificado antes)")
            else:
                resultados.append(f"⚫ **@{username}** — offline")

            self.stream_state[username] = is_live

        self.save_data()

        if not self.check_streams.is_running():
            self.check_streams.start()
            resultados.append("\n✅ Loop do monitor reiniciado!")

        embed = discord.Embed(
            title="✅ Verificação TikTok Concluída",
            description="\n".join(resultados),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="tiktok_rebuild_panels")
    @commands.has_any_role(*config.MOD_ROLE_IDS)
    async def tiktok_rebuild_panels(self, ctx: commands.Context):
        """[ADMIN] Reconstrói os painéis TikTok do zero."""
        await ctx.send("🔄 Reconstruindo painéis TikTok...")
        await self._create_panels_internal()
        await ctx.send("✅ Painéis reconstruídos!")

    @commands.command(name="tiktok_gerenciar")
    @commands.has_any_role(*config.MOD_ROLE_IDS)
    async def tiktok_gerenciar(self, ctx: commands.Context):
        """[ADMIN] Gerenciar canais TikTok aprovados (remover, editar)."""
        if not self.approved_channels:
            await ctx.send("⚠️ Nenhum canal aprovado para gerenciar.")
            return

        embed = discord.Embed(
            title="⚙️ Gerenciar Canais TikTok",
            description=f"**{len(self.approved_channels)}** canal(is) aprovado(s).\nSelecione um canal no menu abaixo:",
            color=discord.Color.from_rgb(238, 29, 82)
        )
        for username, user_id in self.approved_channels.items():
            is_live = self.stream_state.get(username, False)
            status = "🔴 Ao vivo" if is_live else "⚫ Offline"
            embed.add_field(
                name=f"@{username}",
                value=f"{status}\n[tiktok.com/@{username}](https://www.tiktok.com/@{username})\n👤 <@{user_id}>",
                inline=True
            )
        embed.set_footer(text="Selecione um canal e escolha Remover ou Editar Username")
        await ctx.send(embed=embed, view=TikTokManageView(self))


# ─────────────────────────────────────────────────────────────
# VIEWS DE GERENCIAMENTO
# ─────────────────────────────────────────────────────────────

class TikTokManagePanelView(discord.ui.View):
    """Botão persistente no painel de aprovação que abre a interface de gerenciamento."""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="⚙️ Gerenciar Canais",
        style=discord.ButtonStyle.secondary,
        custom_id="tiktok_manage_panel_btn"
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
            title="⚙️ Gerenciar Canais TikTok",
            description=f"**{len(self.cog.approved_channels)}** canal(is) aprovado(s). Selecione um canal:",
            color=discord.Color.from_rgb(238, 29, 82)
        )
        for username, user_id in self.cog.approved_channels.items():
            is_live = self.cog.stream_state.get(username, False)
            status = "🔴 Ao vivo" if is_live else "⚫ Offline"
            embed.add_field(
                name=f"@{username}",
                value=f"{status}\n[tiktok.com/@{username}](https://www.tiktok.com/@{username})\n👤 <@{user_id}>",
                inline=True
            )
        await interaction.response.send_message(embed=embed, view=TikTokManageView(self.cog), ephemeral=True)


class TikTokManageView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=120)
        self.cog = cog
        self.selected: str | None = None

        options = [
            discord.SelectOption(label=f"@{username}", value=username,
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
            content=f"Canal **`@{self.selected}`** selecionado. Escolha uma ação:",
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
            content=f"✅ Canal `@{self.selected}` **removido** do monitoramento TikTok!",
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
        await interaction.response.send_modal(TikTokEditModal(self.cog, self.selected))


class TikTokEditModal(discord.ui.Modal, title="Editar Canal TikTok"):
    novo_username = discord.ui.TextInput(
        label="Novo username do TikTok",
        placeholder="novo_usuario (sem @ e sem URL)",
        min_length=2,
        max_length=50
    )

    def __init__(self, cog, old_username: str):
        super().__init__()
        self.cog = cog
        self.old_username = old_username

    async def on_submit(self, interaction: discord.Interaction):
        novo = self.novo_username.value.strip().lstrip("@").lower()
        if "tiktok.com/@" in novo:
            m = re.search(r'tiktok\.com/@([a-zA-Z0-9_.]+)', novo)
            if m:
                novo = m.group(1).lower()

        if novo == self.old_username:
            await interaction.response.send_message("Nenhuma alteração feita.", ephemeral=True)
            return
        if novo in self.cog.approved_channels:
            await interaction.response.send_message(f"Canal `@{novo}` já existe!", ephemeral=True)
            return

        user_id = self.cog.approved_channels.pop(self.old_username)
        self.cog.approved_channels[novo] = user_id
        state = self.cog.stream_state.pop(self.old_username, False)
        self.cog.stream_state[novo] = state
        self.cog.save_data()
        await interaction.response.send_message(
            f"✅ Canal atualizado: `@{self.old_username}` → `@{novo}` | [tiktok.com/@{novo}](https://www.tiktok.com/@{novo})"
        )


async def setup(bot: commands.Bot):
    print("[TIKTOK] 🚀 setup() chamado")
    await bot.add_cog(TikTokMonitorCog(bot))
    print("[TIKTOK] ✅ TikTokMonitorCog adicionado ao bot!")
