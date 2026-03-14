@echo off
REM ============================================================
REM Script para iniciar o bot minimizado na bandeja do Windows
REM ============================================================

REM Define o diretório correto
cd /d "%~dp0"

REM Ativa o ambiente virtual
call .venv\Scripts\activate.bat

REM Inicia o bot
if "%1"=="" (
    REM Se chamado diretamente, minimiza e executa
    start "" /min "" cmd /c python bot.py
    exit /b 0
) else (
    REM Se chamado com parâmetro, executa normalmente (para debug)
    python bot.py
)
