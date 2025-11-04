#!/bin/bash
echo "Building Video Conference Client..."
echo ""

# Install PyInstaller if not already installed
pip install pyinstaller

echo ""
echo "Building executable..."
python -m PyInstaller build_client.spec --clean

echo ""
echo "Build complete!"
echo "Executable location: dist/VideoConferenceClient"
