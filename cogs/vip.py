# cogs/vip.py
"""
Painel VIP do servidor ARK Land BR
Exibe benefícios do VIP e redireciona para a loja de assinaturas
"""

import discord
from discord.ext import commands
from typing import Any

# ============================================
# CONFIGURAÇÃO
# ============================================
VIP_STORE_URL = "https://arklandbr.tip4serv.com/"
VIP_PAINEL_CONFIG_FILE = "data/vip_painel.json"
VIP_PANEL_CHANNEL_ID = 1476793873622630481  # Canal onde o painel VIP é enviado

import json
import os

def _salvar_vip_config(message_id: int, channel_id: int) -> None:
    os.makedirs("data", exist_ok=True)
    with open(VIP_PAINEL_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"message_id": message_id, "channel_id": channel_id}, f)

def _carregar_vip_config() -> dict:
    if not os.path.exists(VIP_PAINEL_CONFIG_FILE):
        return {}
    try:
        with open(VIP_PAINEL_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ============================================
# VIEW — BOTÃO LINK PARA A LOJA
# ============================================
class VipPainelView(discord.ui.View):
    """View persistente com botão de link para a loja VIP"""

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="💜 Assinar VIP",
            url=VIP_STORE_URL,
            style=discord.ButtonStyle.link,
            emoji="🛒"
        ))


# ============================================
# EMBED DO PAINEL
# ============================================
def _build_vip_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🌋 SISTEMA VIP ARKLAND – CONSTRUÍDO PELA TRIBO 🦖",
        description=(
            "Na **ARKLAND**, poder não é imposto.\n"
            "Ele é conquistado… e construído em conjunto.\n\n"
            "O nosso Sistema VIP já está disponível, mas existe um diferencial que torna tudo mais interessante:\n\n"
            "💬 **Os benefícios de cada VIP serão definidos junto com a comunidade.**\n\n"
            "Isso mesmo.\n"
            "Bronze, Prata, Ouro, Diamante e VIP Doação não serão apenas pacotes prontos. "
            "Eles serão moldados com a opinião dos jogadores que fazem o servidor existir.\n\n"
            "Você não está apenas comprando vantagens.\n"
            "**Você está ajudando a desenhar como elas funcionarão.**"
        ),
        color=discord.Color.from_rgb(148, 0, 211)
    )

    embed.add_field(
        name="💠 Planos disponíveis atualmente",
        value=(
            "• **VIP Bronze** — R$20\n"
            "• **VIP Prata** — R$30\n"
            "• **VIP Ouro** — R$50\n"
            "• **VIP Diamante** — R$75\n"
            "• **VIP Doação** — valor livre para apoiar o servidor"
        ),
        inline=False
    )

    embed.add_field(
        name="🔥 Por que participar agora?",
        value=(
            "Porque quem entra cedo ajuda a decidir:\n"
            "✔️ Quais bônus cada VIP terá\n"
            "✔️ Quais vantagens fazem sentido para o servidor\n"
            "✔️ Como manter o equilíbrio sem quebrar a experiência\n\n"
            "Além disso, você estará apoiando diretamente a evolução da ARKLAND "
            "durante o período de testes e ajustes."
        ),
        inline=False
    )

    embed.add_field(
        name="\u200b",
        value=(
            "Aqui, o VIP não é apenas um título.\n"
            "**É um voto. É influência. É presença ativa na construção do servidor.**\n\n"
            "🌎 A era está começando.\n"
            "*E quem ajuda a erguer o império… jamais é esquecido.*"
        ),
        inline=False
    )

    embed.set_footer(text="ARKLAND BR • Clique no botão abaixo para apoiar o servidor 💜")
    return embed


# ============================================
# COG
# ============================================
class VipCog(commands.Cog, name="VIP"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.painel_criado = False

    async def cog_load(self) -> None:
        """Registra a view persistente ao carregar o cog"""
        self.bot.add_view(VipPainelView())

    @commands.Cog.listener()
    async def on_ready(self):
        """Verifica se o painel VIP ainda existe ao iniciar"""
        if self.painel_criado:
            return
        self.painel_criado = True

        config = _carregar_vip_config()
        if not config:
            return

        guild = self.bot.get_guild(1440802112601854159)
        if not guild:
            return

        canal = guild.get_channel(int(config.get("channel_id", 0)))
        if not canal or not isinstance(canal, discord.TextChannel):
            return

        try:
            await canal.fetch_message(config["message_id"])
            print("✅ [VIP] Painel VIP encontrado e views registradas.")
        except discord.NotFound:
            print("⚠️ [VIP] Painel VIP não encontrado no canal. Use !painelvip para recriar.")

    @commands.command(name="painelvip", aliases=["vippainel", "criarvip"])
    @commands.has_permissions(administrator=True)
    async def painel_vip(self, ctx: commands.Context[Any]):
        """Cria o painel VIP no canal configurado"""
        try:
            await ctx.message.delete()
        except Exception:
            pass

        guild = ctx.guild
        if not guild:
            return

        canal = guild.get_channel(VIP_PANEL_CHANNEL_ID)
        if not canal or not isinstance(canal, discord.TextChannel):
            await ctx.send(f"❌ Canal VIP (ID: `{VIP_PANEL_CHANNEL_ID}`) não encontrado.", delete_after=8)
            return

        embed = _build_vip_embed()
        view = VipPainelView()
        msg = await canal.send(embed=embed, view=view)

        try:
            await msg.pin()
        except Exception:
            pass

        _salvar_vip_config(msg.id, canal.id)
        print(f"✅ [VIP] Painel VIP criado (ID: {msg.id}) no canal {canal.id}")

        await ctx.send(f"✅ Painel VIP criado em {canal.mention}!", delete_after=5)


async def setup(bot: commands.Bot):
    await bot.add_cog(VipCog(bot))
