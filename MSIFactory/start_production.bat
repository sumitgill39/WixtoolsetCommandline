@echo off
title MSI Factory - Production Server
color 0A

echo ============================================================
echo MSI FACTORY - Production Server
echo ============================================================
echo.

echo [1] Killing any existing Python processes...
cls
taskkill /F /IM python.exe 2>nul
taskkill /F /IM py.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2] Starting MSI Factory production server...
cd /d "%~dp0"
start /B cmd /c py app_server.py

echo [3] Waiting for server to initialize...
timeout /t 5 /nobreak >nul

echo [4] Opening browser...
start http://localhost:5000

echo.
echo ============================================================
echo MSI Factory Production Server is running!
echo ============================================================
echo.
echo Server: Waitress WSGI (Production Ready)
echo URL: http://localhost:5000
echo.
echo Default accounts:
echo   Admin: admin
echo   User:  john.doe
echo.
echo To stop the server, run stop.bat
echo ============================================================
echo.

timeout /t 10