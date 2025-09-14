@echo off
echo =============================================
echo WiX v6 MSI Build for Windows Service
echo =============================================
echo.

echo Checking WiX version...
wix --version
echo.

echo Building MSI package from Product.wxs and Files.wxs...
echo Command: wix build Product.wxs Files.wxs -ext WixToolset.Util.wixext -ext WixToolset.Firewall.wixext -o WindowsService.msi
echo.

wix build Product.wxs Files.wxs -ext WixToolset.Util.wixext -ext WixToolset.Firewall.wixext -o WindowsService.msi

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =============================================
    echo BUILD SUCCESS!
    echo =============================================
    echo MSI Package created: WindowsService.msi
    echo.
    echo The MSI contains:
    echo - Windows Service executable and configuration
    echo - Service installation with configurable account
    echo - Event log source registration
    echo - Firewall exception rules
    echo - Registry settings
    echo - Environment variables
    echo - Service recovery options
    echo.
    echo INSTALLATION OPTIONS:
    echo.
    echo Interactive Installation (with UI):
    echo   msiexec /i WindowsService.msi
    echo.
    echo Silent Installation Examples:
    echo   LocalSystem:      msiexec /i WindowsService.msi SERVICE_ACCOUNT_TYPE=LocalSystem /qn
    echo   LocalService:     msiexec /i WindowsService.msi SERVICE_ACCOUNT_TYPE=LocalService /qn
    echo   NetworkService:   msiexec /i WindowsService.msi SERVICE_ACCOUNT_TYPE=NetworkService /qn
    echo   Virtual Account:  msiexec /i WindowsService.msi SERVICE_ACCOUNT_TYPE=VirtualAccount /qn
    echo   Custom User:      msiexec /i WindowsService.msi SERVICE_ACCOUNT_TYPE=CustomUser SERVICE_CUSTOM_USER="DOMAIN\User" SERVICE_PASSWORD="password" /qn
    echo.
    dir *.msi
) else (
    echo.
    echo =============================================
    echo BUILD FAILED!
    echo =============================================
    echo Error code: %ERRORLEVEL%
    echo Check the error messages above for details.
)

pause