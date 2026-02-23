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
            
            regras_completas = """**🗺️ ArkLand Brasil • Primal Fear • Ragnarok**  
*Versão Atualizada - Obrigatório para todos em progressão avançada/endgame*

**⚠️ AVISO PRINCIPAL**  
Mesmo sendo **TOTALMENTE PvE**, suas criaturas, invocações e construções podem:  
• Matar outros jogadores  
• Destruir bases e progresso alheio  
• Causar lag no servidor  

**VOCÊ É 100% RESPONSÁVEL** por TUDO que causar.  
PvE ≠ Sem regras ou consequências.  
**Respeito mútuo é lei aqui.**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 1. ÁREAS PROTEGIDAS (Ragnarok)
**🚫 PROIBIDO** construir, colocar estruturas, teleporters ou deixar criaturas em:  
• Desert Arena  
• Lava Golem Arena  
• Ice Queen Arena  
• Dragon Arena  
• Wyvern Trench  
• **Qualquer spawn de Boss ou Artefato**  

**Distância mínima:** **100 fundações** (em linha reta).  

**Motivo:** Essencial para progressão de **TODOS**.  
**Penalidade:** Remoção imediata + advertência/ban.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 2. CRIATURAS DE ALTO RISCO  
*(Spirit, Celestial, Demonic, Chaos, Fey, Bosses, Alphas/Apexes e equivalentes de Primal Fear/Expansões)*  

Essas são **EXTREMAMENTE perigosas** mesmo em PvE.  

**✅ OBRIGATÓRIO:**  
• Sempre em **Passive**  
• **NUNCA** em Aggressive/Wandering  
• **NUNCA** soltas fora da base (sem supervisão)  
• **Cryopodadas** ao sair/logoff  
• Use **Dino Storage** para excesso  

**🚫 PROIBIDO:** Deixar sem supervisão ou soltas.  

**Penalidade:** Remoção das criaturas + ban em reincidência.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 3. INVOCAÇÃO DE BOSSES & EVENTOS  
**Permitido**, mas:  
• **Distância mínima de QUALQUER base:** **150 fundações**  
• **Somente** em áreas isoladas ou arenas próprias  
• **🚫 NUNCA** em áreas públicas/protegidas/rotas  

**Você responde por TODO dano** (mortes, destruição, lag).  
**Penalidade:** Remoção + reparação + ban.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 4. GRIEFING (PROIBIDO - MESMO PvE)  
**Exemplos:**  
• Atrair mobs/bosses para bases alheias  
• Invocações perto de outros  
• Trollar iniciantes com OP dinos  
• Bloquear recursos/spawns  
• Teleporters públicos em áreas protegidas  

**Penalidade:** **BAN PERMANENTE** (sem aviso).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 5. BASES, CONSTRUÇÃO & LAG  
**🚫 PROIBIDO:**  
• Spam de estruturas/fundações (incluindo S+)  
• Bases gigantes desnecessárias  
• Excesso de entidades (tochas, dinos renderizados)  

Admins removem **sem aviso** se causar lag.  
**Dica:** Otimize com S+ e Dino Storage.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 6. LIMITE DE CRIATURAS ENDGAME  
• Mantenha **mínimo necessário**  
• Cryopods/Dino Storage para o resto  
• Excesso = remoção automática  

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 7. PODER DOS ADMINS  
• Remover criaturas/bases/estruturas para proteger servidor  
• Reverter danos causados por irresponsabilidade  
• **Sem discussão** em casos claros.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 👑 REGRA FINAL  
**PvE = Progressão + Respeito.**  
Seu poder **NÃO** pode foder a experiência dos outros.  

**Reaja com ☠️ para confirmar!**  

*🗺️ ArkLand Brasil • Primal Fear + Expansões • Ragnarok PvE*  
*Mods: [Coleção Steam](https://steamcommunity.com/sharedfiles/filedetails/?id=3239651918)*"""
            
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
