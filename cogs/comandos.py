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
            "shutdown": "Desliga o bot (admin).",
            "regras": "Envia as regras do servidor (admin).",
            "rules": "Envia as regras do servidor (admin).",
            "ticketpanel": "Envia o painel de tickets (admin)."
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

    @commands.command(name="regras", aliases=["rules"])
    @commands.has_permissions(administrator=True)
    async def regras_command(self, ctx: commands.Context[Any]):
        """Envia as regras do servidor na sala de regras (admin only)"""
        try:
            RULES_CHANNEL_ID = 1473500120430673940
            canal_regras = self.bot.get_channel(RULES_CHANNEL_ID)
            
            if not isinstance(canal_regras, discord.TextChannel):
                await ctx.send(f"❌ Canal de regras ({RULES_CHANNEL_ID}) não encontrado.")
                return
            
            regras_completas = """# 🦕 REGRAS ARKLAND BRASIL – PVE 10x 🦖
**ARK: Survival Evolved | Cluster Completo**

**✅ PVE PURO – Sem PVP, sem grief, cooperação total**  
**Vigência:** 2026  
**Rates:** 10× | Mods: S+, Dino Storage, SpyGlass

══════════════════════════════════════════════════════════════

## 1. REGRAS BÁSICAS
• Idade mínima: 13 anos  
• Idioma: Português ou Inglês  
• **NUNCA** ataque players, tames ou bases (mesmo offline/soltos) → **BAN PERM**  
• Sem hacks, dupes, glitches, fly, clip → **BAN HWID**  
• Sem spam, flood, caps excessivo ou emotes repetidos → mute/kick  
• Ajude os novos! Cooperação é lei aqui

══════════════════════════════════════════════════════════════

## 2. BASES
• Máximo **3 bases principais** por mapa + secundárias pequenas (10×10)  
• Distância mínima: **200 m** entre tribos diferentes  
• **Proibido bloquear**:
  - Spawns (100 m livre ao redor)
  - Obelisks, beacons, drops, cavernas, boss arenas
  - Nodes iniciais de metal/cristal/obsidiana
• Pillar spam: máximo **50 estruturas vazias** por base  
• Decay: **7 dias**  
• Bases abandonadas (14 dias offline): anuncie no Discord e pode demolir

══════════════════════════════════════════════════════════════

## 3. DINOS & TAMING
• **Tames 100% protegidos** – nunca mate, roube, aggro ou abra inventário  
• Limite: **500 dinos por tribo por mapa**  
• Quilombos/kibble farms: ok, mas sem bloquear caminhos/spawns  
• Transfer cluster: **1 wyvern/rock drake/quetzal por semana** por tribo  
• Proibido deixar tames bloqueando cavernas, obelisks ou arenas

══════════════════════════════════════════════════════════════

## 4. RECURSOS & LOOT
• Sem loot steal (não mate dinos que outro está tameando)  
• Farm público: liberado, mas deixe rotas comuns acessíveis  
• Trades: use o canal #trades | **sem venda por dinheiro real**

══════════════════════════════════════════════════════════════

## 5. TRIBOS & ALIANÇAS
• Máximo **12 membros por tribo**  
• Alianças: até **3 tribos** (declare no Discord)  
• Mesclar ou kick: avise admins com 24h de antecedência  
• Raid interno: proibido – ao sair da tribo leva só itens pessoais

══════════════════════════════════════════════════════════════

## 6. COMPORTAMENTO
• Sem racismo, homofobia, sexismo, bullying, toxicidade ou NSFW  
• Sem propaganda sem permissão dos admins

══════════════════════════════════════════════════════════════

## 7. PUNIÇÕES (progressivas)
Leve (spam, caps) → mute 1h → mute 24h → ban 3 dias  
Média (bloqueio leve, grief) → ban 1 dia → 7 dias → 30 dias  
Grave (matar tame, pillar spam) → ban 7 dias → 30 dias → **PERM**  
Muito grave (PVP, hacks, dupe) → **BAN PERM** imediato  

Apelação → ticket com provas (vídeo/print) – resposta em até 48h

══════════════════════════════════════════════════════════════

## 8. WIPES & EVENTOS
• Wipe mensal: dia **1** de cada mês (aviso com 7 dias)  
• Eventos: toda **sexta às 20h BRT** (rates duplo, boss runs, giveaways)

══════════════════════════════════════════════════════════════

**Resumindo em 3 frases:**
1. Coopere, não atrapalhe ninguém.
2. Respeite os tames e bases dos outros.
3. Qualquer dúvida ou problema → abra ticket!

**Divirta-se no ARKLAND BRASIL!** 🦖✨

**🎮 Pronto para entrar no servidor?**
**► Discord:** https://discord.gg/7wPswZkb8z"""
            
            # Dividir em mensagens menores (limite Discord é 2000 caracteres)
            mensagens = []
            pedaco_atual = ""
            
            for linha in regras_completas.split('\n'):
                if len(pedaco_atual) + len(linha) + 1 > 1950:
                    if pedaco_atual:
                        mensagens.append(pedaco_atual)
                    pedaco_atual = linha
                else:
                    pedaco_atual += '\n' + linha if pedaco_atual else linha
            
            if pedaco_atual:
                mensagens.append(pedaco_atual)
            
            # Enviar mensagens na sala de regras
            for msg in mensagens:
                try:
                    await canal_regras.send(msg)
                except Exception as e:
                    print(f"❌ Erro ao enviar parte das regras: {e}")
            
            await ctx.send(f"✅ Regras enviadas com sucesso em {canal_regras.mention}!")
            
        except Exception as e:
            await ctx.send(f"❌ Erro ao enviar regras: {e}")
            print(f"❌ Erro ao enviar regras: {e}")
            import traceback
            traceback.print_exc()

async def setup(bot: commands.Bot):
    await bot.add_cog(ComandosCog(bot))

# ============================================================
# Atualizado em: 2025-11-23 22:41:53 (Horário de Brasília)
# ============================================================
