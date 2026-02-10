@echo off
chcp 65001 > nul
echo ============================================================
echo HIVE Launcher - Setup Script
echo ============================================================
echo.
echo WARNING: Educational Research Only
echo This software implements COORDINATED COLLUSION.
echo ILLEGAL in real poker. EXTREMELY UNETHICAL.
echo.
echo Press any key to continue setup...
pause > nul

echo.
echo ============================================================
echo Step 1: Checking Python installation...
echo ============================================================
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found!
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Step 2: Installing dependencies...
echo ============================================================
echo Installing from launcher/requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r launcher/requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to install dependencies!
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Step 3: Creating config directory...
echo ============================================================
if not exist "config" mkdir config
if not exist "config\roi" mkdir config\roi
if not exist "config\bot_settings" mkdir config\bot_settings
echo Config directories created.

echo.
echo ============================================================
echo Step 4: Running tests (optional)...
echo ============================================================
echo Do you want to run tests? (y/n)
set /p run_tests=
if /i "%run_tests%"=="y" (
    echo Running launcher tests...
    python -m pytest launcher/tests/test_roadmap6_final.py -v
)

echo.
echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Run: START_LAUNCHER.bat
echo   2. Read: QUICK_START_LAUNCHER.md
echo   3. Configure accounts and ROI
echo   4. Start bots
echo.
echo Remember: EDUCATIONAL USE ONLY!
echo.
pause
