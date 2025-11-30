# cogs/comandos.py
import discord
from discord.ext import commands
from typing import Any, Dict, List

class ComandosCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.descriptions: Dict[str, str] = {
            "bobo": "Exibe a lista de comandos disponível.",
            "comandos": "Exibe a lista de comandos disponível.",
            "ajuda": "Exibe a lista de comandos disponível.",
            "echo": "Repete a mensagem enviada.",
            "ia": "Chat com IA (Gemini).",
            "chat": "Chat com IA (Gemini).",
            "imagem": "Gera imagem via Gemini Imagen.",
            "img": "Gera imagem via Gemini Imagen.",
            "gerar": "Gera imagem via Gemini Imagen.",
            "xp": "Mostra seu nível e XP.",
            "level": "Mostra seu nível e XP.",
            "lvl": "Mostra seu nível e XP.",
            "promo": "Busca e publica promoções de jogos.",
            "faxina": "Apaga todas as mensagens do canal.",
            "limpar": "Apaga mensagens até atingir N caracteres.",
            "limpezageral": "Purge global de mensagens de um usuário.",
            "testar_boas_vindas": "Envia mensagem de boas-vindas de teste.",
            "reload": "Recarrega uma extensão (admin).",
            "load": "Carrega uma extensão (admin).",
            "unload": "Descarrega uma extensão (admin).",
            "restart": "Reinicia o bot (admin).",
            "shutdown": "Desliga o bot (admin)."
        }

    @commands.command(name="bobo", aliases=["comandos", "ajuda"])
    async def help_command(self, ctx: commands.Context[Any]):
        try:
            resolved = await self.bot.get_prefix(ctx.message)
            if isinstance(resolved, str):
                prefix = resolved
            else:
                prefix = resolved[0] if resolved else "!"
        except Exception:
            prefix = "!"

        embed = discord.Embed(
            title="📚 Comandos do Bot",
            description="Lista dinâmica de comandos disponíveis por categoria.",
            color=discord.Color.blue()
        )

        groups: Dict[str, List[str]] = {}
        for cmd in sorted(self.bot.commands, key=lambda c: (c.cog_name or "", c.name)):
            group = cmd.cog_name or "Outros"
            aliases = f" (aliases: {', '.join(cmd.aliases)})" if getattr(cmd, "aliases", None) else ""
            base = f"`{prefix}{cmd.name}`{aliases}"
            desc = (cmd.help or "").strip() or self.descriptions.get(cmd.name) or "Sem descrição"
            entry = f"{base} — {desc}"
            groups.setdefault(group, []).append(entry)

        for group_name, items in groups.items():
            value = "\n".join(items) if items else "Nenhum comando"
            embed.add_field(name=group_name, value=value, inline=False)

        embed.set_footer(text=f"Prefixo atual: {prefix}")
        await ctx.send(embed=embed)

    @commands.command(name="echo")
    async def echo_command(self, ctx: commands.Context[Any], *, message: str):
        await ctx.send(message)

async def setup(bot: commands.Bot):
    await bot.add_cog(ComandosCog(bot))

# ============================================================
# Atualizado em: 2025-11-23 22:41:53 (Horário de Brasília)
# ============================================================
