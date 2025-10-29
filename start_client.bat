@echo off
REM Batch script to start the LAN Communication Client

echo ========================================
echo  LAN Communication Client
echo ========================================
echo.

cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if dependencies are installed
echo Checking dependencies...
python -c "import cv2" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo Starting client...
echo.
echo A connection dialog will appear.
echo Enter the server IP address and your username.
echo ========================================
echo.

python src\client\client.py

pause
