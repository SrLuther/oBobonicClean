@echo off
REM 🌑 START BOT - HIDDEN MODE (Batch)
REM Inicia o bot sem exibir janela

setlocal enabledelayedexpansion

REM Verificar se .env existe
if not exist .env (
    echo ❌ Erro: Arquivo .env nao encontrado!
    exit /b 1
)

REM Ativar venv se existir
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat >nul 2>&1
)

REM Verificar e instalar dependências silenciosamente
python check_and_install_dependencies.py >nul 2>&1

REM Criar arquivo VBScript temporário para executar sem janela
set VBS_FILE=%temp%\start_bot_%random%.vbs

(
    echo Set objShell = CreateObject("WScript.Shell"^)
    echo objShell.Run "python bot.py", 0, False
) > "%VBS_FILE%"

REM Executar
cscript.exe "%VBS_FILE%" //nologo >nul 2>&1

REM Limpar
del "%VBS_FILE%" /Q 2>nul

echo Bot iniciado em modo oculto!
echo Dependencias verificadas automaticamente.
echo Use: tasklist /v para encontrar o processo Python
echo Para parar: taskkill /IM python.exe /F
exit /b 0
