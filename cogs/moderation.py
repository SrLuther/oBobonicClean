# cogs/moderation.py
from discord.ext import commands
import discord
import re
from datetime import datetime
from typing import Optional, List, Any, cast
from config import CANAL_LOGS_ID, QUARANTINE_ROLE_ID
try:
    from utils.cache import channel_cache
except ImportError:
    # Fallback se utils não estiver disponível
    channel_cache = None

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self._compile_badwords()
        # Regex pré-compilada para convites (melhor performance)
        self.invite_regex = re.compile(r"(discord\.gg/|discord\.com/invite/)", re.IGNORECASE)
    
    def _compile_badwords(self) -> None:
        """Carrega e compila lista de palavrões em regex otimizada."""
        try:
            with open(".bancos/palavroes.txt", "r", encoding="utf8") as f:
                words = [w.strip().lower() for w in f.readlines() if w.strip()]
            
            if words:
                # Cria regex com word boundaries para melhor performance
                pattern = "|".join(re.escape(word) for word in words)
                self.badwords_regex = re.compile(r"\b(" + pattern + r")\b", re.IGNORECASE)
                self.badwords_count = len(words)
            else:
                self.badwords_regex = None
                self.badwords_count = 0
                
            print(f"✅ Filtro de palavrões carregado: {self.badwords_count} palavras.")
        except FileNotFoundError:
            print("⚠️ Arquivo palavroes.txt não encontrado. Filtro de palavrões desativado.")
            self.badwords_regex = None
            self.badwords_count = 0

    def get_log_channel(self, guild: Optional[discord.Guild]) -> Optional[discord.TextChannel]:
        """Obtém canal de logs com cache."""
        if channel_cache:
            channel = channel_cache.get(self.bot, CANAL_LOGS_ID)
            return cast(Optional[discord.TextChannel], channel) if isinstance(channel, discord.TextChannel) else None
        else:
            channel = self.bot.get_channel(CANAL_LOGS_ID)
            return cast(Optional[discord.TextChannel], channel)

    @commands.command(name="faxina", aliases=['purgeall'])
    @commands.has_permissions(manage_messages=True)
    async def faxina(self, ctx: commands.Context[Any]) -> None:
        try:
            if ctx.guild is None or not isinstance(ctx.channel, discord.TextChannel):
                await ctx.send("❌ Este comando só pode ser usado em canais de texto do servidor.", delete_after=8)
                return
            try:
                await ctx.message.delete()
            except (discord.NotFound, discord.Forbidden):
                pass
            deleted: List[discord.Message] = await ctx.channel.purge()
            log_channel: Optional[discord.TextChannel] = self.get_log_channel(ctx.guild)
            if log_channel:
                embed = discord.Embed(
                    title="🧹 Faxina Completa (Purge)",
                    description=f"Todas as mensagens foram apagadas em {ctx.channel.mention}.",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Mensagens Deletadas", value=len(deleted), inline=True)
                embed.add_field(name="Executado Por", value=ctx.author.mention, inline=True)
                embed.timestamp = datetime.now()
                await log_channel.send(embed=embed)

            await ctx.send(f"🧹 Faxina feita! {len(deleted)} mensagens deletadas.", delete_after=5)

        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissão para deletar mensagens neste canal.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Ocorreu um erro ao tentar deletar as mensagens: {e}")

    @commands.command(name="limpar", aliases=['clear'])
    @commands.has_permissions(manage_messages=True)
    async def limpar(self, ctx: commands.Context[Any], quantidade: int) -> None:
        if ctx.guild is None or not isinstance(ctx.channel, discord.TextChannel):
            await ctx.send("❌ Este comando só pode ser usado em canais de texto do servidor.", delete_after=8)
            return
        await ctx.message.delete()
        if quantidade <= 0:
            await ctx.send("❌ A quantidade de caracteres precisa ser maior que 0.", delete_after=5)
            return

        contador: int = 0
        mensagens: List[discord.Message] = []

        async for msg in ctx.channel.history(limit=None):
            contador += len(msg.content)
            mensagens.append(msg)
            if contador >= quantidade:
                break

        if mensagens:
            try:
                await ctx.channel.delete_messages(mensagens)
                log_channel: Optional[discord.TextChannel] = self.get_log_channel(ctx.guild)
                if log_channel:
                    embed = discord.Embed(
                        title="🧹 Limpeza por Caracteres",
                        description=f"Mensagens deletadas em {ctx.channel.mention} até atingir o limite de caracteres.",
                        color=discord.Color.dark_blue()
                    )
                    embed.add_field(name="Caracteres Alvo", value=quantidade, inline=True)
                    embed.add_field(name="Mensagens Deletadas", value=len(mensagens), inline=True)
                    embed.add_field(name="Executado Por", value=ctx.author.mention, inline=False)
                    embed.timestamp = datetime.now()
                    await log_channel.send(embed=embed)

                await ctx.send(f"🧹 Mensagens deletadas até atingir {quantidade} caracteres.", delete_after=5)
            except discord.Forbidden:
                await ctx.send("❌ Não tenho permissão para deletar mensagens neste canal.")
            except discord.HTTPException as e:
                await ctx.send(f"❌ Ocorreu um erro ao tentar deletar as mensagens: {e}")
        else:
            await ctx.send("⚠️ Não foram encontradas mensagens para deletar.", delete_after=5)

    @commands.command(aliases=['limparall'])
    @commands.has_permissions(administrator=True)
    async def limpezageral(self, ctx: commands.Context[Any], usuario: discord.Member, limite: int = 200) -> None:
        if not 1 <= limite <= 1000:
            await ctx.send("O limite deve ser entre 1 e 1000.")
            return

        if ctx.guild is None:
            await ctx.send("❌ Este comando só pode ser usado dentro de um servidor.", delete_after=8)
            return
        await ctx.message.delete()

        log_channel: Optional[discord.TextChannel] = self.get_log_channel(ctx.guild)
        mensagens_apagadas: int = 0

        guild: discord.Guild = ctx.guild
        try:
            from utils.cache import role_cache
            quarantine_role: Optional[discord.Role] = role_cache.get(guild, QUARANTINE_ROLE_ID) if role_cache else guild.get_role(QUARANTINE_ROLE_ID)
        except ImportError:
            quarantine_role: Optional[discord.Role] = guild.get_role(QUARANTINE_ROLE_ID)
        if quarantine_role:
            try:
                await usuario.edit(roles=[quarantine_role], reason="Conta comprometida/Raid - Quarentena.")
                await ctx.send(f"🛡️ **QUARENTENA APLICADA:** {usuario.mention} foi isolado e o sistema Anti-Raid está em ação.", delete_after=10)
            except discord.Forbidden:
                await ctx.send("❌ Não tenho permissão para modificar cargos do usuário (verifique a hierarquia).", delete_after=15)
            except Exception as e:
                print(f"Erro ao aplicar quarentena: {e}")

        for channel in guild.text_channels:
            try:
                def is_target(message: discord.Message) -> bool:
                    return message.author == usuario

                deleted: List[discord.Message] = await channel.purge(limit=limite, check=is_target)

                if deleted:
                    mensagens_apagadas += len(deleted)
                    await channel.send(
                        f"🛡️ **SISTEMA DE AUTODEFESA ACIONADO** 🛡️\n"
                        f"O membro {usuario.mention} está em **QUARENTENA** por suspeita de RAID. "
                        f"Suas últimas **{len(deleted)}** mensagens neste canal foram removidas.",
                        delete_after=120
                    )

            except discord.Forbidden:
                continue
            except Exception as e:
                print(f"Erro ao limpar mensagens em {channel.name}: {e}")
                continue

        if log_channel:
            embed = discord.Embed(
                title="🚨 AÇÃO ANTI-RAID: Limpeza Global & Quarentena",
                description="Conta comprometida detectada e isolada. Limpeza de mensagens concluída.",
                color=discord.Color.red()
            )
            embed.add_field(name="Usuário Alvo", value=usuario.mention, inline=True)
            embed.add_field(name="Total Apagado", value=f"{mensagens_apagadas} mensagens", inline=True)
            embed.add_field(name="Quarentena Aplicada", value="Sim" if quarantine_role else "Não (Cargo não configurado)", inline=False)
            embed.add_field(name="Executado Por", value=ctx.author.mention, inline=False)
            embed.timestamp = datetime.now()
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        log_channel: Optional[discord.TextChannel] = self.get_log_channel(message.guild)
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Verifica convites (regex pré-compilada para melhor performance)
        if self.invite_regex.search(message.content):
            await message.delete()
            if log_channel:
                await log_channel.send(f"🚫 Convite bloqueado ({now}) de {message.author.mention}:\n`{message.content}`")
            await message.channel.send(f"{message.author.mention}, enviar convites é proibido.", delete_after=5)
            return

        # Verifica palavrões (regex compilada para melhor performance)
        if self.badwords_regex and self.badwords_regex.search(message.content):
            await message.delete()
            if log_channel:
                await log_channel.send(f"⚠ Palavrão detectado ({now}) de {message.author.mention}:\n`{message.content}`")
            return

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))

# ============================================================
# Atualizado em: 2025-11-23 22:41:53 (Horário de Brasília)
# ============================================================
