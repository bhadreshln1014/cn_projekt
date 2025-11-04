@echo off
echo Building Video Conference Client...
echo.

REM Install PyInstaller if not already installed
pip install pyinstaller

echo.
echo Building executable...
pyinstaller build_client.spec --clean

echo.
echo Build complete! 
echo Executable location: dist\VideoConferenceClient.exe
pause
