@echo off
echo =====================================================
echo Standalone Website MSI Installation with Credentials
echo =====================================================
echo.
echo Choose Application Pool Identity Type:
echo.
echo 1. ApplicationPoolIdentity (Most Secure - Recommended)
echo 2. NetworkService (Built-in account with network access)
echo 3. LocalService (Built-in account, no network access)
echo 4. LocalSystem (Full privileges - NOT recommended)
echo 5. Custom User Account (Provide credentials)
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto AppPoolIdentity
if "%choice%"=="2" goto NetworkService
if "%choice%"=="3" goto LocalService
if "%choice%"=="4" goto LocalSystem
if "%choice%"=="5" goto CustomUser
goto InvalidChoice

:AppPoolIdentity
echo.
echo Installing with ApplicationPoolIdentity (most secure)...
echo This creates a virtual account: IIS AppPool\MyWebSiteAppPool
echo.
msiexec /i StandaloneWebSite.msi /l*v install_apppool.log
goto End

:NetworkService
echo.
echo Installing with NetworkService account...
echo This uses the built-in NETWORK SERVICE account
echo.
msiexec /i StandaloneWebSite.msi APPPOOL_IDENTITY="networkService" /l*v install_network.log
goto End

:LocalService
echo.
echo Installing with LocalService account...
echo This uses the built-in LOCAL SERVICE account (no network access)
echo.
msiexec /i StandaloneWebSite.msi APPPOOL_IDENTITY="localService" /l*v install_local.log
goto End

:LocalSystem
echo.
echo WARNING: LocalSystem has full system privileges!
echo Are you sure you want to use LocalSystem? (Y/N)
set /p confirm="Enter Y to continue: "
if not "%confirm%"=="Y" goto End
echo.
echo Installing with LocalSystem account...
msiexec /i StandaloneWebSite.msi APPPOOL_IDENTITY="localSystem" /l*v install_system.log
goto End

:CustomUser
echo.
echo Enter custom user credentials:
echo.
set /p domain="Domain (leave empty for local account): "
set /p username="Username: "
set /p password="Password: "

echo.
echo Installing with custom user account...
echo User: %domain%\%username%
echo.

if "%domain%"=="" (
    msiexec /i StandaloneWebSite.msi APPPOOL_USER="%username%" APPPOOL_PASSWORD="%password%" /l*v install_custom.log
) else (
    msiexec /i StandaloneWebSite.msi APPPOOL_USER="%username%" APPPOOL_PASSWORD="%password%" APPPOOL_DOMAIN="%domain%" /l*v install_custom.log
)
goto End

:InvalidChoice
echo Invalid choice! Please run the script again.
goto End

:End
echo.
echo =====================================================
echo Installation process initiated.
echo Check the log file for details.
echo.
echo IMPORTANT NOTES:
echo - ApplicationPoolIdentity is the most secure option
echo - Custom users need appropriate permissions on website folder
echo - Never use LocalSystem unless absolutely required
echo - Review IIS Manager to verify settings after installation
echo =====================================================
pause