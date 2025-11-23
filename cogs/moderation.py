from discord.ext import commands
import discord
import re
import os
from datetime import datetime
# Importando IDs necessários para logs e quarentena
from config import CANAL_LOGS_ID, QUARANTINE_ROLE_ID 

# ==============================================================================
# 🛡️ CLASSE PRINCIPAL: Moderation (Filtros e Comandos de Ação Rápida)
# ==============================================================================
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            # Tenta carregar a lista de palavrões
            with open("palavroes.txt", "r", encoding="utf8") as f:
                self.badwords = [w.strip().lower() for w in f.readlines()]
        except FileNotFoundError:
            print("⚠️ Arquivo palavroes.txt não encontrado. Filtro de palavrões desativado.")
            self.badwords = []

    def get_log_channel(self, guild):
        """Retorna o canal de logs (CANAL_LOGS_ID) para auditoria."""
        return self.bot.get_channel(CANAL_LOGS_ID)

    # ----------------------------------------------------------------------
    # A. COMANDOS DE LIMPEZA
    # ----------------------------------------------------------------------

    @commands.command(name="faxina", aliases=['purgeall'])
    @commands.has_permissions(manage_messages=True)
    async def faxina(self, ctx):
        """Apaga todas as mensagens no canal atual (Ação Imediata)."""
        await ctx.message.delete()
        try:
            # Deleta todas as mensagens no canal
            deleted = await ctx.channel.purge()
            
            # 1. Log de Auditoria
            log_channel = self.get_log_channel(ctx.guild)
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
    async def limpar(self, ctx, quantidade: int):
        """Apaga mensagens até que a soma dos caracteres atinja a quantidade especificada."""
        await ctx.message.delete()
        if quantidade <= 0:
            await ctx.send("❌ A quantidade de caracteres precisa ser maior que 0.", delete_after=5)
            return

        contador = 0
        mensagens = []

        # Itera o histórico para somar o tamanho dos caracteres
        async for msg in ctx.channel.history(limit=None):
            contador += len(msg.content)
            mensagens.append(msg)
            if contador >= quantidade:
                break

        if mensagens:
            try:
                await ctx.channel.delete_messages(mensagens)
                
                # 1. Log de Auditoria
                log_channel = self.get_log_channel(ctx.guild)
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
    async def limpezageral(self, ctx, usuario: discord.Member, limite: int = 200):
        """
        🛑 COMANDO ANTI-RAID 🛑 
        Apaga as últimas N mensagens de um usuário em todos os canais de texto e aplica Quarentena.
        """
        if not 1 <= limite <= 1000:
            return await ctx.send("O limite deve ser entre 1 e 1000.")

        await ctx.message.delete()
        
        log_channel = self.get_log_channel(ctx.guild)
        mensagens_apagadas = 0
        
        # 1. Aplicar Quarentena (Ação Imediata)
        quarantine_role = ctx.guild.get_role(QUARANTINE_ROLE_ID)
        if quarantine_role:
            try:
                # Remove todos os cargos e aplica o cargo de quarentena
                await usuario.edit(roles=[quarantine_role], reason="Conta comprometida/Raid - Quarentena.")
                
                # Log imediato no canal de moderação
                await ctx.send(f"🛡️ **QUARENTENA APLICADA:** {usuario.mention} foi isolado e o sistema Anti-Raid está em ação.", delete_after=10)
            except discord.Forbidden:
                await ctx.send("❌ Não tenho permissão para modificar cargos do usuário (verifique a hierarquia).", delete_after=15)
            except Exception as e:
                 print(f"Erro ao aplicar quarentena: {e}")

        # 2. Limpeza Global de Mensagens e Notificação por Canal
        for channel in ctx.guild.text_channels:
            try:
                def is_target(message):
                    return message.author == usuario

                deleted = await channel.purge(limit=limite, check=is_target)
                
                if deleted:
                    mensagens_apagadas += len(deleted)
                    
                    # Enviar notificação no canal após a limpeza
                    await channel.send(
                        f"🛡️ **SISTEMA DE AUTODEFESA ACIONADO** 🛡️\n"
                        f"O membro {usuario.mention} está em **QUARENTENA** por suspeita de RAID. "
                        f"Suas últimas **{len(deleted)}** mensagens neste canal foram removidas.",
                        delete_after=120 # Auto-deleta a mensagem de aviso após 2 minutos
                    )
                
            except discord.Forbidden:
                continue
            except Exception as e:
                print(f"Erro ao limpar mensagens em {channel.name}: {e}")
                continue

        # 3. Log de Auditoria Final
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


    # ----------------------------------------------------------------------
    # B. FILTROS DE MENSAGENS (on_message)
    # ----------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        log_channel = self.get_log_channel(message.guild)
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Bloqueio de convites
        convite_regex = r"(discord\.gg/|discord\.com/invite/)"
        if re.search(convite_regex, message.content.lower()):
            await message.delete()
            if log_channel:
                await log_channel.send(f"🚫 Convite bloqueado ({now}) de {message.author.mention}:\n`{message.content}`")
            await message.channel.send(f"{message.author.mention}, enviar convites é proibido.", delete_after=5)
            return

        # Bloqueio de palavrões
        if any(bad in message.content.lower() for bad in self.badwords):
            await message.delete()
            if log_channel:
                await log_channel.send(f"⚠ Palavrão detectado ({now}) de {message.author.mention}:\n`{message.content}`")
            return


# ==============================================================================
# ⚙️ FUNÇÃO DE SETUP
# ==============================================================================
async def setup(bot):
    await bot.add_cog(Moderation(bot))