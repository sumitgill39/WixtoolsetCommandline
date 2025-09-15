@echo off
title MSI Factory - Development Server
color 0E

echo ============================================================
echo MSI FACTORY - Development Server
echo ============================================================
echo.

echo [1] Killing any existing Python processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM py.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2] Starting MSI Factory development server...
cd /d "%~dp0"
set WERKZEUG_RUN_MAIN=true
start /B cmd /c py main.py 2^>nul

echo [3] Waiting for server to initialize...
timeout /t 5 /nobreak >nul

echo [4] Opening browser...
start http://localhost:5000

echo.
echo ============================================================
echo MSI Factory Development Server is running!
echo ============================================================
echo.
echo Mode: Development (Flask)
echo URL: http://localhost:5000
echo.
echo Default accounts:
echo   Admin: admin
echo   User:  john.doe
echo.
echo Note: For production, use start_production.bat
echo To stop the server, run stop.bat
echo ============================================================
echo.

timeout /t 10