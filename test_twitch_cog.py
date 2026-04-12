#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script de teste para diagnosticar TwitchMonitorCog"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("🧪 TESTE DE CARREGAMENTO DO TWITCH_MONITOR")
print("=" * 60)

try:
    print("\n1️⃣ Importando config...")
    import config
    print("   ✅ config importado")
    print(f"   TWITCH_CHANNEL_REQUEST: {config.TWITCH_CHANNEL_REQUEST}")
    print(f"   TWITCH_CHANNEL_APPROVAL: {config.TWITCH_CHANNEL_APPROVAL}")
    print(f"   TWITCH_CHANNEL_NOTIF: {config.TWITCH_CHANNEL_NOTIF}")
except Exception as e:
    print(f"   ❌ ERRO ao importar config: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n2️⃣ Importando discord...")
    import discord
    from discord.ext import commands
    print("   ✅ discord importado")
except Exception as e:
    print(f"   ❌ ERRO ao importar discord: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n3️⃣ Importando cogs.twitch_monitor...")
    from cogs.twitch_monitor import TwitchMonitorCog, setup
    print("   ✅ twitch_monitor importado com sucesso!")
except Exception as e:
    print(f"   ❌ ERRO ao importar twitch_monitor: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ TODOS OS TESTES PASSARAM!")
print("=" * 60)
