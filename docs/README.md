# LAN-Based Multi-User Communication Application

**Computer Networks Project**  
**Developed by:** Bhadresh L and Santhana Srinivasan R  
**Date:** November 2025

---

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Features](#features)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Running the Application](#running-the-application)
7. [Usage Guide](#usage-guide)
8. [Technical Documentation](#technical-documentation)
9. [Troubleshooting](#troubleshooting)
10. [Project Structure](#project-structure)

---

## Overview

This is a comprehensive LAN-based multi-user communication application that provides enterprise-grade collaboration features without requiring internet connectivity. The system operates entirely within a Local Area Network (LAN), making it ideal for:

- Organizations with restricted internet access
- Secure environments requiring isolated communication
- Locations with unreliable internet connectivity
- Educational institutions conducting remote labs

### Key Features
- **Multi-User Video Conferencing**: Real-time video streaming with up to 10 participants
- **Multi-User Audio Conferencing**: Low-latency audio with server-side mixing
- **Screen/Slide Sharing**: Presenter-controlled screen broadcasting
- **Group Text Chat**: Instant messaging with chat history and private messages
- **File Sharing**: Peer-to-peer file transfer with progress tracking

---

## System Architecture

The application follows a **client-server architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                      Central Server                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ • User Session Management                            │   │
│  │ • Video Stream Broadcasting (UDP)                    │   │
│  │ • Audio Mixing & Broadcasting (UDP)                  │   │
│  │ • Screen Share Relay (TCP + UDP)                     │   │
│  │ • Chat Message Broadcasting (TCP)                    │   │
│  │ • File Transfer Coordination (TCP)                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │ Client 1│       │ Client 2│       │ Client N│
   │         │       │         │       │ (Max 10)│
   └─────────┘       └─────────┘       └─────────┘
```

### Network Protocol Usage

| Feature | Protocol | Port | Reason |
|---------|----------|------|--------|
| Control Messages & Chat | TCP | 5000 | Reliability required for session management |
| Video Streaming | UDP | 5001 | Low latency prioritized over reliability |
| Audio Streaming | UDP | 5002 | Real-time delivery critical |
| Screen Share Control | TCP | 5003 | Ensures command integrity |
| Screen Share Data | UDP | 5004 | Balances quality and performance |
| File Transfer | TCP | 5005 | Guarantees complete file delivery |

---

## Prerequisites

### Software Requirements
- **Python**: Version 3.8 or higher
- **Operating System**: Windows 10/11, Linux, or macOS
- **Webcam**: For video conferencing
- **Microphone & Speakers**: For audio conferencing
- **Network**: All devices must be on the same LAN

### Hardware Recommendations
- **Server Machine**:
  - CPU: Quad-core processor or better
  - RAM: 4GB minimum (8GB recommended for 10+ users)
  - Network: Gigabit Ethernet (recommended)
  
- **Client Machine**:
  - CPU: Dual-core processor or better
  - RAM: 2GB minimum
  - Network: 100 Mbps Ethernet or WiFi

---

## Installation

### Step 1: Clone/Download the Project
```bash
# If using Git
git clone <repository-url>
cd projekt

# Or download and extract the ZIP file
```

### Step 2: Install Python Dependencies
```bash
# Navigate to the project directory
cd c:\Users\bhadr\OneDrive\Desktop\IIITDM\SEM5\CN\projekt

# Install required packages
pip install -r requirements.txt
```

### Dependencies Installed:
- `opencv-python==4.8.1.78` - Video capture and processing
- `numpy==1.24.3` - Numerical operations for audio/video
- `Pillow==10.0.0` - Image processing
- `pyaudio==0.2.14` - Audio capture and playback
- `mss==9.0.1` - Screen capture for screen sharing
- `PyQt6==6.6.0` - Modern GUI framework
- `qt-material==2.14` - Material Design styling
- `qtawesome==1.3.1` - Icon library

### Step 3: Build Executables (Optional)

#### For Windows:
```bash
# Build Server
build_server.bat

# Build Client
build_client.bat
```

#### For Linux/macOS:
```bash
# Build Server
chmod +x build_server.sh
./build_server.sh

# Build Client
chmod +x build_client.sh
./build_client.sh
```

Built executables will be in the `dist/` folder.

---

## Running the Application

### Method 1: Using Python Scripts

#### Start the Server:
```bash
# Windows
start_server.bat

# Linux/macOS
chmod +x start_server.sh
./start_server.sh

# Or directly with Python
python -m src.server.server
```

#### Start the Client(s):
```bash
# Windows
start_client.bat

# Linux/macOS
chmod +x start_client.sh
./start_client.sh

# Or directly with Python
python -m src.client.client
```

### Method 2: Using Executables
```bash
# Run server executable
dist\VideoConferenceServer.exe  # Windows
./dist/VideoConferenceServer    # Linux/macOS

# Run client executable
dist\VideoConferenceClient.exe  # Windows
./dist/VideoConferenceClient    # Linux/macOS
```

---

## Usage Guide

### Server Setup

1. **Launch the Server Application**
   - The server will automatically start listening on all network interfaces (0.0.0.0)
   - Note the IP address displayed (e.g., 192.168.1.100)
   - Server console will display:
     ```
     [HH:MM:SS] Server started
     [HH:MM:SS] TCP Control Port: 5000
     [HH:MM:SS] UDP Video Port: 5001
     [HH:MM:SS] UDP Audio Port: 5002
     [HH:MM:SS] TCP Screen Sharing Control Port: 5003
     [HH:MM:SS] UDP Screen Sharing Data Port: 5004
     [HH:MM:SS] TCP File Transfer Port: 5005
     [HH:MM:SS] Waiting for connections...
     ```

2. **Monitor Connected Users**
   - The server logs all user connections/disconnections
   - View real-time activity in the console

### Client Setup

1. **Launch the Client Application**
   - A modern GUI window will open

2. **Connect to Server**
   - Enter the **server IP address** (e.g., 192.168.1.100)
   - Enter your **username**
   - Select your **microphone** and **speaker** from dropdowns
   - Click **Connect**

3. **Configure Audio/Video**
   - Toggle **Microphone** on/off
   - Toggle **Speaker** on/off
   - Toggle **Camera** on/off
   - Toggle **Show Self Video** to see your own feed

### Video Conferencing

- **Automatic Layout**: The system automatically arranges video feeds in a grid
- **Layout Options**: Switch between 1x1, 2x2, 3x3, or 4x4 grid layouts
- **Video Quality**: 640x480 resolution at 30 FPS with JPEG compression (quality: 60)
- **Bandwidth**: Approximately 200-500 KB/s per video stream

### Audio Conferencing

- **Real-time Communication**: ~23ms latency per audio chunk
- **Server-side Mixing**: All audio streams mixed on server before broadcasting
- **Audio Quality**: 44.1kHz sample rate, mono channel, 16-bit depth
- **Controls**: Individual microphone and speaker mute/unmute

### Screen Sharing

1. **Start Presenting**:
   - Click the **"Start Screen Share"** button
   - Only one presenter allowed at a time
   - Screen captured at 960x540 resolution, 10 FPS

2. **View Shared Screen**:
   - Shared screen appears in a dedicated panel
   - Automatically shown when presenter starts sharing
   - Full-screen mode available

3. **Stop Presenting**:
   - Click **"Stop Screen Share"**
   - Others can immediately take over as presenter

### Group Chat

1. **Send Messages**:
   - Type in the message input field at the bottom
   - Press Enter or click Send
   - Messages appear with timestamp and username

2. **Private Messages**:
   - Click on a user in the People panel
   - Select "Send Private Message"
   - Type message in the chat (marked as private)

3. **Chat Features**:
   - Full chat history maintained
   - Visual notifications for new messages
   - Message timestamps in HH:MM:SS format

### File Sharing

1. **Upload File**:
   - Click the **Files** icon to open file panel
   - Click **"Upload File"** button
   - Select file from your computer (max 100MB)
   - Upload progress shown with progress bar

2. **Download File**:
   - View available files in the Files panel
   - Click **"Download"** button next to the file
   - Select save location
   - Download progress displayed

3. **File Information**:
   - Filename and size displayed
   - Uploader name and timestamp shown
   - 8KB chunks for efficient transfer

---

## Technical Documentation

For detailed technical information about each module, refer to:

- **[Video Module Documentation](VIDEO_MODULE.md)** - Video capture, compression, transmission, and rendering
- **[Audio Module Documentation](AUDIO_MODULE.md)** - Audio capture, mixing, and playback implementation
- **[Screen Share Documentation](SCREENSHARE_MODULE.md)** - Screen capture and presentation system
- **[Chat Module Documentation](CHAT_MODULE.md)** - Messaging protocol and implementation
- **[File Sharing Documentation](FILE_MODULE.md)** - File transfer protocol and handling

---

## Troubleshooting

### Connection Issues

**Problem**: Client cannot connect to server  
**Solutions**:
- Verify server is running and displays "Waiting for connections..."
- Confirm both devices are on the same LAN
- Check firewall settings - allow Python or the executable through firewall
- Verify server IP address is correct
- Ensure ports 5000-5005 are not blocked

**Problem**: "Connection refused" error  
**Solutions**:
- Restart the server application
- Check if another application is using ports 5000-5005
- Disable VPN or proxy settings

### Audio Issues

**Problem**: No audio heard  
**Solutions**:
- Check speaker toggle is ON
- Verify correct audio output device selected
- Ensure other users have microphone ON
- Check system audio levels

**Problem**: Audio choppy or distorted  
**Solutions**:
- Check network bandwidth
- Reduce number of simultaneous video streams
- Verify network latency is under 100ms

### Video Issues

**Problem**: No video showing  
**Solutions**:
- Ensure webcam is not in use by another application
- Toggle camera off and on again
- Check webcam permissions
- Verify OpenCV can access the camera

**Problem**: Video lag or freezing  
**Solutions**:
- Reduce video quality in config.py
- Switch to wired connection instead of WiFi
- Check CPU usage on server

### Screen Share Issues

**Problem**: Cannot start screen share  
**Solutions**:
- Ensure no other user is presenting
- Check screen capture permissions (macOS/Linux)
- Restart the client application

**Problem**: Screen share choppy  
**Solutions**:
- This is expected behavior (10 FPS by design)
- Close unnecessary applications to free bandwidth

### File Transfer Issues

**Problem**: File upload fails  
**Solutions**:
- Ensure file size is under 100MB limit
- Check available disk space on server
- Verify TCP port 5005 is accessible

---

## Project Structure

```
projekt/
│
├── src/
│   ├── client/
│   │   ├── __init__.py
│   │   └── client.py              # Client application (4172 lines)
│   │
│   ├── server/
│   │   ├── __init__.py
│   │   └── server.py              # Server application (934 lines)
│   │
│   └── common/
│       ├── __init__.py
│       └── config.py              # Shared configuration
│
├── docs/
│   ├── README.md                  # This file
│   ├── VIDEO_MODULE.md            # Video module documentation
│   ├── AUDIO_MODULE.md            # Audio module documentation
│   ├── SCREENSHARE_MODULE.md      # Screen share documentation
│   ├── CHAT_MODULE.md             # Chat module documentation
│   └── FILE_MODULE.md             # File sharing documentation
│
├── build/                         # Build artifacts
├── dist/                          # Compiled executables
│
├── requirements.txt               # Python dependencies
├── build_client.bat/sh            # Client build scripts
├── build_server.bat/sh            # Server build scripts
├── start_client.bat/sh            # Client launch scripts
└── start_server.bat/sh            # Server launch scripts
```

---

## Configuration

All configuration parameters are centralized in `src/common/config.py`:

### Network Settings
```python
SERVER_HOST = '0.0.0.0'           # Listen on all interfaces
SERVER_TCP_PORT = 5000            # Control messages
SERVER_UDP_PORT = 5001            # Video streaming
SERVER_AUDIO_PORT = 5002          # Audio streaming
SERVER_SCREEN_PORT = 5003         # Screen share control
SERVER_SCREEN_UDP_PORT = 5004     # Screen share data
SERVER_FILE_PORT = 5005           # File transfers
```

### Video Settings
```python
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
VIDEO_FPS = 30
VIDEO_QUALITY = 60                # JPEG quality (0-100)
```

### Audio Settings
```python
AUDIO_RATE = 44100                # 44.1kHz sample rate
AUDIO_CHUNK = 1024                # Samples per chunk
AUDIO_CHANNELS = 1                # Mono audio
```

### Screen Share Settings
```python
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
SCREEN_FPS = 10
SCREEN_QUALITY = 50
```

### Session Settings
```python
MAX_USERS = 10                    # Maximum concurrent users
MAX_FILE_SIZE = 100 * 1024 * 1024 # 100MB file size limit
```

---

## Performance Metrics

### Bandwidth Usage (per user):
- **Video Upload**: ~300 KB/s
- **Audio Upload**: ~88 KB/s
- **Video Download**: ~300 KB/s × (N-1 users)
- **Audio Download**: ~88 KB/s
- **Screen Share**: ~150 KB/s (when active)

### Latency:
- **Audio**: ~23ms per chunk
- **Video**: ~33ms per frame (30 FPS)
- **Chat**: <10ms (TCP)
- **Screen Share**: ~100ms per frame (10 FPS)

### Resource Usage:
- **Server**: 2-8% CPU per user (varies with user count)
- **Client**: 5-15% CPU (depends on features in use)
- **Memory**: ~100-200 MB per client, ~300-500 MB server

---

## Security Considerations

⚠️ **Important**: This application is designed for trusted LAN environments.

- No encryption implemented (traffic sent in plaintext)
- No authentication beyond username
- No authorization controls
- Suitable for isolated, secure networks only
- **NOT recommended for public or untrusted networks**

---

## Future Enhancements

Potential improvements for future versions:
- End-to-end encryption for all communications
- User authentication and session tokens
- Recording functionality for video/audio
- Whiteboard/annotation tools
- Breakout rooms support
- Mobile client applications
- Cross-platform native builds

---

## License

This project is developed as an academic assignment for Computer Networks course.

---

## Contact & Support

**Developers**:
- Bhadresh L
- Santhana Srinivasan R

**Institution**: IIITDM  
**Course**: Computer Networks (SEM 5)  
**Date**: November 2025

---

## Acknowledgments

- Python community for excellent networking libraries
- PyQt6 for the robust GUI framework
- OpenCV for video processing capabilities
- Course instructors for project guidance

---

**End of README**
