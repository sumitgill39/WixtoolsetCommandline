@echo off
title MSI Factory - Stop Application
color 0C

echo ============================================================
echo MSI FACTORY - Stopping Application
echo ============================================================
echo.

echo [1] Stopping all Python processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM py.exe 2>nul

echo.
echo [2] Application stopped successfully
echo ============================================================
echo.

timeout /t 3 /nobreak >nul