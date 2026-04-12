#!/usr/bin/env python3
"""
🐛 START BOT - DEBUG MODE
Inicia o bot com a janela do CMD visível para debug e monitoramento
Use este script quando precisar acompanhar logs em tempo real
"""

import os
import sys
import subprocess
from pathlib import Path

print("\n" + "=" * 70)
print("🐛 INICIANDO BOT - MODO DEBUG")
print("=" * 70 + "\n")

# Verificar ambiente
root_dir = Path(__file__).parent
venv_path = root_dir / ".venv"
bot_file = root_dir / "bot.py"
env_file = root_dir / ".env"
dep_script = root_dir / "check_and_install_dependencies.py"

print("✓ Verificações iniciais:")

# Verificar .env
if env_file.exists():
    print(f"  ✅ Arquivo .env encontrado")
else:
    print(f"  ❌ Arquivo .env NÃO encontrado! Configure as variáveis de ambiente.")
    sys.exit(1)

# ============================================================================
# VERIFICAR E INSTALAR DEPENDÊNCIAS
# ============================================================================
print("\n" + "=" * 70)
print("📦 VERIFICANDO DEPENDÊNCIAS")
print("=" * 70)

if dep_script.exists():
    # Executar script de verificação de dependências
    python_exe = venv_path / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    dep_result = subprocess.run([str(python_exe), str(dep_script)])
    
    if dep_result.returncode != 0:
        print("\n❌ Erro ao verificar/instalar dependências!")
        sys.exit(1)
else:
    print(f"⚠️  Script de dependências não encontrado: {dep_script}")
    print("   Continuando mesmo assim...\\n")

# Verificar venv
if venv_path.exists():
    print(f"  ✅ Ambiente virtual encontrado")
else:
    print(f"  ⚠️  Ambiente virtual não encontrado. Tentando usar Python global...")

# Verificar bot.py
if bot_file.exists():
    print(f"  ✅ bot.py encontrado")
else:
    print(f"  ❌ bot.py NÃO encontrado!")
    sys.exit(1)

print("\n" + "=" * 70)
print("🚀 Iniciando bot em MODO DEBUG...")
print("=" * 70 + "\n")

# Criar comando para iniciar
if sys.platform == "win32":
    # Windows: usar a venv se existir
    if venv_path.exists():
        python_exe = str(venv_path / "Scripts" / "python.exe")
    else:
        python_exe = sys.executable
    
    # Executar Python normalmente (CMD visível)
    cmd = [python_exe, str(bot_file)]
    print(f"📌 Comando: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        print("\n\n⏹️  Bot interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro ao iniciar bot: {e}")
        sys.exit(1)
else:
    # Linux/Mac
    if venv_path.exists():
        python_exe = str(venv_path / "bin" / "python")
    else:
        python_exe = sys.executable
    
    cmd = [python_exe, str(bot_file)]
    print(f"📌 Comando: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        print("\n\n⏹️  Bot interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro ao iniciar bot: {e}")
        sys.exit(1)
