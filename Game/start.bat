
@echo off
title Beyond the Arena
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv

    if errorlevel 1 (
        echo Failed to create virtual environment!
        pause
        exit /b 1
    )
)

echo Installing requirements...
venv\Scripts\python.exe -m pip install -r requirements.txt

if errorlevel 1 (
    echo Failed to install requirements!
    pause
    exit /b 1
)

echo.
echo Starting Beyond the Arena...
echo.

venv\Scripts\python.exe run.py

pause
