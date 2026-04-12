#!/usr/bin/env pwsh
# setup-ssh.ps1 - Configura SSH para acesso remoto

Write-Host "================================" -ForegroundColor Cyan
Write-Host "SSH SETUP - BOT OBOBONIC" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Verificar se é admin
$admin = [Security.Principal.WindowsIdentity]::GetCurrent().Groups -contains "S-1-5-32-544"
if (-not $admin) {
    Write-Host "❌ Precisa rodar como ADMINISTRADOR!" -ForegroundColor Red
    Write-Host "`nClique direito no PowerShell e escolha 'Executar como administrador'"
    exit 1
}

Write-Host "`n✅ Rodando como administrador`n"

# Passo 1: Verificar SSH Client
Write-Host "📋 Verificando SSH Client..." -ForegroundColor Yellow

$sshClient = Get-WindowsCapability -Online | Where-Object { $_.Name -like "*OpenSSH.Client*" }

if ($sshClient.State -eq "Installed") {
    Write-Host "✅ SSH Client já instalado"
} else {
    Write-Host "📥 Instalando SSH Client..."
    Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0 | Out-Null
    Write-Host "✅ SSH Client instalado"
}

# Passo 2: Gerar chave SSH
Write-Host "`n🔑 Gerando chave SSH..." -ForegroundColor Yellow

$sshDir = "$HOME\.ssh"
$keyPath = "$sshDir\id_ed25519"

if (-not (Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
}

if (Test-Path $keyPath) {
    Write-Host "⚠️  Chave já existe em: $keyPath"
} else {
    ssh-keygen -t ed25519 -f $keyPath -N "" | Out-Null
    Write-Host "✅ Chave criada"
}

# Passo 3: Mostrar chave pública
Write-Host "`n📤 Sua chave pública:" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════" -ForegroundColor Gray
Get-Content "$keyPath.pub"
Write-Host "════════════════════════════════════════════════" -ForegroundColor Gray

Write-Host "`n🎯 PRÓXIMO PASSO (Alguém na BAHIA):`n" -ForegroundColor Cyan
Write-Host "1. Na máquina BAHIA (179.185.19.88), abra PowerShell como ADMIN" -ForegroundColor White
Write-Host "2. Execute:" -ForegroundColor White
Write-Host "   New-Item -ItemType Directory -Path `$HOME\.ssh -Force | Out-Null`n" -ForegroundColor Green

Write-Host "3. Cole a chave em um arquivo. Use:" -ForegroundColor White
Write-Host "   Notepad `$HOME\.ssh\authorized_keys`n" -ForegroundColor Green

Write-Host "4. Cole TODA a chave acima, salve e feche." -ForegroundColor White
Write-Host "`n✅ Feito! Eu consigo acessar a Bahia depois.`n" -ForegroundColor Cyan
