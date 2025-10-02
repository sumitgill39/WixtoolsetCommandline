@echo off
echo ============================================================
echo WINCORE - Stopping Application
echo ============================================================

:: Find and terminate Python processes running app.py
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /v ^| find "app.py"') do (
    echo Terminating process: %%a
    taskkill /PID %%a /F
)

echo.
echo [INFO] Application shutdown complete
echo ============================================================
pause