@echo off
title MSI Factory - Enterprise MSI Generation System
color 0A

echo ============================================================
echo MSI FACTORY - Starting Application
echo ============================================================
echo.

echo [1] Killing any existing Python processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM py.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2] Starting MSI Factory server in background...
cd /d "%~dp0"
start /B cmd /c py main.py

echo [3] Waiting for server to initialize...
timeout /t 5 /nobreak >nul

echo [4] Opening browser...
start http://localhost:5000

echo.
echo ============================================================
echo MSI Factory is running!
echo ============================================================
echo.
echo Server URL: http://localhost:5000
echo.
echo Default accounts:
echo   Admin: admin
echo   User:  john.doe
echo.
echo To stop the server, run stop.bat or press Ctrl+C
echo ============================================================
echo.

timeout /t 10