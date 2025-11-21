import discord
from discord.ext import commands

# ID do cargo moderador
MOD_ROLE_ID = 1440828412599210135
# ID do canal específico para enviar o painel de tickets
TICKET_CHANNEL_ID = 1440909767974453328

class Comandos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------------------- Ajuda --------------------
    @commands.command(name="ajuda")
    async def ajuda(self, ctx):
        embed = discord.Embed(
            title="📜 Lista de Comandos do oBobonic",
            description="Aqui estão todos os comandos disponíveis e o que eles fazem:",
            color=discord.Color.green()
        )

        # 🎫 Tickets
        embed.add_field(
            name="🎫 Tickets",
            value=(
                "**Comandos:**\n"
                "• `!ticket` — Moderador envia e fixa o painel de tickets (canal específico).\n"
                "• `!abrirticket` — Abre um ticket de suporte (através do botão no painel).\n"
                "• `!aceitarticket <ticket>` — Moderador aceita um ticket (através do botão no ticket).\n"
                "• `!fecharticket <ticket>` — Moderador fecha e arquiva um ticket (através do botão no ticket).\n\n"
                "**Como funciona:**\n"
                "• Apenas moderadores podem usar `!ticket`, e somente no canal designado.\n"
                "• Usuários clicam no botão 'Abrir Ticket' para criar seu ticket.\n"
                "• Moderadores clicam em 'Aceitar Ticket' para começar a atender.\n"
                "• O botão 'Fechar (Moderação)' encerra e arquiva o ticket.\n"
                "• Tickets inativos por 48h são fechados automaticamente."
            ),
            inline=False
        )

        # 🧹 Limpeza / Mensagens
        embed.add_field(
            name="🧹 Limpeza / Mensagens",
            value=(
                "• `!faxina` — Limpa o máximo de mensagens do canal.\n"
                "• `!limpar <x>` — Deleta mensagens cumulativas até atingir x caracteres.\n"
                "⚠️ Ambos os comandos exigem permissão de **Gerenciar Mensagens**."
            ),
            inline=False
        )

        # ⚙️ Administração
        embed.add_field(
            name="⚙️ Administração",
            value=(
                "• `!reload <cog>` — Recarrega uma extensão (admin/moderador).\n"
                "• `!load <cog>` — Carrega uma extensão.\n"
                "• `!unload <cog>` — Descarrega uma extensão."
            ),
            inline=False
        )

        # 🛡️ Moderação
        embed.add_field(
            name="🛡️ Moderação",
            value=(
                "• `!ban <usuário> [motivo]` — Bane um usuário.\n"
                "• `!kick <usuário> [motivo]` — Expulsa um usuário.\n"
                "• `!mute <usuário> [tempo]` — Silencia um usuário.\n"
                "• `!unmute <usuário>` — Remove o silêncio.\n"
                "• `!warn <usuário> [motivo]` — Adiciona advertência.\n"
                "• `!warnings <usuário>` — Mostra advertências de um usuário."
            ),
            inline=False
        )

        # ⭐ XP / Ranking
        embed.add_field(
            name="⭐ XP / Ranking",
            value=(
                "• `!xp <usuário>` — Mostra o XP atual de um usuário.\n"
                "• `!rank <usuário>` — Mostra a posição no ranking."
            ),
            inline=False
        )

        # 📌 Utilitário
        embed.add_field(
            name="📌 Utilitário",
            value="• `!ajuda` — Mostra esta mensagem de ajuda.",
            inline=False
        )

        await ctx.send(embed=embed)

    # -------------------- Comando Ticket --------------------
    @commands.command(name="ticket")
    @commands.has_role(MOD_ROLE_ID)
    async def ticket(self, ctx):
        if ctx.channel.id != TICKET_CHANNEL_ID:
            await ctx.send(f"❌ Este comando só pode ser usado no canal <#{TICKET_CHANNEL_ID}>.", delete_after=10)
            await ctx.message.delete()
            return

        cog = self.bot.get_cog("TicketSystem")
        if cog is None:
            await ctx.send("❌ Cog de Tickets não carregado. Contate o administrador.", delete_after=10)
            return

        try:
            view = cog.__class__.TicketPanelView()
        except Exception as e:
            await ctx.send(f"❌ Erro ao criar o painel de tickets: {e}", delete_after=10)
            return

        embed = discord.Embed(
            title="🎫 Sistema de Tickets",
            description=(
                "• Clique no botão abaixo para abrir um ticket.\n"
                "• Moderadores podem aceitar e fechar tickets.\n"
                "• Tempo máximo de inatividade: 48h.\n\n"
                "Se precisar de ajuda, aguarde um moderador aceitar seu ticket."
            ),
            color=discord.Color.blurple()
        )

        message = await ctx.send(embed=embed, view=view)
        await message.pin()
        await ctx.message.delete()

    # -------------------- Faxina --------------------
    @commands.command(name="faxina")
    @commands.has_permissions(manage_messages=True)
    async def faxina(self, ctx):
        try:
            deleted = await ctx.channel.purge()
            await ctx.send(f"🧹 Faxina feita! {len(deleted)} mensagens deletadas.", delete_after=5)
        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissão para deletar mensagens neste canal.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Ocorreu um erro ao tentar deletar as mensagens: {e}")

    # -------------------- Limpar --------------------
    @commands.command(name="limpar")
    @commands.has_permissions(manage_messages=True)
    async def limpar(self, ctx, quantidade: int):
        if quantidade <= 0:
            await ctx.send("❌ A quantidade de caracteres precisa ser maior que 0.", delete_after=5)
            return

        contador = 0
        mensagens = []

        async for msg in ctx.channel.history(limit=None):
            contador += len(msg.content)
            mensagens.append(msg)
            if contador >= quantidade:
                break

        if mensagens:
            try:
                await ctx.channel.delete_messages(mensagens)
                await ctx.send(f"🧹 Mensagens deletadas até atingir {quantidade} caracteres.", delete_after=5)
            except discord.Forbidden:
                await ctx.send("❌ Não tenho permissão para deletar mensagens neste canal.")
            except discord.HTTPException as e:
                await ctx.send(f"❌ Ocorreu um erro ao tentar deletar as mensagens: {e}")
        else:
            await ctx.send("⚠️ Não foram encontradas mensagens para deletar.", delete_after=5)

# -------------------- Setup da Cog --------------------
async def setup(bot):
    await bot.add_cog(Comandos(bot))
