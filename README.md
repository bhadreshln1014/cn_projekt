# 🎥 LAN Video Conferencing Application# LAN-Based Multi-User Communication Application



A feature-rich, real-time video conferencing application for Local Area Networks, built with Python and PyQt6.A robust, standalone, server-based multi-user communication application for Local Area Networks (LAN).



## ✨ Features## Features



### 🎬 Video Conferencing (Module 1)### Module 1: Multi-User Video Conferencing ✅

- Real-time video streaming at 30 FPS- Real-time video capture and transmission

- Support for up to 9 participants- Server-side broadcasting to all clients

- Dynamic grid layout- Multi-stream rendering in dynamic grid layout

- Camera on/off toggle- UDP-based low-latency streaming

- Camera toggle with hardware control

### 🎤 Audio Conferencing (Module 2)- Dynamic layouts (Auto, 1×1, 2×2, 3×3, 4×4)

- High-quality audio streaming (44.1 kHz, 16-bit)

- Jitter buffer for smooth playback### Module 2: Multi-User Audio Conferencing ✅

- Noise gate for echo reduction- Real-time audio capture from microphone

- Server-side audio mixing- Server-side audio mixing (NumPy-based averaging)

- Microphone mute/unmute- Low-latency audio playback

- Independent microphone and speaker controls

### 📺 Screen Sharing (Module 3)- 44100 Hz CD-quality audio

- Real-time screen broadcasting (10 FPS)- ~25-30ms end-to-end latency

- Presenter role management (one at a time)

- Automatic spotlight mode layout## Requirements

- 960x540 resolution with compression

- Python 3.8+

### 💬 Group Text Chat (Module 4)- Webcam (for video conferencing)

- Group chat (broadcast to all)- Microphone and speakers/headphones (for audio conferencing)

- Private 1-to-1 messaging- LAN connectivity

- Multi-recipient private chat

- Visual notifications## Installation

- System event messages

```bash

### 📁 File Sharing (Module 5)pip install -r requirements.txt

- Upload files up to 100 MB```

- Download with progress tracking

- Multi-file selection## Usage

- File deletion (owner only)

- Real-time file list updates### Start Server

```bash

## 🚀 Quick Startpython src/server/server.py

```

### Prerequisites

- Python 3.8 or higher### Start Client

- pip (Python package manager)```bash

- Webcam (for video conferencing)python src/client/client.py

- Microphone (for audio conferencing)```



### Installation## Architecture



1. **Clone or download the project**- **Network**: Client-Server architecture using TCP for control, UDP for video/audio streaming

   ```bash- **Video**: JPEG compression, 640×480 @ 30 FPS, UDP port 5001

   git clone <repository-url>- **Audio**: PCM 16-bit mono @ 44100 Hz, server-side mixing, UDP port 5002

   cd projekt- **Platform**: Cross-platform (Windows/Linux)

   ```- **UI**: Tkinter-based GUI with dynamic layouts



2. **Install dependencies**## Project Structure

   ```bash

   pip install -r requirements.txt```

   ```projekt/

├── src/

3. **Start the server**│   ├── server/        # Server application

   │   ├── client/        # Client application

   Windows:│   └── common/        # Shared utilities and constants

   ```bash├── requirements.txt

   start_server.bat└── README.md

   ``````

   
   Linux/Mac:
   ```bash
   ./start_server.sh
   ```

4. **Start the client(s)**
   
   Windows:
   ```bash
   start_client.bat
   ```
   
   Linux/Mac:
   ```bash
   ./start_client.sh
   ```

5. **Connect to the server**
   - Enter server IP address (default: localhost)
   - Enter your username
   - Click "Connect"

## 📚 Documentation

**All documentation is now organized in the [`docs/`](docs/) folder.**

### 📖 Start Here
- **[docs/INDEX.md](docs/INDEX.md)** - Complete documentation index
- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Quick start guide
- **[docs/INSTALLATION_AND_TESTING.md](docs/INSTALLATION_AND_TESTING.md)** - Detailed setup

### 🏗️ Architecture
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture overview

### 📦 Module Documentation
- **[docs/MODULE1_SUMMARY.md](docs/MODULE1_SUMMARY.md)** - Video Conferencing
- **[docs/MODULE2_SUMMARY.md](docs/MODULE2_SUMMARY.md)** - Audio Conferencing
- **[docs/MODULE3_SCREEN_SHARING.md](docs/MODULE3_SCREEN_SHARING.md)** - Screen Sharing
- **[docs/MODULE4_GROUP_CHAT.md](docs/MODULE4_GROUP_CHAT.md)** - Group Text Chat
- **[docs/MODULE5_FILE_SHARING.md](docs/MODULE5_FILE_SHARING.md)** - File Sharing

### 🔨 Build & Deploy
- **[docs/BUILD_INSTRUCTIONS.md](docs/BUILD_INSTRUCTIONS.md)** - Create executables

## 🌐 Network Architecture

| Module | Protocol | Port | Purpose |
|--------|----------|------|---------|
| Control | TCP | 5000 | User management, chat, notifications |
| Video | UDP | 5001 | Video frame streaming |
| Audio | UDP | 5002 | Audio streaming & mixing |
| Screen Control | TCP | 5003 | Presenter role coordination |
| Screen Data | UDP | 5004 | Screen frame streaming |
| File Transfer | TCP | 5005 | File upload/download |

## 💻 Technology Stack

- **GUI Framework**: PyQt6
- **Video Processing**: OpenCV (cv2)
- **Audio I/O**: PyAudio
- **Screen Capture**: mss (Multi-Screen Shot)
- **Audio Processing**: NumPy
- **Networking**: Python sockets (TCP/UDP)

## 📋 System Requirements

### Minimum Requirements
- **OS**: Windows 10/11, Linux (Ubuntu 20.04+), macOS 10.15+
- **Python**: 3.8 or higher
- **RAM**: 4 GB
- **Network**: 100 Mbps LAN

### Recommended
- **OS**: Windows 11, Ubuntu 22.04
- **Python**: 3.10+
- **RAM**: 8 GB or higher
- **Network**: Gigabit LAN (1 Gbps)

## 🛠️ Project Structure

```
projekt/
├── docs/                       # 📚 All documentation (16 files)
│   ├── INDEX.md               # Documentation index
│   ├── MODULE1_SUMMARY.md     # Video module docs
│   ├── MODULE2_SUMMARY.md     # Audio module docs
│   ├── MODULE3_SCREEN_SHARING.md  # Screen sharing docs
│   ├── MODULE4_GROUP_CHAT.md  # Chat module docs
│   ├── MODULE5_FILE_SHARING.md    # File sharing docs
│   └── ...                    # Architecture, build guides, etc.
├── src/
│   ├── client/
│   │   └── client.py          # Client application (3912 lines)
│   ├── server/
│   │   └── server.py          # Server application (920 lines)
│   └── common/
│       └── config.py          # Shared configuration
├── build/                      # Build artifacts (generated)
├── requirements.txt            # Python dependencies
├── build_client.bat/sh         # Build scripts for client
├── build_server.bat/sh         # Build scripts for server
└── start_client.bat/sh         # Launch scripts for client
```

## 🎯 Usage Guide

### Starting a Conference
1. Run the server first
2. Launch client applications on each machine
3. Connect all clients to the server IP
4. Video and audio start automatically (unmuted by default)

### Controls
- **🎥 Camera**: Toggle video on/off
- **🎤 Microphone**: Mute/unmute audio
- **📺 Screen Share**: Start/stop screen sharing
- **💬 Chat**: Send group or private messages
- **📁 Files**: Upload/download files

### Chat Features
- Select "Everyone" for group messages
- Select a username for private 1-to-1 chat
- Click 👥 icon to select multiple recipients
- Notifications appear when chat is closed

### File Sharing
- Click "Upload File" to share a file
- Check files to download, click "Download Selected"
- Delete your own files with "Delete Selected"

## ✅ Module Status

All 5 modules are **fully functional** and **production-ready**:

| Module | Status | Key Features |
|--------|--------|--------------|
| 1. Video | ✅ Complete | 30 FPS, 9 participants, grid layout |
| 2. Audio | ✅ Complete | Jitter buffer, noise gate, mixing |
| 3. Screen | ✅ Complete | Presenter mode, spotlight layout |
| 4. Chat | ✅ Complete | Group + private, notifications |
| 5. Files | ✅ Complete | Upload/download, progress tracking |

## 🐛 Troubleshooting

### Common Issues

**Audio is jittery or breaking**
- See [docs/AUDIO_FIXES.md](docs/AUDIO_FIXES.md)
- Check [docs/MODULE2_TESTING.md](docs/MODULE2_TESTING.md)

**Cannot connect to server**
- Verify server is running
- Check firewall settings (ports 5000-5005)
- Ensure clients and server are on same LAN

**Video not displaying**
- Check camera permissions
- Verify camera is not used by another application
- See [docs/MODULE1_SUMMARY.md](docs/MODULE1_SUMMARY.md)

**Build fails**
- Check Python version (3.8+)
- Verify all dependencies installed
- See [docs/BUILD_INSTRUCTIONS.md](docs/BUILD_INSTRUCTIONS.md)

## 📝 Development

### Running from Source

**Server:**
```bash
python src/server/server.py
```

**Client:**
```bash
python src/client/client.py
```

### Building Executables

Windows:
```bash
build_client.bat
build_server.bat
```

Linux/Mac:
```bash
./build_client.sh
./build_server.sh
```

Executables will be in `dist/` folder.

## 🧪 Testing

Each module includes comprehensive testing checklists in its documentation:
- [Module 1 Testing](docs/MODULE1_SUMMARY.md#testing-checklist)
- [Module 2 Testing](docs/MODULE2_SUMMARY.md#testing-checklist) + [MODULE2_TESTING.md](docs/MODULE2_TESTING.md)
- [Module 3 Testing](docs/MODULE3_SCREEN_SHARING.md#testing-checklist)
- [Module 4 Testing](docs/MODULE4_GROUP_CHAT.md#testing-checklist)
- [Module 5 Testing](docs/MODULE5_FILE_SHARING.md#testing-checklist)

## 🔒 Security Note

This application is designed for **trusted LAN environments**:
- No encryption on data transmission
- No authentication/authorization
- No input sanitization for untrusted data
- Do not expose to public internet

## 🎓 Academic Context

**Course**: Computer Networks (SEM 5)  
**Institution**: IIIT Dharwad  
**Objective**: Demonstrate practical implementation of:
- Client-server architecture
- TCP/UDP protocol usage
- Real-time media streaming
- Multi-threaded programming
- Network application design

## 📄 License

This project is developed as an academic assignment for educational purposes.

## 🙏 Acknowledgments

- PyQt6 for the excellent GUI framework
- OpenCV for video processing capabilities
- PyAudio for audio I/O
- mss for cross-platform screen capture

## 📞 Support

For detailed information on any component:
1. Check the [docs/INDEX.md](docs/INDEX.md) for navigation
2. Review the specific module documentation
3. Consult troubleshooting sections

---

**Project Repository**: IIITDM/SEM5/CN/projekt  
**Documentation**: [docs/](docs/) folder (16 comprehensive documents)  
**Total Lines of Code**: ~4,900 lines (client: 3912, server: 920, config: 59)

**Made with ❤️ for Computer Networks Course**
