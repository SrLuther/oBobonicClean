import discord
from discord.ext import commands
from discord.ext.commands import MissingPermissions, NotOwner
from config import CANAL_LOGS_ID # Importa o ID do canal de logs para auditoria
from datetime import datetime
import sys # 🛑 NOVO: Necessário para forçar o código de saída no restart

# ==============================================================================
# 🛠️ CLASSE PRINCIPAL: Admin (Gerencia comandos de manutenção e controle)
# ==============================================================================
class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ----------------------------------------------------------------------
    # 1. COMANDOS DE MANUTENÇÃO (RELOAD, LOAD, UNLOAD, RESTART)
    # ----------------------------------------------------------------------
    
    @commands.command(aliases=['recarregar'])
    @commands.has_permissions(administrator=True)
    async def reload(self, ctx, cog_name: str):
        """Recarrega um cog existente em tempo de execução."""
        module_name = f"cogs.{cog_name}" 
        
        try:
            await self.bot.reload_extension(module_name)
            await ctx.send(f"♻️ Cog `{cog_name}` recarregado com sucesso!", delete_after=10)

            # Log para canal de logs (Auditoria Aprimorada com Embed)
            canal_logs = self.bot.get_channel(CANAL_LOGS_ID)
            if canal_logs:
                embed = discord.Embed(
                    title="🔄 Cog Recarregado",
                    description=f"A extensão **`{cog_name}`** foi recarregada manualmente por segurança.",
                    color=discord.Color.gold()
                )
                embed.set_footer(text=f"Ação executada por: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
                embed.timestamp = datetime.now()
                await canal_logs.send(embed=embed)
                
        except commands.ExtensionNotLoaded:
            await ctx.send(f"❌ Cog `{cog_name}` não está carregado. Use `!load {cog_name}`.", delete_after=10)
        except Exception as e:
            await ctx.send(f"❌ Falha ao recarregar `{cog_name}`: ```{e}```", delete_after=20)


    @commands.command(aliases=['carregar'])
    @commands.has_permissions(administrator=True)
    async def load(self, ctx, cog_name: str):
        """Carrega um cog que não está ativo."""
        module_name = f"cogs.{cog_name}"
        try:
            await self.bot.load_extension(module_name)
            await ctx.send(f"✅ Cog `{cog_name}` carregado com sucesso!", delete_after=10)
        except commands.ExtensionAlreadyLoaded:
            await ctx.send(f"⚠️ Cog `{cog_name}` já está carregado.", delete_after=10)
        except Exception as e:
            await ctx.send(f"❌ Falha ao carregar `{cog_name}`: ```{e}```", delete_after=20)


    @commands.command(aliases=['descarregar'])
    @commands.has_permissions(administrator=True)
    async def unload(self, ctx, cog_name: str):
        """Descarrega temporariamente um cog."""
        module_name = f"cogs.{cog_name}"
        try:
            # Proteção contra descarregar o próprio cog de administração
            if cog_name.lower() == 'admin': 
                await ctx.send("🛑 Não é possível descarregar o próprio cog de administração.", delete_after=10)
                return

            await self.bot.unload_extension(module_name)
            await ctx.send(f"💤 Cog `{cog_name}` descarregado com sucesso!", delete_after=10)
        except commands.ExtensionNotLoaded:
            await ctx.send(f"⚠️ Cog `{cog_name}` não está carregado/ativo para ser descarregado.", delete_after=10)
        except Exception as e:
            await ctx.send(f"❌ Falha ao descarregar `{cog_name}`: ```{e}```", delete_after=20)
            
            
    @commands.command(aliases=['reboot', 'reiniciar'])
    @commands.has_permissions(administrator=True)
    async def restart(self, ctx):
        """Reinicia o bot completamente."""
        try:
            await ctx.send("🟠 Reiniciando o Bobonic... Voltarei em um instante.", delete_after=10)
            
            # Log de auditoria de restart
            canal_logs = self.bot.get_channel(CANAL_LOGS_ID)
            if canal_logs:
                embed = discord.Embed(
                    title="🟠 Reiniciando o Bot",
                    description=f"Bot reiniciado manualmente por {ctx.author.mention}.",
                    color=discord.Color.orange()
                )
                embed.timestamp = datetime.now()
                await canal_logs.send(embed=embed)
            
            # 1. Fecha a conexão do Discord
            await self.bot.close() 
            # 2. Define o código de saída (24 é um código padrão para 'restart')
            sys.exit(24) 
            
        except Exception as e:
            await ctx.send(f"❌ Erro ao tentar reiniciar: {e}")

    # ----------------------------------------------------------------------
    # 2. COMANDO DE DESLIGAMENTO CONTROLADO
    # ----------------------------------------------------------------------

    @commands.command(aliases=['desligar'])
    @commands.has_permissions(administrator=True)
    async def shutdown(self, ctx):
        """Desliga o bot de forma controlada."""
        await ctx.send("🔴 Desligando o Bobonic... Adeus.", delete_after=10)
        
        # Log de auditoria de shutdown
        canal_logs = self.bot.get_channel(CANAL_LOGS_ID)
        if canal_logs:
            embed = discord.Embed(
                title="🔴 Bot Desligado",
                description=f"Bot desligado manualmente por {ctx.author.mention}.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Processo encerrado.")
            embed.timestamp = datetime.now()
            await canal_logs.send(embed=embed)
        
        await self.bot.close() # Encerra a conexão com o Discord
        

    # ----------------------------------------------------------------------
    # 3. TRATAMENTO DE ERROS DE PERMISSÃO (MELHORIA)
    # ----------------------------------------------------------------------
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # Ignora erros que não são deste cog
        if ctx.cog != self or ctx.command.name not in ['reload', 'load', 'unload', 'shutdown', 'restart']:
            return
            
        if isinstance(error, MissingPermissions):
            await ctx.send("❌ **Acesso Negado:** Você não tem a permissão de **Administrador** para usar este comando.", delete_after=10)
        elif isinstance(error, NotOwner):
            await ctx.send("❌ **Acesso Negado:** Somente o Proprietário do Bot pode executar este comando.", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"⚠️ **Argumento Faltando:** Você deve especificar o nome do cog. Exemplo: `!{ctx.command.name} autoresponse`", delete_after=10)
        else:
            # Para o desenvolvedor, logar erros não esperados
            print(f"Erro inesperado no comando {ctx.command.name} por {ctx.author}: {error}")


# ==============================================================================
# ⚙️ FUNÇÃO DE SETUP
# ==============================================================================
async def setup(bot):
    await bot.add_cog(Admin(bot))