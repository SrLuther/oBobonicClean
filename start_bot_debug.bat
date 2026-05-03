@echo off
REM 🐛 START BOT - DEBUG MODE (Batch)
REM Inicia o bot com janela visível para monitorar logs

cls
color 0A
title 🐛 OboBOT - DEBUG MODE

echo.
echo ================================================================
echo  🐛 INICIANDO BOT - MODO DEBUG
echo ================================================================
echo.
echo  Logs em tempo real estarao visiveis nesta janela
echo  Use Ctrl+C para parar o bot
echo.
echo ================================================================
echo.

REM Verificar se .env existe
if not exist .env (
    echo ❌ Erro: Arquivo .env nao encontrado!
    echo    Configure as variaveis de ambiente primeiro.
    pause
    exit /b 1
)

REM Verificar se venv existe e ativar
if exist .venv\Scripts\activate.bat (
    echo ✅ Ativando ambiente virtual...
    call .venv\Scripts\activate.bat
) else (
    echo ⚠️  Ambiente virtual nao encontrado, usando Python do sistema...
)

REM Iniciar bot
echo.
echo ================================================================
echo  [%date% %time%] Iniciando bot...
echo ================================================================
echo.

python bot.py

if errorlevel 1 (
    color 0C
    echo.
    echo ❌ Bot saiu com erro!
    pause
    exit /b 1
)

pause
