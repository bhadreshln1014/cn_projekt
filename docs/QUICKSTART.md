# Quick Start Guide

## Installation

1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Option 1: On the Same Computer (Testing)

**Terminal 1 - Start the Server:**
```bash
python src/server/server.py
```

**Terminal 2 & 3 - Start Clients:**
```bash
python src/client/client.py
```
- In the connection dialog, use `127.0.0.1` as the server IP
- Enter different usernames for each client

### Option 2: On LAN (Production Use)

**On the Server Computer:**
1. Find your local IP address:
   - Windows: `ipconfig` (look for IPv4 Address)
   - Linux: `ifconfig` or `ip addr`
2. Start the server:
   ```bash
   python src/server/server.py
   ```
3. Note the IP address (e.g., 192.168.1.100)

**On Client Computers:**
1. Start the client:
   ```bash
   python src/client/client.py
   ```
2. In the connection dialog:
   - Enter the server's IP address (e.g., 192.168.1.100)
   - Enter your username
   - Click "Connect"

## Features

### Module 1: Video Conferencing ✓
- **Real-time video capture** from webcam
- **UDP-based streaming** for low latency
- **Multi-user support** (up to 10 users)
- **Grid layout** showing all participants
- **Automatic broadcasting** of video streams
- **Graceful connection/disconnection** handling

## Architecture Overview

### Server
- **TCP Socket (Port 5000)**: Handles user authentication, session management, and control messages
- **UDP Socket (Port 5001)**: Receives and broadcasts video streams
- **Threading**: Separate threads for accepting connections and handling video streams
- **Session Management**: Tracks connected users and their video streams

### Client
- **TCP Connection**: Maintains persistent connection for control messages
- **UDP Socket**: Sends captured video and receives others' video streams
- **Video Capture**: Uses OpenCV to capture from webcam at 640x480, 30 FPS
- **JPEG Compression**: Compresses frames to ~60% quality for network efficiency
- **GUI**: Tkinter-based interface with 3x3 grid for up to 9 simultaneous video streams

## Network Protocol

### TCP Control Messages
- `CONNECT:<username>` - Client connects to server
- `ID:<client_id>` - Server assigns client ID
- `USERS:<serialized_user_list>` - Server broadcasts user list updates
- `PING`/`PONG` - Heartbeat mechanism

### UDP Video Packets
- Format: `[4 bytes: client_id][remaining: JPEG frame data]`
- Client → Server: Own video stream
- Server → Clients: Broadcasts received streams to all other clients

## Troubleshooting

### Camera Not Working
- Check camera permissions
- Ensure no other application is using the camera
- Try running with administrator privileges

### Connection Failed
- Verify server is running
- Check firewall settings (allow ports 5000 and 5001)
- Ensure both computers are on the same network
- Verify the server IP address is correct

### Poor Video Quality
- Adjust `VIDEO_QUALITY` in `src/common/config.py` (0-100)
- Check network bandwidth
- Reduce `VIDEO_WIDTH` and `VIDEO_HEIGHT` for slower networks

## Configuration

Edit `src/common/config.py` to customize:
- Video resolution and quality
- Network ports
- Maximum users
- Grid layout

## Future Modules (Upcoming)
- Module 2: Audio Conferencing
- Module 3: Text Chat
- Module 4: Screen Sharing/Presentation
- Module 5: File Sharing

## System Requirements
- Python 3.8+
- Webcam
- LAN connectivity
- Windows/Linux OS
