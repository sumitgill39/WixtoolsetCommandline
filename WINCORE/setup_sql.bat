@echo off
echo ============================================================
echo WINCORE - Database Connection Check
echo ============================================================

:: Check database connection
py -c "import pyodbc; conn=pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=SUMEETGILL7E47\\MSSQLSERVER01;DATABASE=MSIFactory;Trusted_Connection=yes;'); print('Database connection successful!')" >nul
if errorlevel 1 (
    echo [ERROR] Could not connect to MSIFactory database
    exit /b 1
)

echo [OK] Database connection verified
exit /b 0
sc query "SQLBrowser" > nul
if not errorlevel 1 (
    sc query "SQLBrowser" | find "STATE" | find "RUNNING" > nul
    if errorlevel 1 (
        echo [WARNING] SQL Server Browser is not running
        echo Starting SQL Server Browser...
        net start SQLBrowser
        if errorlevel 1 (
            echo [WARNING] Failed to start SQL Server Browser
        ) else (
            echo [OK] SQL Server Browser started
        )
    ) else (
        echo [OK] SQL Server Browser is running
    )
)

:: Run the Python SQL setup script
call run_sql_setup.bat
if errorlevel 1 (
    echo [ERROR] Failed to setup SQL database
    exit /b 1
)

echo [OK] SQL Server setup completed successfully
exit /b 0

:: Configure TCP/IP using PowerShell
echo [INFO] Configuring SQL Server network settings...
powershell -Command ^
    "$path = 'HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server\MSSQL16.MSSQLSERVER01\MSSQLServer\SuperSocketNetLib\Tcp'; ^
    if (Test-Path $path) { ^
        Set-ItemProperty -Path $path -Name 'Enabled' -Value 1; ^
        Set-ItemProperty -Path $path -Name 'ListenOnAllIPs' -Value 1; ^
        Write-Host '[OK] TCP/IP enabled for SQL Server'; ^
    } else { ^
        Write-Host '[WARNING] SQL Server registry path not found'; ^
    }"

:: Restart SQL Server to apply changes
echo [INFO] Restarting SQL Server to apply changes...
net stop MSSQLSERVER
net start MSSQLSERVER

echo.
echo [INFO] Testing SQL connection...
sqlcmd -S "SUMEETGILL7E47\MSSQLSERVER01" -Q "SELECT @@VERSION" -E
if errorlevel 1 (
    echo [ERROR] SQL connection test failed
    echo Please check:
    echo 1. SQL Server instance name is correct ^(SUMEETGILL7E47\MSSQLSERVER01^)
    echo 2. Windows Authentication is enabled
    echo 3. Firewall allows SQL Server port ^(default: 1433^)
    echo.
    echo Would you like to:
    echo [1] Try connecting with SQL Authentication
    echo [2] Continue anyway
    echo [3] Exit
    choice /C 123 /N /M "Choose an option (1-3): "
    
    if errorlevel 3 exit /b 1
    if errorlevel 2 goto :continue
    if errorlevel 1 (
        set /p "sqluser=Enter SQL username: "
        set /p "sqlpass=Enter SQL password: "
        sqlcmd -S "SUMEETGILL7E47\MSSQLSERVER01" -U "!sqluser!" -P "!sqlpass!" -Q "SELECT @@VERSION"
        if errorlevel 1 (
            echo [ERROR] SQL Authentication failed
            pause
            exit /b 1
        )
    )
) else (
    echo [OK] SQL connection test successful
)

:continue
echo.
echo ============================================================
echo SQL Server Setup Complete
echo Instance: SUMEETGILL7E47\MSSQLSERVER01
echo Authentication: Windows Authentication
echo ============================================================
echo.
pause