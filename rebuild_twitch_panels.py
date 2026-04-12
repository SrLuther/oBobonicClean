#!/usr/bin/env python3
"""
🔧 REBUILD TWITCH PANELS
Reconstrói os painéis do sistema de lives Twitch
Use isso quando os painéis sumirem ou não aparecerem
"""

import asyncio
import discord
from discord.ext import commands
import os
import sys
from pathlib import Path

# Adicionar diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

import config
from cogs.twitch_monitor import TwitchMonitorCog

class PanelRebuilder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.twitch_cog = None

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"\n{'='*70}")
        print("🚀 INICIANDO RECONSTRUÇÃO DE PAINÉIS...")
        print(f"{'='*70}\n")
        
        # Aguarda um pouco para garantir que o bot está pronto
        await asyncio.sleep(2)
        
        try:
            # Busca o cog do Twitch Monitor
            self.twitch_cog = self.bot.get_cog("TwitchMonitorCog")
            
            if not self.twitch_cog:
                print("❌ Erro: TwitchMonitorCog não encontrado!")
                print("   Verifique se o cog está carregado no bot.py")
                await self.bot.close()
                return
            
            print("✅ TwitchMonitorCog encontrado!")
            print("\n📝 Reconstruindo painéis...\n")
            
            # Reconstrói os painéis
            print("  1️⃣  Criando painel de solicitação...")
            await self.twitch_cog._create_request_panel()
            print("     ✅ Painel de solicitação criado")
            
            print("\n  2️⃣  Atualizando painel de aprovação...")
            await self.twitch_cog._update_approval_panel()
            print("     ✅ Painel de aprovação atualizado")
            
            print(f"\n{'='*70}")
            print("✅ PAINÉIS RECONSTRUÍDOS COM SUCESSO!")
            print(f"{'='*70}\n")
            
            print("📊 Informações:")
            print(f"   • Canais monitorados: {len(self.twitch_cog.approved_channels)}")
            print(f"   • Solicitações pendentes: {len(self.twitch_cog.pending_requests)}")
            
            # Fecha o bot após reconstruir
            await asyncio.sleep(2)
            await self.bot.close()
            
        except Exception as e:
            print(f"\n❌ ERRO ao reconstruir painéis: {e}")
            import traceback
            traceback.print_exc()
            await self.bot.close()

async def main():
    # Criar bot com intents minimais
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True
    
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    async with bot:
        # Adiciona o cog de reconstrução
        await bot.add_cog(PanelRebuilder(bot))
        
        # Carrega o TwitchMonitorCog
        try:
            await bot.load_extension("cogs.twitch_monitor")
            print("✅ TwitchMonitorCog carregado")
        except Exception as e:
            print(f"❌ Erro ao carregar TwitchMonitorCog: {e}")
            return
        
        # Conecta ao Discord
        try:
            await bot.start(config.DISCORD_TOKEN)
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🔧 FERRAMENTA DE RECONSTRUÇÃO DE PAINÉIS TWITCH")
    print("="*70)
    
    # Verificar .env
    if not os.path.exists(".env"):
        print("\n❌ Arquivo .env não encontrado!")
        sys.exit(1)
    
    print("\n⏳ Conectando ao Discord...\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
