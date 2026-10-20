@echo off
setlocal
cd /d "%~dp0"
title Iniciar Azure DevOps Demandas

:: 1. Executa verificação de dependências
python check_dependencies.py
if errorlevel 1 (
    echo.
    echo Dependencias ausentes ou instalacao cancelada.
    pause
    exit /b
)

:: 2. Inicia o programa sem janela preta de terminal se pythonw estiver disponivel
start "" pythonw app.py
if errorlevel 1 (
    python app.py
)
