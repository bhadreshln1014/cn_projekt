#!/bin/bash
echo "Building Video Conference Server..."
echo ""

# Install PyInstaller if not already installed
pip install pyinstaller

echo ""
echo "Building executable..."
python -m PyInstaller build_server.spec --clean

echo ""
echo "Build complete!"
echo "Executable location: dist/VideoConferenceServer"
