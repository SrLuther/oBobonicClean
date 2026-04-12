#!/usr/bin/env pwsh
# Script para atualizar e reiniciar bot na máquina ArkServer (Bahia)

param(
    [string]$RemoteHost = "179.185.19.88",
    [string]$RemoteUser = "ArkServer",
    [string]$ProjectPath = "C:\Users\ArkServer\Documents\oBobonicClean"

Write-Host "================================"
Write-Host "🚀 DEPLOY REMOTO - ARKSERVER"
Write-Host "================================"

# Verificar conexão SSH
Write-Host "`n🔌 Testando conexão SSH..."
try {
    ssh -o ConnectTimeout=5 "${RemoteUser}@${RemoteHost}" "echo ok" | Out-Null
    Write-Host "✅ Conexão OK"
} catch {
    Write-Host "❌ Erro: Não consegue conectar. Verifique:"
    Write-Host "   - IP/hostname correto: $RemoteHost"
    Write-Host "   - SSH está habilitado lá"
    Write-Host "   - Credenciais corretas"
    exit 1
}

# Comando remoto para executar
$RemoteCommands = @"
cd $ProjectPath
Write-Host '📥 Puxando mudanças do git...'
git pull origin main

Write-Host '📦 Verificando dependências...'
.venv\Scripts\python check_and_install_dependencies.py

Write-Host '✅ Deploy concluído! Bot pronto para iniciar.'
"@

Write-Host "`n📤 Enviando comandos para $RemoteHost..."

# Executar no remoto
ssh "${RemoteUser}@${RemoteHost}" $RemoteCommands

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ DEPLOY CONCLUÍDO COM SUCESSO!"
    Write-Host "   A máquina Bahia está atualizada"
} else {
    Write-Host "`n❌ ERRO durante deploy"
    exit 1
}
