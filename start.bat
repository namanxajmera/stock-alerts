@echo off
REM Stock Alerts - One-Click Startup Script for Windows
REM This script sets up the environment and launches the web dashboard

setlocal enabledelayedexpansion

echo ==========================================
echo 🚀 Stock Alerts - One-Click Startup
echo ==========================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if Python is installed
echo [INFO] Checking Python version...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check Python version (basic check)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [SUCCESS] Python %PYTHON_VERSION% found

REM Create virtual environment if it doesn't exist
echo [INFO] Setting up virtual environment...
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    echo [SUCCESS] Virtual environment created
) else (
    echo [INFO] Virtual environment already exists
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate
echo [SUCCESS] Virtual environment activated

REM Install dependencies
echo [INFO] Installing dependencies...
if exist "requirements.txt" (
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    echo [SUCCESS] Dependencies installed
) else (
    echo [ERROR] requirements.txt not found
    pause
    exit /b 1
)

REM Check environment configuration
echo [INFO] Checking environment configuration...
if not exist ".env" (
    if exist ".env.example" (
        echo [WARNING] .env file not found. Creating from .env.example...
        copy ".env.example" ".env"
        echo [WARNING] Please edit .env file with your Telegram bot token and other settings
        echo [WARNING] You can continue running for web dashboard only, but Telegram bot won't work
    ) else (
        echo [WARNING] No .env file found. Some features may not work properly.
    )
) else (
    echo [SUCCESS] Environment configuration found
)

REM Create necessary directories
echo [INFO] Setting up directories...
if not exist "logs" mkdir logs
if not exist "db" mkdir db
if not exist "static\js" mkdir static\js
echo [SUCCESS] Directories created

echo.
echo ==========================================
echo ✅ Setup Complete - Starting Application
echo ==========================================
echo.

REM Start the application
echo [INFO] Starting Stock Alerts Dashboard...
echo [INFO] Setting up database and initializing application...

REM Get port from environment or use default
if not defined PORT set PORT=5001

echo [SUCCESS] 🚀 Starting Stock Alerts Dashboard on port %PORT%
echo [SUCCESS] 📊 Web Dashboard: http://localhost:%PORT%
echo [SUCCESS] 📱 Bot commands: /start, /add, /list, /remove, /help
echo.
echo [INFO] Press Ctrl+C to stop the application
echo [INFO] Logs are being written to logs/stock_alerts.log

REM Start the Flask application
python app.py

pause