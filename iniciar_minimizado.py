"""
Script para iniciar o bot minimizado (alternativa ao .bat)
Uso: python iniciar_minimizado.py
"""

import subprocess
import sys
import os

# Muda para o diretório do script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Ativa venv e inicia o bot
try:
    # Opção 1: Usar subprocess com CREATE_NO_WINDOW
    result = subprocess.run(
        [sys.executable, "bot.py"],
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    )
    sys.exit(result.returncode)
except Exception as e:
    print(f"❌ Erro ao iniciar bot: {e}")
    sys.exit(1)
