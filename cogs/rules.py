"""
Cog para gerenciar as regras do servidor ArkLand Brasil
"""
import discord
from discord.ext import commands


class RulesCog(commands.Cog):
    """Cog responsável pelas regras do servidor"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="regras", aliases=["rules"])
    @commands.has_permissions(administrator=True)
    async def regras_command(self, ctx: commands.Context) -> None:
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
*Mods: [Coleção Steam](<https://steamcommunity.com/sharedfiles/filedetails/?id=3239651918>)*"""

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


async def setup(bot: commands.Bot) -> None:
    """Setup do cog"""
    await bot.add_cog(RulesCog(bot))
