@echo off
REM Quick start script for local development server
REM Windows batch file version
REM Usage: dev-server.bat

setlocal enabledelayedexpansion

echo ==================================================
echo Automation Dashboard - Development Server
echo ==================================================
echo.
echo Starting local server on localhost:6060...
echo.

REM Check if Python is available
python3 --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python 3 is not installed!
    echo Please install Python 3 from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] %PYTHON_VERSION% found
echo [OK] Serving files from: %cd%
echo.
echo Dashboard available at:
echo   -> http://localhost:6060
echo   -> http://localhost:6060/index.html
echo.
echo Press CTRL+C to stop server
echo ==================================================
echo.

REM Run the server
python3 server.py

if errorlevel 1 (
    echo.
    echo [ERROR] Server failed to start!
    pause
    exit /b 1
)

pause
