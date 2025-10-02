@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo WINCORE - JFrog Multi-threaded Polling System Startup
echo ============================================================

:: Check SQL Server connection
echo [INFO] Checking SQL Server connection...

py -c "import pyodbc; conn=pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=SUMEETGILL7E47\\MSSQLSERVER01;DATABASE=MSIFactory;Trusted_Connection=yes;')" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Could not connect to MSIFactory database
    echo Please ensure:
    echo 1. Connection settings are correct
    echo 2. MSIFactory database exists
    echo.
    pause
    exit /b 1
) else (
    echo [OK] Successfully connected to MSIFactory database
)

:: Check Python installation
cls
py --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

:: Check if virtual environment exists, create if not
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    py -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [INFO] Installing pip tools...
    .\venv\Scripts\python.exe -m pip install --upgrade pip wheel setuptools
    if errorlevel 1 (
        echo [ERROR] Failed to install pip tools
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call venv\Scripts\activate
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

:: Check and install requirements
echo [INFO] Checking dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

:: Check SQL Server connectivity
echo [INFO] Checking SQL Server connection...
py -c "from db_helper import DatabaseHelper; db = DatabaseHelper()" > nul 2>&1
if errorlevel 1 (
    echo [WARNING] SQL Server connection failed
    echo Please ensure:
    echo 1. SQL Server is running
    echo 2. Connection settings in config.py are correct
    echo 3. MSIFactory database exists
    echo.
    choice /C YN /M "Do you want to continue anyway"
    if errorlevel 2 exit /b 1
)

:: Start the application
echo.
echo [INFO] Starting WINCORE application...
echo [INFO] Press Ctrl+C to stop the application
echo ============================================================
echo.

py app.py

:: If application exits, deactivate virtual environment
call venv\Scripts\deactivate

echo.
if errorlevel 1 (
    echo [ERROR] Application terminated with errors
) else (
    echo [INFO] Application shutdown successfully
)

pause