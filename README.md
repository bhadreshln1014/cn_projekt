# LAN-Based Multi-User Communication Application

A robust, standalone, server-based multi-user communication application for Local Area Networks (LAN).

## Features

### Module 1: Multi-User Video Conferencing
- Real-time video capture and transmission
- Server-side broadcasting to all clients
- Multi-stream rendering in grid layout
- UDP-based low-latency streaming

## Requirements

- Python 3.8+
- Webcam
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

- **Network**: Client-Server architecture using TCP/IP for control and UDP for video streaming
- **Platform**: Cross-platform (Windows/Linux)
- **UI**: Tkinter-based GUI

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
