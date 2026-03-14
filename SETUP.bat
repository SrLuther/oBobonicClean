@echo off
chcp 65001 >nul
REM ============================================================
REM SETUP INICIAL - Instala tudo na primeira vez
REM ============================================================

echo.
echo ✅ oBobonicClean - Setup Inicial
echo ============================================================
echo.

REM Define o diretório correto
cd /d "%~dp0"

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERRO: Python não está instalado ou não está no PATH!
    echo.
    echo 📥 Instale Python de: https://www.python.org/downloads/
    echo 💡 NÃO ESQUEÇA: Marque "Add Python to PATH" durante instalação
    pause
    exit /b 1
)

echo ✅ Python encontrado
echo.

REM Verifica se .venv existe
if not exist ".venv" (
    echo 📦 Criando ambiente virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ Erro ao criar .venv
        pause
        exit /b 1
    )
    echo ✅ Ambiente virtual criado
    echo.
)

REM Ativa o venv
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Erro ao ativar .venv
    pause
    exit /b 1
)

echo ✅ Ambiente virtual ativado
echo.

REM Instala dependências
echo 📥 Instalando dependências (isso pode levar alguns minutos)...
pip install --upgrade pip setuptools wheel >nul 2>&1
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Erro ao instalar dependências
    pause
    exit /b 1
)

echo.
echo ✅ Setup concluído com sucesso!
echo.
echo 🚀 Agora você pode usar:
echo    - Iniciar_Bot_Oculto.vbs (recomendado - sem janela)
echo    - Iniciar_Minimizado.bat (com logs visíveis)
echo.
pause
