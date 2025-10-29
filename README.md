# LAN-Based Multi-User Communication Application

A robust, standalone, server-based multi-user communication application for Local Area Networks (LAN).

## Features

### Module 1: Multi-User Video Conferencing ✅
- Real-time video capture and transmission
- Server-side broadcasting to all clients
- Multi-stream rendering in dynamic grid layout
- UDP-based low-latency streaming
- Camera toggle with hardware control
- Dynamic layouts (Auto, 1×1, 2×2, 3×3, 4×4)

### Module 2: Multi-User Audio Conferencing ✅
- Real-time audio capture from microphone
- Server-side audio mixing (NumPy-based averaging)
- Low-latency audio playback
- Independent microphone and speaker controls
- 44100 Hz CD-quality audio
- ~25-30ms end-to-end latency

## Requirements

- Python 3.8+
- Webcam (for video conferencing)
- Microphone and speakers/headphones (for audio conferencing)
- LAN connectivity

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Start Server
```bash
python src/server/server.py
```

### Start Client
```bash
python src/client/client.py
```

## Architecture

- **Network**: Client-Server architecture using TCP for control, UDP for video/audio streaming
- **Video**: JPEG compression, 640×480 @ 30 FPS, UDP port 5001
- **Audio**: PCM 16-bit mono @ 44100 Hz, server-side mixing, UDP port 5002
- **Platform**: Cross-platform (Windows/Linux)
- **UI**: Tkinter-based GUI with dynamic layouts

## Project Structure

```
projekt/
├── src/
│   ├── server/        # Server application
│   ├── client/        # Client application
│   └── common/        # Shared utilities and constants
├── requirements.txt
└── README.md
```
