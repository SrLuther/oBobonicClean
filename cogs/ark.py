# cogs/ark.py
# Integração RCON + controle de serviços para ARK: Survival Evolved
# Protocolo RCON: Source RCON (Valve)
# Controle de serviço: systemctl (bot roda na mesma VPS que os servidores)
#
# Variáveis de ambiente (.env):
#   ARK_HOST=<IP padrão>
#   ARK_RCON_PASSWORD=<senha RCON padrão>
#
#   ARK_MAP1_NAME=TheIsland
#   ARK_MAP1_PORT=27020
#   ARK_MAP1_SERVICE=ark-theisland.service   ← necessário para ligar/desligar/reiniciar
#
#   ARK_MAP2_NAME=Ragnarok
#   ARK_MAP2_PORT=27021
#   ARK_MAP2_SERVICE=ark-ragnarok.service
#   ... (ARK_MAP3_*, ARK_MAP4_*, etc.)
#
#   Opcionais por mapa: ARK_MAPx_HOST, ARK_MAPx_PASSWORD

import asyncio
import discord
from discord.ext import commands
from datetime import datetime

import config

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────

TIMEOUT_RCON       = 8    # segundos para respostas RCON
TIMEOUT_SYSTEMCTL  = 30   # segundos para operações de start/stop/restart
CONFIRM_TIMEOUT    = 30   # segundos para o usuário confirmar ação


# ──────────────────────────────────────────────
# Helper RCON
# ──────────────────────────────────────────────

def _rcon_run_sync(host: str, port: int, password: str, command: str) -> str:
    from rcon import Client
    with Client(host, port, passwd=password, timeout=TIMEOUT_RCON) as client:
        return client.run(command)


async def rcon_run(host: str, port: int, password: str, command: str) -> str:
    return await asyncio.to_thread(_rcon_run_sync, host, port, password, command)


# ──────────────────────────────────────────────
# Helper systemctl
# ──────────────────────────────────────────────

async def systemctl(action: str, service: str) -> tuple[int, str, str]:
    """Executa 'systemctl <action> <service>' e retorna (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "systemctl", action, service,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SYSTEMCTL)
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", "Timeout ao executar systemctl"
    return proc.returncode or 0, stdout.decode().strip(), stderr.decode().strip()


# ──────────────────────────────────────────────
# Helpers utilitários
# ──────────────────────────────────────────────

def _resolve_map(name_input: str) -> dict | None:
    key = name_input.lower()
    if key in config.ARK_MAPS:
        return config.ARK_MAPS[key]
    for k, v in config.ARK_MAPS.items():
        if key in k:
            return v
    return None


def _map_list_text() -> str:
    if not config.ARK_MAPS:
        return "_Nenhum mapa configurado_"
    return ", ".join(f"`{v['name']}`" for v in config.ARK_MAPS.values())


# ──────────────────────────────────────────────
# View de confirmação com botões
# ──────────────────────────────────────────────

class ConfirmView(discord.ui.View):
    def __init__(self, author: discord.abc.User, *, timeout: float = CONFIRM_TIMEOUT):
        super().__init__(timeout=timeout)
        self.author = author
        self.confirmed: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "❌ Somente quem executou o comando pode confirmar.", ephemeral=True
            )
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


# ──────────────────────────────────────────────
# Cog
# ──────────────────────────────────────────────

class ArkCog(commands.Cog, name="ARK RCON"):
    """Comandos de integração RCON e controle dos servidores ARK."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        """Bloqueia todos os comandos ARK fora do canal permitido ou sem permissão de admin."""
        # 1. Verifica o canal
        if ctx.channel.id != config.ARK_CANAL_RCON_ID:  # type: ignore[union-attr]
            try:
                await ctx.message.delete()
            except Exception:
                pass
            canal = ctx.guild.get_channel(config.ARK_CANAL_RCON_ID) if ctx.guild else None
            mencao = canal.mention if canal else f"<#{config.ARK_CANAL_RCON_ID}>"
            await ctx.send(
                f"🔒 Comandos ARK só podem ser usados em {mencao}.",
                delete_after=8,
            )
            return False

        # 2. Verifica permissão de administrador
        if not ctx.author.guild_permissions.administrator:  # type: ignore[union-attr]
            try:
                await ctx.message.delete()
            except Exception:
                pass
            await ctx.send(
                "🔒 Apenas administradores podem usar os comandos ARK.",
                delete_after=8,
            )
            return False

        return True

    # ── !arkmapas ─────────────────────────────────────────────────
    @commands.command(name="arkmapas", aliases=["arkmaps", "arkservers"])
    @commands.has_permissions(administrator=True)
    async def ark_mapas(self, ctx: commands.Context):
        """Lista todos os mapas ARK configurados."""
        if not config.ARK_MAPS:
            await ctx.send("❌ Nenhum mapa ARK configurado no `.env`.")
            return

        embed = discord.Embed(
            title="🗺️ Mapas ARK Configurados",
            color=discord.Color.og_blurple(),
            timestamp=datetime.now(),
        )
        for _, info in config.ARK_MAPS.items():
            service_txt = f"`{info['service']}`" if info.get("service") else "_não configurado_"
            embed.add_field(
                name=info["name"],
                value=(
                    f"**Host:** `{info['host']}`\n"
                    f"**Porta RCON:** `{info['port']}`\n"
                    f"**Serviço:** {service_txt}"
                ),
                inline=True,
            )
        embed.set_footer(text="Use !arkstatus para verificar quais estão online")
        await ctx.send(embed=embed)

    # ── !arkstatus [mapa] ──────────────────────────────────────────
    @commands.command(name="arkstatus", aliases=["arkserver", "arkinfo"])
    @commands.has_permissions(administrator=True)
    async def ark_status(self, ctx: commands.Context, mapa: str | None = None):
        """Exibe o status (online/offline e jogadores) de um ou todos os mapas."""
        if not config.ARK_MAPS:
            await ctx.send("❌ Nenhum mapa ARK configurado.")
            return

        if mapa:
            found = _resolve_map(mapa)
            if not found:
                await ctx.send(f"❌ Mapa `{mapa}` não encontrado. Disponíveis: {_map_list_text()}")
                return
            targets = [found]
        else:
            targets = list(config.ARK_MAPS.values())

        msg = await ctx.send("🔄 Verificando servidores ARK, aguarde...")

        embed = discord.Embed(
            title="🦕 Status dos Servidores ARK",
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )
        embed.set_footer(text=f"Solicitado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

        async def check_map(info: dict) -> tuple[str, bool, str]:
            try:
                response = await asyncio.wait_for(
                    rcon_run(info["host"], info["port"], info["password"], "listplayers"),
                    timeout=TIMEOUT_RCON + 2,
                )
                return info["name"], True, response.strip()
            except Exception as e:
                return info["name"], False, str(e)

        results = await asyncio.gather(*[check_map(t) for t in targets])

        all_offline = True
        for name, online, data in results:
            if online:
                all_offline = False
                if "No Players Connected" in data or not data:
                    player_info = "_Nenhum jogador conectado_"
                else:
                    lines = [l.strip() for l in data.splitlines() if l.strip()]
                    player_info = f"{len(lines)} jogador(es) conectado(s)"
                embed.add_field(
                    name=f"🟢 {name}",
                    value=f"**Status:** Online\n**Jogadores:** {player_info}",
                    inline=True,
                )
            else:
                embed.add_field(
                    name=f"🔴 {name}",
                    value="**Status:** Offline ou inacessível",
                    inline=True,
                )

        if all_offline:
            embed.color = discord.Color.red()
        elif any(not ok for _, ok, _ in results):
            embed.color = discord.Color.orange()

        await msg.edit(content=None, embed=embed)

    # ── !arkplayers <mapa> ─────────────────────────────────────────
    @commands.command(name="arkplayers", aliases=["arkjogadores", "arkwho"])
    @commands.has_permissions(administrator=True)
    async def ark_players(self, ctx: commands.Context, *, mapa: str):
        """Lista os jogadores conectados em um mapa."""
        info = _resolve_map(mapa)
        if not info:
            await ctx.send(f"❌ Mapa `{mapa}` não encontrado. Disponíveis: {_map_list_text()}")
            return

        msg = await ctx.send(f"🔄 Consultando jogadores em **{info['name']}**...")

        try:
            response = await asyncio.wait_for(
                rcon_run(info["host"], info["port"], info["password"], "listplayers"),
                timeout=TIMEOUT_RCON + 2,
            )
        except asyncio.TimeoutError:
            await msg.edit(content=f"⏱️ Timeout — **{info['name']}** pode estar offline.")
            return
        except Exception as e:
            await msg.edit(content=f"❌ Erro ao conectar em **{info['name']}**: `{e}`")
            return

        embed = discord.Embed(
            title=f"👥 Jogadores em {info['name']}",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )
        embed.set_footer(text=f"Solicitado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

        raw = response.strip()
        if not raw or "No Players Connected" in raw:
            embed.description = "_Nenhum jogador conectado no momento._"
        else:
            lines = [l.strip() for l in raw.splitlines() if l.strip()]
            embed.description = "\n".join(f"• {l}" for l in lines)
            embed.set_author(name=f"{len(lines)} jogador(es) online")

        await msg.edit(content=None, embed=embed)

    # ── !rcon <mapa> <comando> ─────────────────────────────────────
    @commands.command(name="rcon")
    @commands.has_permissions(administrator=True)
    async def rcon_cmd(self, ctx: commands.Context, mapa: str, *, comando: str):
        """Envia um comando RCON diretamente ao servidor.

        Exemplos:
          !rcon theisland broadcast Aviso aos jogadores!
          !rcon ragnarok SaveWorld
          !rcon extinction DestroyWildDinos
        """
        info = _resolve_map(mapa)
        if not info:
            await ctx.send(f"❌ Mapa `{mapa}` não encontrado. Disponíveis: {_map_list_text()}")
            return

        msg = await ctx.send(f"📡 Enviando comando para **{info['name']}**...")

        try:
            response = await asyncio.wait_for(
                rcon_run(info["host"], info["port"], info["password"], comando),
                timeout=TIMEOUT_RCON + 2,
            )
        except asyncio.TimeoutError:
            await msg.edit(content=f"⏱️ Timeout — **{info['name']}** pode estar offline.")
            return
        except Exception as e:
            await msg.edit(content=f"❌ Erro ao conectar em **{info['name']}**: `{e}`")
            return

        embed = discord.Embed(
            title=f"📟 RCON → {info['name']}",
            color=discord.Color.teal(),
            timestamp=datetime.now(),
        )
        embed.add_field(name="Comando enviado", value=f"```{comando}```", inline=False)
        resposta = response.strip() if response and response.strip() else "_Sem resposta do servidor_"
        if len(resposta) > 1000:
            resposta = resposta[:997] + "..."
        embed.add_field(name="Resposta do servidor", value=f"```{resposta}```", inline=False)
        embed.set_footer(text=f"Executado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

        await msg.edit(content=None, embed=embed)

    # ── Métodos internos (lógica desacoplada dos comandos) ────────────

    async def _do_ligar(self, ctx: commands.Context, info: dict) -> None:
        if not info.get("service"):
            await ctx.send(
                f"❌ O mapa **{info['name']}** não tem `ARK_MAPx_SERVICE` configurado no `.env`.\n"
                f"Adicione o nome do serviço systemd para poder ligar/desligar/reiniciar."
            )
            return

        msg = await ctx.send(f"⚡ Iniciando **{info['name']}** (`{info['service']}`)...")
        rc, out, err = await systemctl("start", info["service"])

        if rc == 0:
            embed = discord.Embed(
                title=f"✅ {info['name']} — Iniciado",
                description=(
                    f"Serviço `{info['service']}` iniciado com sucesso.\n"
                    f"Aguarde alguns minutos para o servidor carregar o mapa."
                ),
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
        else:
            detail = err or out or "Sem saída do systemctl"
            embed = discord.Embed(
                title=f"❌ Falha ao iniciar {info['name']}",
                description=f"```{detail[:1000]}```",
                color=discord.Color.red(),
                timestamp=datetime.now(),
            )
        embed.set_footer(text=f"Por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await msg.edit(content=None, embed=embed)

    async def _do_desligar(self, ctx: commands.Context, info: dict) -> None:
        if not info.get("service"):
            await ctx.send(f"❌ O mapa **{info['name']}** não tem `ARK_MAPx_SERVICE` configurado no `.env`.")
            return

        embed_confirm = discord.Embed(
            title=f"⚠️ Desligar {info['name']}?",
            description=(
                f"Isso irá **parar** o servidor **{info['name']}** (`{info['service']}`).\n\n"
                f"O mundo será salvo via RCON antes do desligamento (se o servidor estiver online).\n\n"
                f"**Esta ação expulsará todos os jogadores conectados.**"
            ),
            color=discord.Color.orange(),
        )
        view = ConfirmView(ctx.author)
        msg = await ctx.send(embed=embed_confirm, view=view)

        await view.wait()
        for item in view.children:
            item.disabled = True  # type: ignore
        await msg.edit(view=view)

        if not view.confirmed:
            await msg.edit(embed=discord.Embed(title="🚫 Operação cancelada", color=discord.Color.greyple()), view=view)
            return

        await msg.edit(embed=discord.Embed(
            title=f"🔄 Desligando {info['name']}...",
            description="Salvando mundo via RCON, aguarde...",
            color=discord.Color.orange(),
        ), view=None)

        rcon_status = "✅ Mundo salvo via RCON."
        try:
            await asyncio.wait_for(
                rcon_run(info["host"], info["port"], info["password"], "SaveWorld"),
                timeout=TIMEOUT_RCON + 2,
            )
            await asyncio.sleep(3)
        except Exception as e:
            rcon_status = f"⚠️ RCON indisponível (`{e}`). Parando serviço diretamente."

        rc, out, err = await systemctl("stop", info["service"])

        if rc == 0:
            embed_result = discord.Embed(
                title=f"🔴 {info['name']} — Desligado",
                description=f"{rcon_status}\nServiço `{info['service']}` parado com sucesso.",
                color=discord.Color.red(),
                timestamp=datetime.now(),
            )
        else:
            detail = err or out or "Sem saída do systemctl"
            embed_result = discord.Embed(
                title=f"❌ Falha ao parar {info['name']}",
                description=f"{rcon_status}\n```{detail[:800]}```",
                color=discord.Color.dark_red(),
                timestamp=datetime.now(),
            )
        embed_result.set_footer(text=f"Por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await msg.edit(embed=embed_result)

    async def _do_reiniciar(self, ctx: commands.Context, info: dict) -> None:
        if not info.get("service"):
            await ctx.send(f"❌ O mapa **{info['name']}** não tem `ARK_MAPx_SERVICE` configurado no `.env`.")
            return

        embed_confirm = discord.Embed(
            title=f"⚠️ Reiniciar {info['name']}?",
            description=(
                f"Isso irá **reiniciar** o servidor **{info['name']}** (`{info['service']}`).\n\n"
                f"• Um aviso será enviado aos jogadores via RCON\n"
                f"• O mundo será salvo antes do reinício\n"
                f"• O servidor voltará automaticamente após o reinício\n\n"
                f"**Os jogadores serão desconectados temporariamente.**"
            ),
            color=discord.Color.orange(),
        )
        view = ConfirmView(ctx.author)
        msg = await ctx.send(embed=embed_confirm, view=view)

        await view.wait()
        for item in view.children:
            item.disabled = True  # type: ignore
        await msg.edit(view=view)

        if not view.confirmed:
            await msg.edit(embed=discord.Embed(title="🚫 Operação cancelada", color=discord.Color.greyple()), view=view)
            return

        await msg.edit(embed=discord.Embed(
            title=f"🔄 Reiniciando {info['name']}...",
            description="Enviando aviso e salvando mundo via RCON, aguarde...",
            color=discord.Color.orange(),
        ), view=None)

        try:
            await asyncio.wait_for(
                rcon_run(info["host"], info["port"], info["password"],
                         "broadcast AVISO: O servidor sera reiniciado em instantes. Salve seus itens!"),
                timeout=TIMEOUT_RCON,
            )
            await asyncio.sleep(5)
        except Exception:
            pass

        rcon_status = "✅ Mundo salvo via RCON."
        try:
            await asyncio.wait_for(
                rcon_run(info["host"], info["port"], info["password"], "SaveWorld"),
                timeout=TIMEOUT_RCON + 2,
            )
            await asyncio.sleep(3)
        except Exception as e:
            rcon_status = f"⚠️ RCON indisponível (`{e}`). Reiniciando serviço diretamente."

        rc, out, err = await systemctl("restart", info["service"])

        if rc == 0:
            embed_result = discord.Embed(
                title=f"🔁 {info['name']} — Reiniciado",
                description=(
                    f"{rcon_status}\n"
                    f"Serviço `{info['service']}` reiniciado com sucesso.\n"
                    f"Aguarde alguns minutos para o mapa carregar completamente."
                ),
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
        else:
            detail = err or out or "Sem saída do systemctl"
            embed_result = discord.Embed(
                title=f"❌ Falha ao reiniciar {info['name']}",
                description=f"{rcon_status}\n```{detail[:800]}```",
                color=discord.Color.red(),
                timestamp=datetime.now(),
            )
        embed_result.set_footer(text=f"Por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await msg.edit(embed=embed_result)

    # ── Comandos genéricos (aceitam nome do mapa) ──────────────────

    @commands.command(name="arkligar", aliases=["arkstart"])
    @commands.has_permissions(administrator=True)
    async def ark_ligar(self, ctx: commands.Context, *, mapa: str):
        """Liga qualquer servidor ARK pelo nome. Ex: !arkligar fjordur"""
        info = _resolve_map(mapa)
        if not info:
            await ctx.send(f"❌ Mapa `{mapa}` não encontrado. Disponíveis: {_map_list_text()}")
            return
        await self._do_ligar(ctx, info)

    @commands.command(name="arkdesligar", aliases=["arkstop", "arkparar"])
    @commands.has_permissions(administrator=True)
    async def ark_desligar(self, ctx: commands.Context, *, mapa: str):
        """Desliga qualquer servidor ARK pelo nome. Ex: !arkdesligar fjordur"""
        info = _resolve_map(mapa)
        if not info:
            await ctx.send(f"❌ Mapa `{mapa}` não encontrado. Disponíveis: {_map_list_text()}")
            return
        await self._do_desligar(ctx, info)

    @commands.command(name="arkreinicia", aliases=["arkrestart", "arkreboot"])
    @commands.has_permissions(administrator=True)
    async def ark_reinicia(self, ctx: commands.Context, *, mapa: str):
        """Reinicia qualquer servidor ARK pelo nome. Ex: !arkreinicia fjordur"""
        info = _resolve_map(mapa)
        if not info:
            await ctx.send(f"❌ Mapa `{mapa}` não encontrado. Disponíveis: {_map_list_text()}")
            return
        await self._do_reiniciar(ctx, info)

    # ── Atalhos por mapa ───────────────────────────────────────────
    # ragom = Ragnarok Omega | tl = The Island | g2 = Genesis 2 | fj = Fjordur

    @commands.command(name="arkligarragom")
    @commands.has_permissions(administrator=True)
    async def ark_ligar_ragom(self, ctx: commands.Context):
        """⚡ Liga o servidor Ragnarok Omega."""
        await self._do_ligar(ctx, config.ARK_MAPS["ragnarok omega"])

    @commands.command(name="arkdesligarragom")
    @commands.has_permissions(administrator=True)
    async def ark_desligar_ragom(self, ctx: commands.Context):
        """🔴 Desliga o servidor Ragnarok Omega (salva antes)."""
        await self._do_desligar(ctx, config.ARK_MAPS["ragnarok omega"])

    @commands.command(name="arkreiniciaragom")
    @commands.has_permissions(administrator=True)
    async def ark_reinicia_ragom(self, ctx: commands.Context):
        """🔁 Reinicia o servidor Ragnarok Omega (avisa e salva)."""
        await self._do_reiniciar(ctx, config.ARK_MAPS["ragnarok omega"])

    @commands.command(name="arkligartl")
    @commands.has_permissions(administrator=True)
    async def ark_ligar_tl(self, ctx: commands.Context):
        """⚡ Liga o servidor The Island."""
        await self._do_ligar(ctx, config.ARK_MAPS["the island"])

    @commands.command(name="arkdesligartl")
    @commands.has_permissions(administrator=True)
    async def ark_desligar_tl(self, ctx: commands.Context):
        """🔴 Desliga o servidor The Island (salva antes)."""
        await self._do_desligar(ctx, config.ARK_MAPS["the island"])

    @commands.command(name="arkreiniciatl")
    @commands.has_permissions(administrator=True)
    async def ark_reinicia_tl(self, ctx: commands.Context):
        """🔁 Reinicia o servidor The Island (avisa e salva)."""
        await self._do_reiniciar(ctx, config.ARK_MAPS["the island"])

    @commands.command(name="arkligarg2")
    @commands.has_permissions(administrator=True)
    async def ark_ligar_g2(self, ctx: commands.Context):
        """⚡ Liga o servidor Genesis 2."""
        await self._do_ligar(ctx, config.ARK_MAPS["genesis 2"])

    @commands.command(name="arkdesligarg2")
    @commands.has_permissions(administrator=True)
    async def ark_desligar_g2(self, ctx: commands.Context):
        """🔴 Desliga o servidor Genesis 2 (salva antes)."""
        await self._do_desligar(ctx, config.ARK_MAPS["genesis 2"])

    @commands.command(name="arkreiniciag2")
    @commands.has_permissions(administrator=True)
    async def ark_reinicia_g2(self, ctx: commands.Context):
        """🔁 Reinicia o servidor Genesis 2 (avisa e salva)."""
        await self._do_reiniciar(ctx, config.ARK_MAPS["genesis 2"])

    @commands.command(name="arkligarfj")
    @commands.has_permissions(administrator=True)
    async def ark_ligar_fj(self, ctx: commands.Context):
        """⚡ Liga o servidor Fjordur."""
        await self._do_ligar(ctx, config.ARK_MAPS["fjordur"])

    @commands.command(name="arkdesligarfj")
    @commands.has_permissions(administrator=True)
    async def ark_desligar_fj(self, ctx: commands.Context):
        """🔴 Desliga o servidor Fjordur (salva antes)."""
        await self._do_desligar(ctx, config.ARK_MAPS["fjordur"])

    @commands.command(name="arkreiniciafj")
    @commands.has_permissions(administrator=True)
    async def ark_reinicia_fj(self, ctx: commands.Context):
        """🔁 Reinicia o servidor Fjordur (avisa e salva)."""
        await self._do_reiniciar(ctx, config.ARK_MAPS["fjordur"])


    # ── !arkajuda ─────────────────────────────────────────────────
    @commands.command(name="arkajuda", aliases=["arkhelp", "arkcomandos"])
    @commands.has_permissions(administrator=True)
    async def ark_ajuda(self, ctx: commands.Context):
        """Lista todos os comandos e atalhos de controle dos servidores ARK."""
        p = ctx.prefix or "!"
        embed = discord.Embed(
            title="🦕 Guia de Comandos ARK",
            description=(
                "Todos os comandos de controle dos servidores ARK.\n"
                "Cada mapa tem atalhos diretos — **sem precisar digitar o nome do mapa**."
            ),
            color=discord.Color.og_blurple(),
            timestamp=datetime.now(),
        )

        mapas_atalhos = [
            ("🗺️ Ragnarok Omega", "ragom"),
            ("🏝️ The Island",     "tl"),
            ("🧬 Genesis 2",      "g2"),
            ("🏔️ Fjordur",        "fj"),
        ]
        for nome, sufixo in mapas_atalhos:
            embed.add_field(
                name=nome,
                value=(
                    f"`{p}arkligar{sufixo}` — ⚡ Liga o servidor\n"
                    f"`{p}arkdesligar{sufixo}` — 🔴 Desliga *(salva antes)*\n"
                    f"`{p}arkreinicia{sufixo}` — 🔁 Reinicia *(avisa e salva)*"
                ),
                inline=True,
            )

        embed.add_field(
            name="⚙️ Comandos Gerais *(aceitam qualquer mapa)*",
            value=(
                f"`{p}arkligar <mapa>` — ⚡ Liga pelo nome\n"
                f"`{p}arkdesligar <mapa>` — 🔴 Desliga pelo nome\n"
                f"`{p}arkreinicia <mapa>` — 🔁 Reinicia pelo nome\n"
                f"`{p}arkstatus [mapa]` — Verifica online/offline e jogadores\n"
                f"`{p}arkplayers <mapa>` — Lista quem está conectado\n"
                f"`{p}rcon <mapa> <cmd>` — Envia comando RCON livre\n"
                f"`{p}arkmapas` — Lista mapas e portas configurados\n"
                f"`{p}arkajuda` — Exibe este guia"
            ),
            inline=False,
        )
        embed.add_field(
            name="📝 Exemplos",
            value=(
                f"`{p}arkligarfj` → liga o Fjordur diretamente\n"
                f"`{p}arkdesligarragom` → desliga Ragnarok Omega *(pede confirmação)*\n"
                f"`{p}arkreiniciatl` → reinicia The Island *(avisos + confirmação)*\n"
                f"`{p}rcon g2 broadcast Reinicio em 5 minutos!`"
            ),
            inline=False,
        )
        embed.set_footer(text="⚠️  Desligar e reiniciar sempre pedem confirmação via botão.")
        await ctx.send(embed=embed)

    # ── Tratamento de erros (cobre todos os comandos acima) ────────
    @ark_status.error
    @ark_players.error
    @rcon_cmd.error
    @ark_mapas.error
    @ark_ligar.error
    @ark_desligar.error
    @ark_reinicia.error
    @ark_ligar_ragom.error
    @ark_desligar_ragom.error
    @ark_reinicia_ragom.error
    @ark_ligar_tl.error
    @ark_desligar_tl.error
    @ark_reinicia_tl.error
    @ark_ligar_g2.error
    @ark_desligar_g2.error
    @ark_reinicia_g2.error
    @ark_ligar_fj.error
    @ark_desligar_fj.error
    @ark_reinicia_fj.error
    @ark_ajuda.error
    async def ark_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🔒 Você não tem permissão para usar este comando.", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"⚠️ Argumento faltando. Use `{ctx.prefix}arkajuda` para ver todos os atalhos.", delete_after=10)


# ──────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(ArkCog(bot))
