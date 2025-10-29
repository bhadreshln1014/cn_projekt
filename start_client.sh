#!/bin/bash
# Bash script to start the LAN Communication Client

echo "========================================"
echo " LAN Communication Client"
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
echo "Starting client..."
echo
echo "A connection dialog will appear."
echo "Enter the server IP address and your username."
echo "========================================"
echo

python3 src/client/client.py
