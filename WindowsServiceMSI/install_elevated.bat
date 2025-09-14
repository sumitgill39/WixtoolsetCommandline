@echo off
echo =====================================================
echo Elevated Windows Service MSI Installation
echo =====================================================
echo.
echo This script will install the Windows Service MSI with
echo administrator privileges using UAC elevation.
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Already running as Administrator.
    goto :install
) else (
    echo Requesting Administrator privileges...
    echo.
    
    :: Request elevation using PowerShell
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\" elevated' -Verb RunAs"
    goto :end
)

:install
echo.
echo Choose Installation Type:
echo 1. LocalSystem Account (Full privileges)
echo 2. LocalService Account (Limited privileges)  
echo 3. NetworkService Account (Network access)
echo 4. Virtual Service Account (Managed account)
echo 5. Custom User Account
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto install_localsystem
if "%choice%"=="2" goto install_localservice
if "%choice%"=="3" goto install_networkservice
if "%choice%"=="4" goto install_virtual
if "%choice%"=="5" goto install_custom
echo Invalid choice!
goto :end

:install_localsystem
echo.
echo Installing with LocalSystem account...
msiexec /i WindowsService.msi SERVICE_ACCOUNT_TYPE=LocalSystem /l*v install_localsystem.log
goto :check_result

:install_localservice
echo.
echo Installing with LocalService account...
msiexec /i WindowsService.msi SERVICE_ACCOUNT_TYPE=LocalService /l*v install_localservice.log
goto :check_result

:install_networkservice
echo.
echo Installing with NetworkService account...
msiexec /i WindowsService.msi SERVICE_ACCOUNT_TYPE=NetworkService /l*v install_networkservice.log
goto :check_result

:install_virtual
echo.
echo Installing with Virtual Service Account...
msiexec /i WindowsService.msi SERVICE_ACCOUNT_TYPE=VirtualAccount /l*v install_virtual.log
goto :check_result

:install_custom
echo.
set /p username="Enter username (DOMAIN\User or .\User): "
set /p password="Enter password: "
echo.
echo Installing with custom account: %username%
msiexec /i WindowsService.msi SERVICE_ACCOUNT_TYPE=CustomUser SERVICE_CUSTOM_USER="%username%" SERVICE_PASSWORD="%password%" /l*v install_custom.log
goto :check_result

:check_result
echo.
if %ERRORLEVEL% == 0 (
    echo =====================================================
    echo INSTALLATION SUCCESSFUL!
    echo =====================================================
    echo.
    echo Service Status:
    sc query MyWindowsService
    echo.
    echo To manage the service:
    echo   Start:   net start MyWindowsService  
    echo   Stop:    net stop MyWindowsService
    echo   Status:  sc query MyWindowsService
    echo.
) else (
    echo =====================================================
    echo INSTALLATION FAILED!
    echo =====================================================  
    echo Error Code: %ERRORLEVEL%
    echo Check the log file for details.
)

:end
echo.
pause