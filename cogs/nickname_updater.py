"""
Cog para atualizar automaticamente o apelido (nickname) dos membros
com base em cargos específicos.

Funciona com discord.py
"""

import discord
from discord.ext import commands
import config
from nicknameUpdater import (
    get_highest_priority_prefix,
    update_member_nickname,
    sync_all_members_nicknames,
    PREFIX_MAP,
    PRIORITY_ORDER
)


class NicknameUpdaterCog(commands.Cog):
    """
    Gerencia a atualização automática de apelidos baseado em cargos.
    
    Cargos suportados:
    - [DEV] 1440828410556321882
    - [ADM] 1476370938969980928
    - [GM] 1440828412599210135
    - [VIP] 1476371640244899963
    - [Tester] 1476780071090917416
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("[NicknameUpdater] 🎯 Cog inicializada!")

    async def cog_load(self) -> None:
        """
        Chamado quando a cog é carregada.
        Executa a sincronização inicial de apelidos.
        """
        print("[NicknameUpdater] 📍 Cog_load() chamado!")
        
        # Aguardar um pouco para garantir que o bot está pronto
        import asyncio
        await asyncio.sleep(2)
        
        # Sincronizar apelidos de todos os membros existentes
        try:
            # Obter a guild configurada
            guild = self.bot.get_guild(config.GUILD_ID)
            if guild:
                print("\n🔄 Sincronizando apelidos de membros existentes...")
                stats = await sync_all_members_nicknames(guild)
                print(f"📊 Resultados: {stats['updated']} atualizados, "
                      f"{stats['skipped']} sem alterações, "
                      f"{stats['failed']} erros\n")
        except Exception as e:
            print(f"⚠️ Erro ao sincronizar apelidos na cog_load: {e}")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Listener que detecta quando um membro é atualizado (cargos, apelido, etc).
        Atualiza o apelido automaticamente se os cargos forem alterados.
        """
        # Verificar se os cargos foram alterados
        roles_before = set(role.id for role in before.roles)
        roles_after = set(role.id for role in after.roles)
        
        roles_changed = roles_before != roles_after

        if not roles_changed:
            return

        # Atualizar o apelido do membro
        await update_member_nickname(after)

    @commands.command(
        name="sincapelidos",
        aliases=["sync_nicks", "synck", "sincnicks"],
        description="Sincroniza os apelidos de todos os membros com seus cargos."
    )
    @commands.has_permissions(administrator=True)
    async def sync_nicknames_command(self, ctx: commands.Context):
        """
        Comando para sincronizar manualmente os apelidos de todos os membros.
        
        Uso: !sincapelidos
        
        Requer: Permissão de administrador
        """
        await ctx.defer()
        
        try:
            embed = discord.Embed(
                title="🔄 Sincronizando Apelidos",
                description="Processando todos os membros do servidor...",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            
            # Executar sincronização
            stats = await sync_all_members_nicknames(ctx.guild)
            
            # Criar embed de resultado
            result_embed = discord.Embed(
                title="✅ Sincronização Completa!",
                color=discord.Color.green()
            )
            
            result_embed.add_field(
                name="📊 Estatísticas",
                value=(
                    f"✅ **Atualizados:** {stats['updated']}\n"
                    f"⏭️ **Sem alterações:** {stats['skipped']}\n"
                    f"❌ **Erros:** {stats['failed']}"
                ),
                inline=False
            )
            
            result_embed.add_field(
                name="📋 Cargos Sincronizados",
                value=(
                    f"🔷 **[DEV]** - ID: 1440828410556321882\n"
                    f"🟥 **[ADM]** - ID: 1476370938969980928\n"
                    f"🟨 **[GM]** - ID: 1440828412599210135\n"
                    f"💜 **[VIP]** - ID: 1476371640244899963\n"
                    f"🧪 **[Tester]** - ID: 1476780071090917416"
                ),
                inline=False
            )
            
            result_embed.set_footer(text="Sincronização realizada por " + str(ctx.author))
            
            await ctx.send(embed=result_embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Erro na Sincronização",
                description=f"```{str(e)}```",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)

    @commands.command(
        name="cargosape",
        aliases=["roles_nick", "nickroles"],
        description="Mostra a lista de cargos que afetam o apelido."
    )
    async def show_roles_command(self, ctx: commands.Context):
        """
        Mostra quais cargos são usados para atualizar apelidos.
        
        Uso: !cargosape
        """
        embed = discord.Embed(
            title="🏷️ Cargos que Afetam Apelido",
            description="Estes cargos são automaticamente adicionados ao seu apelido.",
            color=discord.Color.blurple()
        )
        
        embed.add_field(
            name="🔷 [DEV]",
            value=f"`1440828410556321882`\nPrefixo: `[DEV]`",
            inline=True
        )
        
        embed.add_field(
            name="🟥 [ADM]",
            value=f"`1476370938969980928`\nPrefixo: `[ADM]`",
            inline=True
        )
        
        embed.add_field(
            name="🟨 [GM]",
            value=f"`1440828412599210135`\nPrefixo: `[GM]`",
            inline=True
        )
        
        embed.add_field(
            name="💜 [VIP]",
            value=f"`1476371640244899963`\nPrefixo: `[VIP]`",
            inline=True
        )
        
        embed.add_field(
            name="🧪 [Tester]",
            value=f"`1476780071090917416`\nPrefixo: `[Tester]`",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Ordem de Prioridade",
            value=(
                "Se você tiver múltiplos cargos, o de **maior prioridade** será usado:\n\n"
                "1. **[DEV]** (Maior prioridade)\n"
                "2. **[ADM]**\n"
                "3. **[GM]**\n"
                "4. **[VIP]**\n"
                "5. **[Tester]** (Menor prioridade)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📌 Como Funciona",
            value=(
                "✅ Quando você recebe um dos cargos acima, seu apelido é automaticamente atualizado.\n"
                "✅ Se você tiver múltiplos cargos, o prefixo de maior prioridade é usado.\n"
                "✅ Se você perder todos os cargos, o prefixo é removido.\n"
                "✅ Exemplo: `[DEV] Ciano` ou `[VIP] Lucas`"
            ),
            inline=False
        )
        
        embed.set_footer(text="Sistema automático de apelidos")
        
        await ctx.send(embed=embed)

    @commands.command(
        name="meuapelido",
        aliases=["mynick", "nick_info"],
        description="Mostra seu apelido atual e que cargo determina ele."
    )
    async def my_nickname_command(self, ctx: commands.Context):
        """
        Mostra informações sobre o apelido do autor da mensagem.
        
        Uso: !meuapelido
        """
        # Garantir que temos um Member (tem nick e roles) e não um User
        member = ctx.guild.get_member(ctx.author.id) if ctx.guild else None
        if not isinstance(member, discord.Member):
            await ctx.send("❌ Este comando só pode ser usado dentro de um servidor.", ephemeral=True)
            return

        highest_prefix = get_highest_priority_prefix(member)
        base_name = member.global_name or member.name
        current_nickname = member.nick or base_name
        
        embed = discord.Embed(
            title="📝 Informações do Apelido",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="👤 Nome de Usuário",
            value=f"`{base_name}`",
            inline=False
        )
        
        embed.add_field(
            name="🏷️ Apelido Atual",
            value=f"`{current_nickname}`",
            inline=False
        )
        
        # Listar cargos do usuário que afetam apelido
        relevant_roles = []
        for role_id_str in PRIORITY_ORDER:
            role_id = int(role_id_str)
            if any(role.id == role_id for role in member.roles):
                prefix = PREFIX_MAP[role_id_str]
                relevant_roles.append(f"{prefix}")
        
        if relevant_roles:
            embed.add_field(
                name="🎖️ Cargos que Afetam Apelido",
                value="\n".join(relevant_roles),
                inline=False
            )
            
            embed.add_field(
                name="⭐ Prefixo Atual",
                value=f"`{highest_prefix}`",
                inline=False
            )
        else:
            embed.add_field(
                name="🎖️ Cargos que Afetam Apelido",
                value="Você não possui nenhum cargo com prefixo.",
                inline=False
            )
        
        embed.set_footer(text="O apelido é sincronizado automaticamente com seus cargos.")
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """
    Setup da cog - chamado automaticamente pelo bot.
    """
    await bot.add_cog(NicknameUpdaterCog(bot))
    print("[NicknameUpdater] ✅ Cog carregada com sucesso!")
