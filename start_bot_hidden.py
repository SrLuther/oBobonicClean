#!/usr/bin/env python3
"""
🌑 START BOT - HIDDEN MODE
Inicia o bot sem exibir a janela do CMD
Use este script para rodar o bot em background
"""

import os
import sys
import subprocess
from pathlib import Path
import time

print("\n" + "=" * 70)
print("🌑 INICIANDO BOT - MODO OCULTO")
print("=" * 70 + "\n")

# Verificar ambiente
root_dir = Path(__file__).parent
venv_path = root_dir / ".venv"
bot_file = root_dir / "bot.py"
env_file = root_dir / ".env"
log_file = root_dir / ".bot_hidden.log"
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
print("🚀 Iniciando bot em MODO OCULTO...")
print(f"📝 Logs salvos em: {log_file}")
print("=" * 70 + "\n")

# Abrir arquivo de log
log = open(log_file, 'a', encoding='utf-8')
log.write(f"\n{'='*70}\n")
log.write(f"Bot iniciado em modo oculto - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
log.write(f"{'='*70}\n\n")
log.flush()

if sys.platform == "win32":
    # Windows: usar WIN_CREATE_NO_WINDOW para não mostrar janela
    if venv_path.exists():
        python_exe = str(venv_path / "Scripts" / "python.exe")
    else:
        python_exe = sys.executable
    
    cmd = [python_exe, str(bot_file)]
    
    try:
        # Criar processo sem janela
        import subprocess
        CREATE_NO_WINDOW = 0x08000000
        
        proc = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW,
            start_new_session=True  # Desacoplar do processo pai
        )
        
        print(f"✅ Bot iniciado com sucesso (PID: {proc.pid})")
        print(f"   O processo está rodando em background sem exibir janela")
        print(f"\n📝 Para parar o bot, use:")
        print(f"   taskkill /PID {proc.pid} /F")
        print(f"\n📊 Monitorar logs:")
        print(f"   tail -f {log_file}  (PowerShell: Get-Content {log_file} -Wait)")
        
        log.close()
        
    except Exception as e:
        log.write(f"❌ Erro ao iniciar bot: {e}\n")
        log.close()
        print(f"❌ Erro ao iniciar bot: {e}")
        sys.exit(1)

else:
    # Linux/Mac: usar & para rodar em background
    if venv_path.exists():
        python_exe = str(venv_path / "bin" / "python")
    else:
        python_exe = sys.executable
    
    cmd = f"{python_exe} {bot_file} >> {log_file} 2>&1 &"
    
    try:
        os.system(cmd)
        
        print(f"✅ Bot iniciado com sucesso")
        print(f"   O processo está rodando em background sem exibir janela")
        print(f"\n📝 Para parar o bot, use:")
        print(f"   killall python  (ou procure pelo PID)")
        print(f"\n📊 Monitorar logs:")
        print(f"   tail -f {log_file}")
        
        log.close()
        
    except Exception as e:
        log.write(f"❌ Erro ao iniciar bot: {e}\n")
        log.close()
        print(f"❌ Erro ao iniciar bot: {e}")
        sys.exit(1)
