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
        title="💜 VIP — ARK Land BR",
        description=(
            "Apoie o servidor e ganhe vantagens exclusivas!\n"
            "Sua contribuição mantém os servidores online e ajuda a comunidade a crescer.\n\n"
            "═══════════════════════════════════════"
        ),
        color=discord.Color.from_rgb(148, 0, 211)
    )

    embed.add_field(
        name="💎 Benefícios VIP",
        value=(
            "🏷️ **Cargo exclusivo `[VIP]`** no seu apelido\n"
            "🛒 **Acesso ao canal de lojas VIP**\n"
            "⚡ **Prioridade no suporte via tickets**\n"
            "🎨 **Canais exclusivos para membros VIP**\n"
            "🦕 **Acesso antecipado a eventos e sorteios**\n"
            "📣 **Poder criar anúncios em canais especiais**\n"
            "🎁 **Itens e pacotes exclusivos no servidor ARK**"
        ),
        inline=False
    )

    embed.add_field(
        name="📋 Como Funciona",
        value=(
            "1️⃣ Clique em **🛒 Assinar VIP** abaixo\n"
            "2️⃣ Escolha o plano que melhor te atende\n"
            "3️⃣ Realize o pagamento de forma segura\n"
            "4️⃣ Seu cargo VIP será aplicado automaticamente!\n\n"
            "> ⚠️ Problemas? Abra um ticket em <#1441608808086237265>"
        ),
        inline=False
    )

    embed.add_field(
        name="🌐 Loja",
        value=f"[arklandbr.tip4serv.com]({VIP_STORE_URL})",
        inline=True
    )

    embed.add_field(
        name="💬 Suporte",
        value="Tickets • Discord",
        inline=True
    )

    embed.set_footer(text="ARK Land BR • Obrigado por apoiar o servidor! 💜")
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
