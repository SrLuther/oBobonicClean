@echo off
chcp 65001 > nul
color 0A
cls

echo ================================================
echo  BOT OBOBONIC - ATUALIZAR BAHIA
echo ================================================

REM Máquina Bahia: 179.185.19.88
echo.
echo Este script DEVE ser executado na máquina da BAHIA
echo (179.185.19.88)
echo.
echo Se você está em Sergipe, use:
echo  1. git push (aqui em Sergipe)
echo  2. Execute este arquivo LÁ na Bahia
echo.

pause

cd /d C:\Users\ArkServer\Documents\oBobonicClean

echo.
echo 📥 Puxando atualizações...
git pull origin main

echo.
echo ✅ Feito! Atualizações sincronizadas.
echo.
pause
