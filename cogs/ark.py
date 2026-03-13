
import os
import json
import random
import string
import asyncio
import discord
from discord.ext import commands
from typing import Optional


class ArkCog(commands.Cog):
    @commands.command(name="consultarvinculo")
    async def consultar_vinculo(self, ctx: commands.Context, discord_id: Optional[str] = None):
        links = self._load_links()
        if not discord_id:
            discord_id = str(ctx.author.id)
        found = [v for v in links.values() if str(v.get("discord_id")) == discord_id]
        if not found:

            # ...existing code...

            class ArkCog(commands.Cog):
                """Comandos de integração RCON e controle dos servidores ARK."""
                LINK_DB_PATH = os.path.join(os.path.dirname(__file__), "ark_links.json")

                def __init__(self, bot):
                    self.bot = bot

                def _load_links(self):
                    if not os.path.exists(self.LINK_DB_PATH):
                        return {}
                    with open(self.LINK_DB_PATH, "r", encoding="utf-8") as f:
                        return json.load(f)

                def _save_links(self, links):
                    with open(self.LINK_DB_PATH, "w", encoding="utf-8") as f:
                        json.dump(links, f, ensure_ascii=False, indent=2)

                def _generate_code(self, length=8):
                    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

                async def cog_check(self, ctx: commands.Context) -> bool:
                    # 1. Verifica o canal
                    if ctx.channel.id != config.ARK_CANAL_RCON_ID:
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
                    if not ctx.author.guild_permissions.administrator:
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

                @commands.command(name="arkmapas", aliases=["arkmaps", "arkservers"])
                @commands.has_permissions(administrator=True)
                async def ark_mapas(self, ctx: commands.Context):
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

                @commands.command(name="arkstatus", aliases=["arkserver", "arkinfo"])
                @commands.has_permissions(administrator=True)
                async def ark_status(self, ctx: commands.Context, mapa: str | None = None):
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

                                # ...existing code...
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



# ...existing code...

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

                class ArkCog(commands.Cog):
                    """Comandos de integração RCON e controle dos servidores ARK."""
                    LINK_DB_PATH = os.path.join(os.path.dirname(__file__), "ark_links.json")

                    def __init__(self, bot):
                        self.bot = bot

                    def _load_links(self):
                        if not os.path.exists(self.LINK_DB_PATH):
                            return {}
                        with open(self.LINK_DB_PATH, "r", encoding="utf-8") as f:
                            return json.load(f)

                    def _save_links(self, links):
                        with open(self.LINK_DB_PATH, "w", encoding="utf-8") as f:
                            json.dump(links, f, ensure_ascii=False, indent=2)

                    def _generate_code(self, length=8):
                        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

                    @commands.command(name="consultarvinculo")
                    async def consultar_vinculo(self, ctx: commands.Context, discord_id: Optional[str] = None):
                        links = self._load_links()
                        if not discord_id:
                            discord_id = str(ctx.author.id)
                        found = [v for v in links.values() if str(v.get("discord_id")) == discord_id]
                        if not found:
                            await ctx.send("❌ Nenhum vínculo encontrado.")
                            return
                        for v in found:
                            await ctx.send(f"Vínculo: SteamID `{v.get('steam_id', 'N/A')}` | Mapa: `{v.get('map', 'N/A')}` | Código: `{[k for k, d in links.items() if d == v][0]}`")

                    @commands.command(name="removervinculo")
                    async def remover_vinculo(self, ctx: commands.Context, codigo: str):
                        links = self._load_links()
                        if codigo not in links:
                            await ctx.send("❌ Código não encontrado.")
                            return
                        del links[codigo]
                        self._save_links(links)
                        await ctx.send(f"✅ Vínculo removido para código `{codigo}`.")

                    @commands.command(name="editarvinculo")
                    async def editar_vinculo(self, ctx: commands.Context, codigo: str, steam_id: Optional[str] = None, map_name: Optional[str] = None):
                        links = self._load_links()
                        if codigo not in links:
                            await ctx.send("❌ Código não encontrado.")
                            return
                        if steam_id:
                            links[codigo]["steam_id"] = steam_id
                        if map_name:
                            links[codigo]["map"] = map_name
                        self._save_links(links)
                        await ctx.send(f"✅ Vínculo atualizado para código `{codigo}`.")

                    @commands.command(name="painelvincular")
                    async def painel_vincular(self, ctx: commands.Context):
                        if ctx.channel.id != 1480007139035582546:
                            await ctx.send("❌ Este comando só pode ser usado no canal de vinculação.", delete_after=8)
                            return
                        embed = discord.Embed(
                            title="Painel de Vinculação ARK",
                            description="Clique no botão abaixo para iniciar o vínculo entre seu Discord e o ARK. Siga as instruções!",
                            color=discord.Color.green()
                        )
                        view = discord.ui.View()
                        async def vincular_callback(interaction: discord.Interaction):
                            code = self._generate_code()
                            links = self._load_links()
                            links[code] = {"discord_id": interaction.user.id}
                            self._save_links(links)
                            await interaction.response.send_message(
                                f"Seu código de vinculação é: `{code}`\nCole esse código no chat do ARK para finalizar o vínculo.",
                                ephemeral=True
                            )
                        btn = discord.ui.Button(label="Vincular Discord ao ARK", style=discord.ButtonStyle.primary)
                        btn.callback = vincular_callback
                        view.add_item(btn)
                        await ctx.send(embed=embed, view=view)

                    # ...existing code...
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
