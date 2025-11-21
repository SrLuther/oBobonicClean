import discord
from discord.ext import commands
from config import STAFF_ROLE_ID

class Comandos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ajuda")
    async def ajuda(self, ctx):
        embed = discord.Embed(
            title="📜 Lista de Comandos do oBobonic",
            description="Aqui estão todos os comandos disponíveis e o que eles fazem:",
            color=discord.Color.green()
        )

        # --- Tickets ---
        embed.add_field(name="🎫 Comandos de Tickets", value=(
            "`!ticket` — Moderador envia e fixa o painel de tickets no canal específico.\n"
            "`!abrirticket` — Abre um ticket de suporte (através do botão no painel).\n"
            "`!aceitarticket <ticket>` — Moderador aceita um ticket (através do botão no ticket).\n"
            "`!fecharticket <ticket>` — Moderador fecha e arquiva um ticket (através do botão no ticket).\n\n"
            "ℹ️ **Como funciona:**\n"
            "• Apenas moderadores podem usar `!ticket`, e apenas no canal designado.\n"
            "• Usuários clicam no botão 'Abrir Ticket' para criar seu ticket.\n"
            "• Moderadores clicam em 'Aceitar Ticket' para começar a atender.\n"
            "• O botão 'Fechar (Moderação)' encerra e arquiva o ticket.\n"
            "• Tickets inativos por 48h são fechados automaticamente."
        ), inline=False)

        # --- Limpeza / Mensagens ---
        embed.add_field(name="🧹 Comandos de Limpeza", value=(
            "`!faxina` — Limpa o máximo de mensagens que o bot conseguir do canal.\n"
            "`!limpar <x>` — Deleta mensagens cumulativas até atingir x caracteres.\n"
            "⚠️ Ambos os comandos exigem permissão de **Gerenciar Mensagens**."
        ), inline=False)

        # --- Administração ---
        embed.add_field(name="⚙️ Administração", value=(
            "`!reload <cog>` — Recarrega uma extensão (admin/moderador).\n"
            "`!load <cog>` — Carrega uma extensão.\n"
            "`!unload <cog>` — Descarrega uma extensão.\n"
        ), inline=False)

        # --- Moderação ---
        embed.add_field(name="🛡️ Moderação", value=(
            "`!ban <usuário> [motivo]` — Bane um usuário.\n"
            "`!kick <usuário> [motivo]` — Expulsa um usuário.\n"
            "`!mute <usuário> [tempo]` — Silencia um usuário.\n"
            "`!unmute <usuário>` — Remove o silêncio.\n"
            "`!warn <usuário> [motivo]` — Adiciona advertência.\n"
            "`!warnings <usuário>` — Mostra advertências de um usuário.\n"
        ), inline=False)

        # --- XP / Experiência ---
        embed.add_field(name="⭐ XP", value=(
            "`!xp <usuário>` — Mostra o XP atual de um usuário.\n"
            "`!rank <usuário>` — Mostra a posição no ranking.\n"
        ), inline=False)

        # --- Comando de ajuda ---
        embed.add_field(name="📌 Utilitário", value="`!ajuda` — Mostra esta mensagem de ajuda.", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="ticket")
    @commands.has_role(STAFF_ROLE_ID)  # apenas moderadores
    async def ticket(self, ctx):
        allowed_channel_id = 1440909767974453328
        if ctx.channel.id != allowed_channel_id:
            await ctx.send(f"❌ Este comando só pode ser usado no canal <#{allowed_channel_id}>.", delete_after=10)
            await ctx.message.delete()
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
        # TicketPanelView precisa estar importado ou definido no mesmo arquivo do cog
        view = self.bot.get_cog("TicketSystem").__class__.TicketPanelView()  # pega a view do cog de tickets
        message = await ctx.send(embed=embed, view=view)
        await message.pin()
        await ctx.message.delete()

    @commands.command(name="faxina")
    @commands.has_permissions(manage_messages=True)
    async def faxina(self, ctx):
        """Deleta o máximo de mensagens do canal"""
        try:
            deleted = await ctx.channel.purge()
            await ctx.send(f"🧹 Faxina feita! {len(deleted)} mensagens deletadas.", delete_after=5)
        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissão para deletar mensagens neste canal.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Ocorreu um erro ao tentar deletar as mensagens: {e}")

    @commands.command(name="limpar")
    @commands.has_permissions(manage_messages=True)
    async def limpar(self, ctx, quantidade: int):
        """Deleta mensagens cumulativas até atingir a quantidade de caracteres especificada"""
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

# --- Setup da cog ---
async def setup(bot):
    await bot.add_cog(Comandos(bot))
