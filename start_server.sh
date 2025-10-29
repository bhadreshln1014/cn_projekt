#!/bin/bash
# Bash script to start the LAN Communication Server

echo "========================================"
echo " LAN Communication Server"
echo "========================================"
echo

cd "$(dirname "$0")"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check if dependencies are installed
echo "Checking dependencies..."
python3 -c "import cv2" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
fi

echo
echo "Starting server..."
echo "Server will listen on all network interfaces"
echo "TCP Control Port: 5000"
echo "UDP Video Port: 5001"
echo
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo

python3 src/server/server.py
