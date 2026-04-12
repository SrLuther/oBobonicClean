@echo off
REM 📦 INSTALAR DEPENDÊNCIAS
REM Script para instalar/atualizar todas as dependências do bot

cls
color 0A
title 📦 Instalando Dependências - oBobonic Bot

echo.
echo ================================================================
echo  📦 INSTALADOR DE DEPENDÊNCIAS
echo ================================================================
echo.
echo  Este script irá instalar/atualizar todas as dependências
echo  necessárias para rodar o bot.
echo.
echo ================================================================
echo.

REM Verificar se .env existe
if not exist .env (
    echo ⚠️  Aviso: Arquivo .env não encontrado
    echo    Continuando mesmo assim...
    echo.
)

REM Verificar se venv existe e ativar
if exist .venv\Scripts\activate.bat (
    echo ✅ Ativando ambiente virtual...
    call .venv\Scripts\activate.bat
    echo.
) else (
    echo ⚠️  Ambiente virtual não encontrado em .venv
    echo    Usando Python do sistema...
    echo.
)

REM Fazer upgrade do pip primeiro
echo ================================================================
echo  🔄 ATUALIZANDO PIP
echo ================================================================
echo.
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ⚠️  Aviso: Erro ao atualizar pip, continuando mesmo assim...
    echo.
)

REM Instalar dependências-windows primeiro (se em Windows)
if exist requirements-windows.txt (
    echo.
    echo ================================================================
    echo  📥 INSTALANDO DEPENDÊNCIAS WINDOWS
    echo ================================================================
    echo.
    pip install -r requirements-windows.txt
    if errorlevel 1 (
        color 0C
        echo.
        echo ❌ ERRO ao instalar requirements-windows.txt
        echo.
        pause
        exit /b 1
    )
)

REM Instalar dependências gerais
echo.
echo ================================================================
echo  📥 INSTALANDO DEPENDÊNCIAS GERAIS
echo ================================================================
echo.
pip install -r requirements.txt
if errorlevel 1 (
    color 0C
    echo.
    echo ❌ ERRO ao instalar requirements.txt
    echo.
    pause
    exit /b 1
)

REM Sucesso
color 0B
echo.
echo ================================================================
echo  ✅ TODAS AS DEPENDÊNCIAS FORAM INSTALADAS COM SUCESSO!
echo ================================================================
echo.
echo  Próximas etapas:
echo  1. Execute: start_bot_debug.bat (para modo debug)
echo  2. Ou: start_bot_hidden.bat (para modo oculto)
echo.
echo ================================================================
echo.

pause
exit /b 0
