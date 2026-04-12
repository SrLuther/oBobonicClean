#!/usr/bin/env pwsh
# deploy_sync.ps1 - Sincroniza e reinicia bot na Bahia

param(
    [string]$RemoteHost = "179.185.19.88",
    [string]$User = "ArkServer",
    [string]$Project = "C:\Users\ArkServer\Documents\oBobonicClean"
)

Write-Host "🔄 Sincronizando bot em $RemoteHost..." -ForegroundColor Cyan

ssh "${User}@${RemoteHost}" @"
    cd '$Project'
    git pull origin main
    Write-Host '✅ Atualizado!' -ForegroundColor Green
"@
