@echo off
echo Building Video Conference Server...
echo.

REM Install PyInstaller if not already installed
pip install pyinstaller

echo.
echo Building executable...
pyinstaller build_server.spec --clean

echo.
echo Build complete! 
echo Executable location: dist\VideoConferenceServer.exe
pause
