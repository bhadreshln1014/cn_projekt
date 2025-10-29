@echo off
REM Batch script to start the LAN Communication Server

echo ========================================
echo  LAN Communication Server
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
echo Starting server...
echo Server will listen on all network interfaces
echo TCP Control Port: 5000
echo UDP Video Port: 5001
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python src\server\server.py

pause
