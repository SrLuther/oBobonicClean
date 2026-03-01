# cogs/music.py
import discord
from discord.ext import commands
import asyncio
import os
from collections import deque
from typing import Any, Optional

try:
    import yt_dlp  # type: ignore
except ImportError:
    yt_dlp = None  # type: ignore

# Canal dedicado onde o painel "Tocando agora" fica fixo
MUSIC_PANEL_CHANNEL_ID = 1477466434593493074

# Caminho do arquivo de cookies (opcional — necessário em VPS para contornar bloqueio do YouTube)
_COOKIES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies.txt")
_COOKIES_OPTS: dict[str, Any] = {"cookiefile": _COOKIES_FILE} if os.path.isfile(_COOKIES_FILE) else {}

# Usa o client iOS do YouTube — contorna detecção de bot em servidores de datacenter
_YT_EXTRACTOR_ARGS: dict[str, Any] = {
    "extractor_args": {"youtube": {"player_client": ["ios", "web"]}},
}

YTDL_OPTIONS_SINGLE: dict[str, Any] = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    **_YT_EXTRACTOR_ARGS,
    **_COOKIES_OPTS,
}

YTDL_OPTIONS_PLAYLIST: dict[str, Any] = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "extract_flat": "in_playlist",  # extrai só metadados sem baixar tudo de uma vez
    "quiet": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
    **_YT_EXTRACTOR_ARGS,
    **_COOKIES_OPTS,
}

YTDL_OPTIONS_TRACK: dict[str, Any] = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
    **_YT_EXTRACTOR_ARGS,
    **_COOKIES_OPTS,
}

FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
FFMPEG_OPTIONS_STR = "-vn"


# 
# Modelo de faixa
# 
class Track:
    def __init__(self, source_url: str, title: str, webpage_url: str, duration: int, thumbnail: str, requester: discord.Member):
        self.source_url = source_url
        self.title = title
        self.webpage_url = webpage_url
        self.duration = duration
        self.thumbnail = thumbnail
        self.requester = requester

    @classmethod
    async def resolve_url(cls, url: str, requester: discord.Member, loop: asyncio.AbstractEventLoop) -> "Track":
        """Resolve a URL de uma entrada individual e obtém stream de áudio."""
        if yt_dlp is None:
            raise RuntimeError("yt-dlp não está instalado.")
        ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS_TRACK)  # type: ignore[arg-type]
        data: dict[str, Any] = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=False)  # type: ignore[return-value]
        )
        return cls(
            source_url=data.get("url") or "",
            title=data.get("title") or "Desconhecido",
            webpage_url=data.get("webpage_url") or url,
            duration=int(data.get("duration") or 0),
            thumbnail=data.get("thumbnail") or "",
            requester=requester,
        )

    @classmethod
    async def from_query(cls, query: str, requester: discord.Member, loop: asyncio.AbstractEventLoop) -> "list[Track]":
        """
        Retorna lista de faixas.
        - URL de playlist: retorna todas as faixas da playlist
        - URL simples ou busca por nome: retorna lista com 1 faixa
        """
        if yt_dlp is None:
            raise RuntimeError("yt-dlp não está instalado.")

        is_playlist = "list=" in query or "/playlist" in query

        if is_playlist:
            ytdl_meta = yt_dlp.YoutubeDL(YTDL_OPTIONS_PLAYLIST)  # type: ignore[arg-type]
            data: dict[str, Any] = await loop.run_in_executor(
                None, lambda: ytdl_meta.extract_info(query, download=False)  # type: ignore[return-value]
            )
            entries = data.get("entries") or []
            tracks: list[Track] = []
            for entry in entries:
                url = entry.get("url") or entry.get("webpage_url") or ""
                if not url:
                    continue
                tracks.append(cls(
                    source_url="",            # resolvido na hora de tocar
                    title=entry.get("title") or "Desconhecido",
                    webpage_url=url,
                    duration=int(entry.get("duration") or 0),
                    thumbnail=entry.get("thumbnail") or "",
                    requester=requester,
                ))
            return tracks

        # Busca simples ou URL única
        ytdl_single = yt_dlp.YoutubeDL(YTDL_OPTIONS_SINGLE)  # type: ignore[arg-type]
        data = await loop.run_in_executor(
            None, lambda: ytdl_single.extract_info(query, download=False)  # type: ignore[return-value]
        )
        if "entries" in data:
            data = data["entries"][0]

        return [cls(
            source_url=data.get("url") or "",
            title=data.get("title") or "Desconhecido",
            webpage_url=data.get("webpage_url") or query,
            duration=int(data.get("duration") or 0),
            thumbnail=data.get("thumbnail") or "",
            requester=requester,
        )]

    def format_duration(self) -> str:
        m, s = divmod(self.duration, 60)
        h, m = divmod(m, 60)
        return f"{h:02}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}"


# 
# Estado do player por servidor
# 
class GuildPlayer:
    def __init__(self):
        self.queue: deque[Track] = deque()
        self.current: Optional[Track] = None
        self.voice_client: Optional[discord.VoiceClient] = None
        self.panel_message: Optional[discord.Message] = None
        self._play_next_event = asyncio.Event()
        self.paused = False

    def is_playing(self) -> bool:
        return self.voice_client is not None and self.voice_client.is_playing()


# 
# View com botões do painel
# 
class NowPlayingView(discord.ui.View):
    def __init__(self, cog: "MusicCog", guild_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    def _get_player(self) -> Optional[GuildPlayer]:
        return self.cog.players.get(self.guild_id)

    @discord.ui.button(label=" Pular", style=discord.ButtonStyle.primary, custom_id="music_skip")
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self._get_player()
        if not player or not player.voice_client:
            await interaction.response.send_message(" Nada tocando.", ephemeral=True)
            return
        player.voice_client.stop()
        await interaction.response.send_message(" Pulando...", ephemeral=True, delete_after=3)

    @discord.ui.button(label=" Pausar", style=discord.ButtonStyle.secondary, custom_id="music_pause")
    async def pause_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self._get_player()
        if not player or not player.voice_client:
            await interaction.response.send_message(" Nada tocando.", ephemeral=True)
            return

        if player.voice_client.is_playing():
            player.voice_client.pause()
            player.paused = True
            button.label = " Continuar"
            button.style = discord.ButtonStyle.success
        elif player.voice_client.is_paused():
            player.voice_client.resume()
            player.paused = False
            button.label = " Pausar"
            button.style = discord.ButtonStyle.secondary

        await interaction.response.edit_message(view=self)

    @discord.ui.button(label=" Parar", style=discord.ButtonStyle.danger, custom_id="music_stop")
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self._get_player()
        if not player:
            await interaction.response.send_message(" Nada tocando.", ephemeral=True)
            return

        player.queue.clear()
        player.current = None
        if player.voice_client:
            player.voice_client.stop()
            await player.voice_client.disconnect()
        self.cog.players.pop(self.guild_id, None)

        embed = discord.Embed(
            title=" Player de Música",
            description="Nenhuma música tocando no momento.\nUse `!play <música ou link>` para começar.",
            color=discord.Color.greyple()
        )
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)


# 
# Cog principal
# 
class MusicCog(commands.Cog, name="Música"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}

    def get_player(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = GuildPlayer()
        return self.players[guild_id]

    def _build_now_playing_embed(self, track: Track, queue_size: int) -> discord.Embed:
        embed = discord.Embed(
            title=" Tocando agora",
            description=f"**[{track.title}]({track.webpage_url})**",
            color=discord.Color.green()
        )
        embed.add_field(name=" Duração", value=track.format_duration(), inline=True)
        embed.add_field(name=" Pedido por", value=track.requester.mention, inline=True)
        embed.add_field(name=" Na fila", value=str(queue_size), inline=True)
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        return embed

    async def _update_panel(self, guild_id: int, track: Optional[Track] = None, idle: bool = False):
        """Atualiza ou cria o painel no canal dedicado."""
        player = self.get_player(guild_id)
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        channel = guild.get_channel(MUSIC_PANEL_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return

        if idle:
            embed = discord.Embed(
                title=" Player de Música",
                description="Nenhuma música tocando no momento.\nUse `!play <música ou link>` para começar.",
                color=discord.Color.greyple()
            )
            view = discord.ui.View()
        else:
            if not track:
                return
            embed = self._build_now_playing_embed(track, len(player.queue))
            view = NowPlayingView(self, guild_id)

        try:
            if player.panel_message:
                await player.panel_message.edit(embed=embed, view=view)
            else:
                # Limpa mensagens antigas do bot no canal antes de criar novo painel
                async for msg in channel.history(limit=20):
                    if msg.author == self.bot.user:
                        try:
                            await msg.delete()
                        except Exception:
                            pass
                player.panel_message = await channel.send(embed=embed, view=view)
        except discord.NotFound:
            player.panel_message = await channel.send(embed=embed, view=view)
        except Exception as e:
            print(f"[MUSIC] Erro ao atualizar painel: {e}")

    async def _play_loop(self, guild_id: int):
        """Loop principal que consome a fila e toca faixa por faixa."""
        player = self.get_player(guild_id)

        while True:
            player._play_next_event.clear()

            if not player.queue:
                try:
                    await asyncio.wait_for(player._play_next_event.wait(), timeout=180)
                except asyncio.TimeoutError:
                    if player.voice_client and player.voice_client.is_connected():
                        await player.voice_client.disconnect()
                    await self._update_panel(guild_id, idle=True)
                    self.players.pop(guild_id, None)
                    return
                continue

            track = player.queue.popleft()

            # Se a faixa veio de playlist, ainda não tem source_url  resolve agora
            if not track.source_url:
                try:
                    resolved = await Track.resolve_url(track.webpage_url, track.requester, self.bot.loop)
                    track.source_url = resolved.source_url
                    track.thumbnail = track.thumbnail or resolved.thumbnail
                    track.duration = track.duration or resolved.duration
                except Exception as e:
                    print(f"[MUSIC] Falha ao resolver {track.title}: {e}")
                    player._play_next_event.set()
                    continue

            player.current = track
            player.paused = False

            raw_source = discord.FFmpegPCMAudio(
                track.source_url,
                before_options=FFMPEG_BEFORE_OPTIONS,
                options=FFMPEG_OPTIONS_STR,
            )
            source = discord.PCMVolumeTransformer(raw_source, volume=0.5)

            def after_play(error: Optional[Exception]):
                if error:
                    print(f"[MUSIC] Erro ao reproduzir: {error}")
                self.bot.loop.call_soon_threadsafe(player._play_next_event.set)

            player.voice_client.play(source, after=after_play)  # type: ignore[union-attr]

            await self._update_panel(guild_id, track=track)

            await player._play_next_event.wait()

        player.current = None

    # 
    # Comandos
    # 

    async def _check_and_join(self, ctx: commands.Context[Any]) -> Optional[discord.VoiceChannel]:
        """
        Verifica se o autor está em um canal de voz e se o bot pode entrar.
        Retorna o canal de voz ou None se houver conflito.
        """
        if not isinstance(ctx.author, discord.Member) or not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ Você precisa estar em um canal de voz!", delete_after=8)
            return None

        voice_channel = ctx.author.voice.channel
        player = self.get_player(ctx.guild.id)  # type: ignore[union-attr]

        # Bot já está conectado em outro canal e tocando
        if (
            player.voice_client is not None
            and player.voice_client.is_connected()
            and player.voice_client.channel != voice_channel
            and (player.is_playing() or player.voice_client.is_paused())
        ):
            current_ch = player.voice_client.channel
            await ctx.send(
                f"🎵 O player já está em uso em {current_ch.mention}!\n"
                f"Aguarde a música terminar ou use `!stop` para encerrar.",
                delete_after=10
            )
            return None

        if player.voice_client is None or not player.voice_client.is_connected():
            player.voice_client = await voice_channel.connect()
        elif player.voice_client.channel != voice_channel:
            # Bot está idle — pode mover
            await player.voice_client.move_to(voice_channel)

        return voice_channel  # type: ignore[return-value]

    @commands.command(name="join", aliases=["chamar", "entrar"])
    async def join(self, ctx: commands.Context[Any]):
        """Chama o bot para o seu canal de voz."""
        channel = await self._check_and_join(ctx)
        if channel:
            await ctx.send(f"✅ Entrei em **{channel.name}**!", delete_after=6)

    @commands.command(name="play", aliases=["tocar", "p"])
    async def play(self, ctx: commands.Context[Any], *, query: str):
        """Toca uma música ou playlist do YouTube. Ex: !play lofi hip hop"""

        channel = await self._check_and_join(ctx)
        if not channel:
            return

        player = self.get_player(ctx.guild.id)  # type: ignore[union-attr]

        member = ctx.author
        if not isinstance(member, discord.Member):
            return

        async with ctx.typing():
            try:
                tracks = await Track.from_query(query, member, self.bot.loop)
            except Exception as e:
                await ctx.send(f" Erro ao buscar: `{e}`", delete_after=10)
                return

        for t in tracks:
            player.queue.append(t)

        if len(tracks) == 1:
            if not player.is_playing() and player.current is None:
                await ctx.send(f" Carregando **{tracks[0].title}**...", delete_after=5)
            else:
                await ctx.send(f" **{tracks[0].title}** adicionada à fila. (posição {len(player.queue)})", delete_after=8)
        else:
            await ctx.send(f" **{len(tracks)} músicas** da playlist adicionadas à fila!", delete_after=8)

        if not player.is_playing() and player.current is None:
            self.bot.loop.create_task(self._play_loop(ctx.guild.id))  # type: ignore[union-attr]

        player._play_next_event.set()

    @commands.command(name="skip", aliases=["pular", "s"])
    async def skip(self, ctx: commands.Context[Any]):
        """Pula a música atual."""
        player = self.get_player(ctx.guild.id)  # type: ignore[union-attr]
        if not player.is_playing():
            await ctx.send(" Não há nada tocando!", delete_after=8)
            return
        player.voice_client.stop()  # type: ignore[union-attr]
        await ctx.send(" Pulando...", delete_after=4)

    @commands.command(name="pause", aliases=["pausar"])
    async def pause(self, ctx: commands.Context[Any]):
        """Pausa a música atual."""
        player = self.get_player(ctx.guild.id)  # type: ignore[union-attr]
        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.pause()
            player.paused = True
            await ctx.send(" Pausado.", delete_after=5)
        else:
            await ctx.send(" Não há nada tocando!", delete_after=8)

    @commands.command(name="resume", aliases=["continuar"])
    async def resume(self, ctx: commands.Context[Any]):
        """Retoma a música pausada."""
        player = self.get_player(ctx.guild.id)  # type: ignore[union-attr]
        if player.voice_client and player.voice_client.is_paused():
            player.voice_client.resume()
            player.paused = False
            await ctx.send(" Retomando.", delete_after=5)
        else:
            await ctx.send(" Nada está pausado!", delete_after=8)

    @commands.command(name="stop", aliases=["parar"])
    async def stop(self, ctx: commands.Context[Any]):
        """Para a música e limpa a fila."""
        player = self.get_player(ctx.guild.id)  # type: ignore[union-attr]
        player.queue.clear()
        player.current = None
        if player.voice_client:
            player.voice_client.stop()
            await player.voice_client.disconnect()
        await self._update_panel(ctx.guild.id, idle=True)  # type: ignore[union-attr]
        self.players.pop(ctx.guild.id, None)  # type: ignore[union-attr]
        await ctx.send(" Reprodução encerrada e fila limpa.", delete_after=8)

    @commands.command(name="leave", aliases=["sair", "dc"])
    async def leave(self, ctx: commands.Context[Any]):
        """Faz o bot sair do canal de voz."""
        player = self.get_player(ctx.guild.id)  # type: ignore[union-attr]
        if player.voice_client and player.voice_client.is_connected():
            player.queue.clear()
            player.voice_client.stop()
            await player.voice_client.disconnect()
            await self._update_panel(ctx.guild.id, idle=True)  # type: ignore[union-attr]
            self.players.pop(ctx.guild.id, None)  # type: ignore[union-attr]
            await ctx.send(" Saí do canal de voz.", delete_after=5)
        else:
            await ctx.send(" Não estou em nenhum canal de voz!", delete_after=8)

    @commands.command(name="queue", aliases=["fila", "q"])
    async def queue_cmd(self, ctx: commands.Context[Any]):
        """Exibe a fila de músicas."""
        player = self.get_player(ctx.guild.id)  # type: ignore[union-attr]
        if not player.current and not player.queue:
            await ctx.send(" A fila está vazia!", delete_after=8)
            return

        embed = discord.Embed(title=" Fila de Músicas", color=discord.Color.purple())

        if player.current:
            estado = " Pausado" if player.paused else " Tocando"
            embed.add_field(
                name=estado,
                value=f"[{player.current.title}]({player.current.webpage_url}) `{player.current.format_duration()}`",
                inline=False
            )

        if player.queue:
            linhas = []
            for i, t in enumerate(list(player.queue)[:10], 1):
                dur = t.format_duration() if t.duration else "?"
                linhas.append(f"`{i}.` [{t.title}]({t.webpage_url}) `{dur}`")
            if len(player.queue) > 10:
                linhas.append(f"*... e mais {len(player.queue) - 10} músicas*")
            embed.add_field(name=" Próximas", value="\n".join(linhas), inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="nowplaying", aliases=["np", "tocando"])
    async def nowplaying(self, ctx: commands.Context[Any]):
        """Exibe a música tocando agora."""
        player = self.get_player(ctx.guild.id)  # type: ignore[union-attr]
        if not player.current:
            await ctx.send(" Nada está tocando no momento!", delete_after=8)
            return
        embed = self._build_now_playing_embed(player.current, len(player.queue))
        await ctx.send(embed=embed)

    @commands.command(name="volume", aliases=["vol"])
    async def volume(self, ctx: commands.Context[Any], vol: int):
        """Ajusta o volume (1100). Ex: !volume 60"""
        player = self.get_player(ctx.guild.id)  # type: ignore[union-attr]
        if not player.voice_client or not player.voice_client.source:
            await ctx.send(" Nada está tocando!", delete_after=8)
            return
        if not 1 <= vol <= 100:
            await ctx.send(" O volume deve ser entre 1 e 100.", delete_after=8)
            return
        source = player.voice_client.source
        if isinstance(source, discord.PCMVolumeTransformer):
            source.volume = vol / 100
            await ctx.send(f" Volume ajustado para **{vol}%**", delete_after=5)
        else:
            await ctx.send(" Não é possível ajustar o volume agora.", delete_after=8)


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot))

