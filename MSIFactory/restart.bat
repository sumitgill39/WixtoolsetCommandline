@echo off
title MSI Factory - Restart Application
color 0E

echo ============================================================
echo MSI FACTORY - Restarting Application
echo ============================================================
echo.

echo [1] Stopping existing Python processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM py.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2] Clearing temporary files...
del /Q *.pyc 2>nul
del /Q /S __pycache__ 2>nul

echo [3] Starting fresh instance...
cd /d "%~dp0"
start /B cmd /c py main.py

echo [4] Waiting for server to initialize...
timeout /t 5 /nobreak >nul

echo [5] Opening browser...
start http://localhost:5000

echo.
echo ============================================================
echo MSI Factory has been restarted!
echo ============================================================
echo.
echo Server URL: http://localhost:5000
echo.
echo To stop the server, run stop.bat
echo ============================================================
echo.

timeout /t 10

if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: Failed to restart MSI Factory
    echo ============================================================
    pause
)