@echo off
echo =============================================
echo WiX v6 MSI Build Test for Web Application
echo =============================================
echo.

echo Checking WiX version...
wix --version
echo.

echo Step 1: Generating Files.wxs from WebFiles directory...
py generate_files.py WebFiles Files.wxs
echo.

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to generate Files.wxs
    pause
    exit /b %ERRORLEVEL%
)

echo Step 2: Building MSI package from Product.wxs and Files.wxs...
echo Command: wix build Product.wxs Files.wxs -ext WixToolset.Iis.wixext -o TestWebApp.msi -bindpath .
echo.

wix build Product.wxs Files.wxs -ext WixToolset.Iis.wixext -o TestWebApp.msi -bindpath .

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =============================================
    echo BUILD SUCCESS!
    echo =============================================
    echo MSI Package created: TestWebApp.msi
    echo.
    echo The MSI contains:
    echo - Web application files (index.html, app.js, web.config)
    echo - IIS configuration for Default Web Site
    echo - Application Pool: TestWebAppAppPool
    echo - Virtual Directory: /TestWebApp
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