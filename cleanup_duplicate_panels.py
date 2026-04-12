#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para limpar painéis duplicados do RCON Monitor
Deixa apenas UM painel por servidor no canal de dashboards
"""

import asyncio
import discord
from discord.ext import commands
import json
import os
from pathlib import Path

import config
from utils.ark_monitor_state import ArkMonitorState

class PanelCleaner:
    def __init__(self):
        self.state = ArkMonitorState()
        self.servers = self._load_servers()
        self.intents = discord.Intents.default()
        self.bot = commands.Bot(command_prefix="!", intents=self.intents)
    
    def _load_servers(self):
        """Carrega servidores de config"""
        servers = {}
        for map_key, map_info in config.ARK_MAPS.items():
            server_name = map_info.get("name", map_key)
            servers[server_name] = map_info
        return servers
    
    async def cleanup(self):
        """Remove painéis duplicados e mantém apenas o mais recente"""
        async with self.bot:
            await self.bot.login(config.DISCORD_TOKEN)
            
            channel_id = config.RCON_DASHBOARDS_CHANNEL_ID
            channel = self.bot.get_channel(channel_id)
            
            if not channel or not isinstance(channel, discord.TextChannel):
                print(f"❌ Canal {channel_id} não encontrado!")
                return
            
            print(f"\n🔍 Analisando canal: {channel.name}")
            print(f"📌 Total de servidores: {len(self.servers)}")
            print(f"   • {', '.join(self.servers.keys())}")
            
            # Agrupa mensagens por servidor
            server_messages: dict = {server: [] for server in self.servers.keys()}
            
            print("\n📝 Varrendo mensagens antigas...")
            
            async for msg in channel.history(limit=500):
                if not msg.author == self.bot.user or not msg.embeds:
                    continue
                
                embed = msg.embeds[0]
                title = embed.title or ""
                
                # Extrai nome do servidor do título
                for server_name in self.servers.keys():
                    if server_name.lower() in title.lower():
                        server_messages[server_name].append({
                            "id": msg.id,
                            "title": title,
                            "created_at": msg.created_at
                        })
                        break
            
            # Mostrar resultado
            duplicates_found = 0
            for server_name, messages in server_messages.items():
                if len(messages) > 1:
                    print(f"\n⚠️  {server_name}: {len(messages)} painéis")
                    duplicates_found += len(messages) - 1
                    for i, msg in enumerate(messages):
                        marker = "✅ MANTER" if i == len(messages) - 1 else "❌ DELETAR"
                        print(f"   {marker} - ID: {msg['id']} | {msg['created_at'].strftime('%d/%m %H:%M')}")
                elif len(messages) == 1:
                    print(f"✅ {server_name}: 1 painel correto")
                else:
                    print(f"❌ {server_name}: NENHUM painel!")
            
            if duplicates_found == 0:
                print(f"\n✅ Nenhum duplicado encontrado!")
                return
            
            # Perguntar se quer deletar
            print(f"\n⚠️  Encontrados {duplicates_found} painéis duplicados")
            resposta = input("Deseja deletá-los? (s/n): ").strip().lower()
            
            if resposta != 's':
                print("❌ Limpeza cancelada")
                return
            
            # Deletar painéis antigos (mantém apenas o mais recente)
            deleted_count = 0
            for server_name, messages in server_messages.items():
                # Ordena por data (mais antigos primeiro)
                messages_sorted = sorted(messages, key=lambda x: x['created_at'])
                
                # Deleta todos menos o último
                for msg_data in messages_sorted[:-1]:
                    try:
                        msg = await channel.fetch_message(msg_data['id'])
                        await msg.delete()
                        print(f"   ✅ Deletado painel antigo de {server_name} (ID: {msg_data['id']})")
                        deleted_count += 1
                    except Exception as e:
                        print(f"   ❌ Erro ao deletar {msg_data['id']}: {e}")
            
            print(f"\n✅ Total deletados: {deleted_count}")
            
            # Atualizar state com IDs corretos
            print("\n🔄 Atualizando message IDs no state...")
            
            for server_name, messages in server_messages.items():
                if messages:
                    # Pega o painel mais recente
                    latest = max(messages, key=lambda x: x['created_at'])
                    self.state.set_dashboard_message_id(server_name, latest['id'])
                    print(f"   ✅ {server_name} → ID: {latest['id']}")
            
            print("\n✅ LIMPEZA CONCLUÍDA!")
            print("Reinicie o bot para atualizar os painéis!")

if __name__ == "__main__":
    print("=" * 70)
    print("🧹 LIMPADOR DE PAINÉIS DUPLICADOS - RCON MONITOR")
    print("=" * 70)
    
    cleaner = PanelCleaner()
    asyncio.run(cleaner.cleanup())
