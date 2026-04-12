#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de verificação e instalação automática de dependências
Executado antes do bot inicializar para garantir que tudo está pronto
"""

import subprocess
import sys
import os
from pathlib import Path

def get_venv_python():
    """Retorna o caminho do Python no .venv"""
    if sys.platform == "win32":
        return os.path.join(".venv", "Scripts", "python.exe")
    else:
        return os.path.join(".venv", "bin", "python")

def get_pip_command():
    """Retorna o comando pip apropriado"""
    if sys.platform == "win32":
        return [os.path.join(".venv", "Scripts", "pip.exe")]
    else:
        return [os.path.join(".venv", "bin", "pip")]

def parse_requirements(requirements_file="requirements.txt"):
    """Parse requirements.txt e retorna lista de packages"""
    packages = []
    if not os.path.exists(requirements_file):
        print(f"❌ Arquivo {requirements_file} não encontrado!")
        return packages
    
    with open(requirements_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Pula comentários e linhas vazias
            if not line or line.startswith('#'):
                continue
            # Remove comentários inline
            if '#' in line:
                line = line.split('#')[0].strip()
            packages.append(line)
    
    return packages

def is_package_installed(package_name):
    """Verifica se um package está instalado (com mapeamento correto de módulos)"""
    # Mapeamento de packages para nomes de módulos (pois muitos diferem)
    module_map = {
        'beautifulsoup4': 'bs4',
        'pyyaml': 'yaml',
        'pillow': 'PIL',
        'pycryptodome': 'Crypto',
        'python-dotenv': 'dotenv',
        'pynacl': 'nacl',
        'google-genai': 'google.generativeai',
        'yt-dlp': 'yt_dlp',
    }
    
    # Remove versão (==, >=, ~, etc)
    base_name = package_name.lower().replace('-', '_').split('==')[0].split('>=')[0].split('<=')[0].split('~')[0].strip()
    
    # Tenta usar o mapa, se não achar usa o nome direto
    module_name = module_map.get(base_name, base_name)
    
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False

def install_requirements():
    """Instala todas as dependências do requirements.txt"""
    print("\n" + "=" * 70)
    print("🔍 VERIFICANDO DEPENDÊNCIAS")
    print("=" * 70)
    
    requirements_files = ["requirements.txt"]
    if sys.platform == "win32":
        requirements_files.insert(0, "requirements-windows.txt")
    
    all_packages = []
    for req_file in requirements_files:
        if os.path.exists(req_file):
            packages = parse_requirements(req_file)
            all_packages.extend(packages)
            print(f"\n📄 Arquivo: {req_file}")
            print(f"   Packages: {len(packages)}")
    
    if not all_packages:
        print("❌ Nenhum arquivo de requirements encontrado!")
        return False
    
    # Remove duplicatas
    all_packages = list(set(all_packages))
    
    print(f"\n📦 Total de packages a verificar: {len(all_packages)}")
    
    missing = []
    installed = []
    
    for package in sorted(all_packages):
        # Extrai nome base do package (sem versão)
        base_name = package.split('==')[0].split('>=')[0].split('<=')[0].split('~')[0].strip()
        
        if is_package_installed(base_name):
            installed.append(base_name)
            print(f"   ✅ {base_name}")
        else:
            missing.append(package)
            print(f"   ❌ {base_name} (FALTANDO)")
    
    print(f"\n📊 Resumo:")
    print(f"   ✅ Instalados: {len(installed)}")
    print(f"   ❌ Faltando: {len(missing)}")
    
    if missing:
        print(f"\n⬇️  INSTALANDO {len(missing)} PACKAGE(S)...")
        print("=" * 70)
        
        pip_cmd = get_pip_command()
        failed_packages = []
        success_count = 0
        
        for package in missing:
            try:
                print(f"\n   ⏳ Instalando {package}...")
                result = subprocess.run(
                    pip_cmd + ["install", "--no-cache-dir", package],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    print(f"   ✅ {package} instalado com sucesso!")
                    success_count += 1
                else:
                    print(f"   ❌ Erro ao instalar {package}")
                    if result.stderr:
                        # Mostrar apenas primeira linha do erro para não poluir
                        first_error = result.stderr.split('\n')[0]
                        print(f"      {first_error[:100]}")
                    failed_packages.append(package)
                    # CONTINUA tentando instalar os outros!
                    
            except subprocess.TimeoutExpired:
                print(f"   ❌ Timeout ao instalar {package} (limite 60s)")
                failed_packages.append(package)
            except Exception as e:
                print(f"   ❌ Erro ao instalar {package}: {e}")
                failed_packages.append(package)
        
        print("\n" + "=" * 70)
        print(f"✅ Instalados com sucesso: {success_count}/{len(missing)}")
        
        if failed_packages:
            print(f"⚠️  Falharam: {len(failed_packages)}")
            for pkg in failed_packages:
                print(f"   • {pkg}")
            print("\n🔴 AVISO: Alguns packages falharam. Tentando iniciar bot mesmo assim...")
            print("   Se houver erro, revise as mensagens acima.")
            print("=" * 70)
            return True  # Retorna True mesmo com falhas para tentar rodar o bot
        else:
            print("✅ TODAS AS DEPENDÊNCIAS FORAM INSTALADAS!")
            print("=" * 70)
            return True
    else:
        print("\n" + "=" * 70)
        print("✅ TODAS AS DEPENDÊNCIAS JÁ ESTÃO INSTALADAS!")
        print("=" * 70)
        return True

if __name__ == "__main__":
    success = install_requirements()
    sys.exit(0 if success else 1)
