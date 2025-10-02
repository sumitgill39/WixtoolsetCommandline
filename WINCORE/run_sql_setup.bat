@echo off
echo Running Python SQL setup script...
python setup_sql.py
if %errorlevel% neq 0 (
    echo Failed to run SQL setup script.
    exit /b 1
)
echo SQL Server setup completed successfully.