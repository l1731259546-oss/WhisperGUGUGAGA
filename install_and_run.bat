@echo off
chcp 65001 >nul
echo ========================================
echo WhisperGUGUGAGA - Automatic Installer
echo ========================================
echo.

echo Step 1: Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.13 or newer from:
    echo https://www.python.org/downloads/windows/
    echo.
    pause
    exit /b 1
)

python -c "import sys; version = sys.version_info; print(f'Found Python {version.major}.{version.minor}'); if not (version.major == 3 and version.minor >= 13): print('\nWARNING: Python 3.13 or newer is recommended.'); input('Press Enter to continue anyway...')" >nul 2>&1

echo.
echo Step 2: Creating config file if not exists...
if not exist config.yaml (
    copy config.example.yaml config.yaml
    echo Created config.yaml from example template
) else (
    echo config.yaml already exists, skipping
)
echo.

echo Step 3: Creating .env file if not exists...
if not exist .env (
    copy .env.example .env
    echo Created .env from example template
) else (
    echo .env already exists, skipping
)
echo.

echo Step 4: Installing dependencies...
echo This may take a few minutes...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

echo ========================================
echo Installation complete!
echo ========================================
echo.
echo NEXT STEPS:
echo 1. Edit config.yaml to customize your assistant
echo 2. Edit .env and add your OPENAI_API_KEY
echo 3. Press any key to start the application
echo.
pause

echo Starting WhisperGUGUGAGA...
python main.py

pause
