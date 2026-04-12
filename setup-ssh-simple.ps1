# setup-ssh-simple.ps1 - Gera chave SSH para acesso remoto

Write-Host "======================================"
Write-Host "SSH SETUP"
Write-Host "======================================"

# Verificar se é admin
$admin = [Security.Principal.WindowsIdentity]::GetCurrent().Groups -contains "S-1-5-32-544"
if (-not $admin) {
    Write-Host "ERRO: Precisa rodar como ADMINISTRADOR!" -ForegroundColor Red
    exit 1
}

Write-Host "OK: Rodando como administrador"

# Passo 1: SSH Client
Write-Host ""
Write-Host "Verificando SSH Client..." -ForegroundColor Yellow

$sshClient = Get-WindowsCapability -Online | Where-Object { $_.Name -like "*OpenSSH.Client*" }

if ($sshClient.State -eq "Installed") {
    Write-Host "OK: SSH Client ja instalado"
} else {
    Write-Host "Instalando SSH Client..."
    Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0 | Out-Null
    Write-Host "OK: SSH Client instalado"
}

# Passo 2: Gerar chave
Write-Host ""
Write-Host "Gerando chave SSH..." -ForegroundColor Yellow

$sshDir = "$HOME\.ssh"
$keyPath = "$sshDir\id_ed25519"

if (-not (Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
}

if (Test-Path $keyPath) {
    Write-Host "AVISO: Chave ja existe em: $keyPath"
} else {
    ssh-keygen -t ed25519 -f $keyPath -N "" | Out-Null
    Write-Host "OK: Chave criada"
}

# Passo 3: Mostrar chave
Write-Host ""
Write-Host "============ SUA CHAVE PUBLICA ============" -ForegroundColor Green
Get-Content "$keyPath.pub"
Write-Host "========== FIM DA CHAVE ==========" -ForegroundColor Green

Write-Host ""
Write-Host "PROXIMOS PASSOS:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Copie TODA a chave acima (de com e sem a linha amarela)"
Write-Host ""
Write-Host "2. Na BAHIA (179.185.19.88), execute como ADMIN:"
Write-Host "   New-Item -ItemType Directory -Path `$HOME\.ssh -Force | Out-Null"
Write-Host ""
Write-Host "3. Na BAHIA, abra Notepad:"
Write-Host "   Notepad C:\Users\ArkServer\.ssh\authorized_keys"
Write-Host ""
Write-Host "4. Cole a chave, salve e feche."
Write-Host ""
Write-Host "5. Na BAHIA, rodando como ADMIN:"
Write-Host "   icacls C:\Users\ArkServer\.ssh\authorized_keys /inheritance:r /grant:r `"SYSTEM:(F)`""
Write-Host ""
Write-Host "Pronto! Acesso remoto configurado."
