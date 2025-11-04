# 📚 Documentation Index

Complete documentation for the LAN Video Conferencing Application project.

## 🗂️ Documentation Overview

### 📖 Getting Started
- **[README.md](../README.md)** - Main project README (in root)
- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide
- **[INSTALLATION_AND_TESTING.md](INSTALLATION_AND_TESTING.md)** - Setup and testing

### 🏗️ Architecture & Design
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture overview
- **[LAYOUT_GUIDE.md](LAYOUT_GUIDE.md)** - UI layout system
- **[UI_IMPROVEMENTS.md](UI_IMPROVEMENTS.md)** - UI enhancements
- **[MATERIAL_ICONS.md](MATERIAL_ICONS.md)** - Icon usage guide

### 📦 Module Documentation

#### Module 1: Video Conferencing
**[MODULE1_SUMMARY.md](MODULE1_SUMMARY.md)**
- Real-time video streaming (30 FPS, 640x480)
- UDP-based transmission
- Dynamic grid layout (1-9 participants)
- Camera controls (on/off toggle)

#### Module 2: Audio Conferencing
**[MODULE2_SUMMARY.md](MODULE2_SUMMARY.md)**
- Real-time audio streaming (44.1 kHz, 16-bit mono)
- Jitter buffer with pre-buffering (5 frames)
- Noise gate (RMS > 100) for echo reduction
- Server-side rate-limited mixing
- Microphone controls (mute/unmute)
- **[MODULE2_TESTING.md](MODULE2_TESTING.md)** - Audio testing procedures
- **[AUDIO_FIXES.md](AUDIO_FIXES.md)** - Audio quality improvements

#### Module 3: Screen Sharing
**[MODULE3_SCREEN_SHARING.md](MODULE3_SCREEN_SHARING.md)**
- Real-time screen broadcasting (10 FPS, 960x540)
- Presenter role management (mutual exclusion)
- TCP control + UDP streaming
- Spotlight mode UI layout
- JPEG compression (50% quality)

#### Module 4: Group Text Chat
**[MODULE4_GROUP_CHAT.md](MODULE4_GROUP_CHAT.md)**
- Group chat (broadcast to all)
- Private chat (1-to-1 and multi-recipient)
- Real-time message delivery via TCP
- Chat notifications with popups
- System messages for join/leave events

#### Module 5: File Sharing
**[MODULE5_FILE_SHARING.md](MODULE5_FILE_SHARING.md)**
- Upload files to server (max 100 MB)
- Download files with progress tracking
- TCP-based reliable transfer
- File management (delete own files)
- Multi-file selection

### 🔨 Build & Deployment
- **[BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)** - PyInstaller build guide
- Build scripts: `build_client.bat/sh`, `build_server.bat/sh`
- Spec files: `build_client.spec`, `build_server.spec`

## 🎯 Quick Navigation Guide

### For New Users → Start Here
1. [QUICKSTART.md](QUICKSTART.md) - Get up and running in 5 minutes
2. [INSTALLATION_AND_TESTING.md](INSTALLATION_AND_TESTING.md) - Full setup guide
3. [MODULE1_SUMMARY.md](MODULE1_SUMMARY.md) - Learn about video features

### For Developers → Deep Dive
1. [ARCHITECTURE.md](ARCHITECTURE.md) - Understand system design
2. [MODULE1_SUMMARY.md](MODULE1_SUMMARY.md) through [MODULE5_FILE_SHARING.md](MODULE5_FILE_SHARING.md) - Study each module
3. [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) - Deploy the application

### For Testers → Validation
1. [INSTALLATION_AND_TESTING.md](INSTALLATION_AND_TESTING.md) - Setup test environment
2. Each MODULE document has a "Testing Checklist" section
3. [MODULE2_TESTING.md](MODULE2_TESTING.md) - Specific audio tests

### For Designers → UI/UX
1. [UI_IMPROVEMENTS.md](UI_IMPROVEMENTS.md) - UI philosophy and enhancements
2. [LAYOUT_GUIDE.md](LAYOUT_GUIDE.md) - Layout system details
3. [MATERIAL_ICONS.md](MATERIAL_ICONS.md) - Icon guidelines

## 🌐 Network Architecture Summary

| Module | Protocol | Port | Purpose |
|--------|----------|------|---------|
| Control | TCP | 5000 | User management, chat, notifications |
| Video | UDP | 5001 | Video frame streaming |
| Audio | UDP | 5002 | Audio streaming & mixing |
| Screen Control | TCP | 5003 | Presenter role coordination |
| Screen Data | UDP | 5004 | Screen frame streaming |
| File Transfer | TCP | 5005 | File upload/download |

## 💻 Technology Stack

- **GUI**: PyQt6 (Qt6 framework)
- **Video**: OpenCV (cv2)
- **Audio**: PyAudio + NumPy
- **Screen**: mss (Multi-Screen Shot)
- **Networking**: Python sockets (TCP/UDP)
- **Build**: PyInstaller

## ✅ Project Status

All 5 modules are **fully functional** and **production-ready**:

| Module | Status | Documentation |
|--------|--------|---------------|
| Video Conferencing | ✅ Complete | [MODULE1_SUMMARY.md](MODULE1_SUMMARY.md) |
| Audio Conferencing | ✅ Complete | [MODULE2_SUMMARY.md](MODULE2_SUMMARY.md) |
| Screen Sharing | ✅ Complete | [MODULE3_SCREEN_SHARING.md](MODULE3_SCREEN_SHARING.md) |
| Group Text Chat | ✅ Complete | [MODULE4_GROUP_CHAT.md](MODULE4_GROUP_CHAT.md) |
| File Sharing | ✅ Complete | [MODULE5_FILE_SHARING.md](MODULE5_FILE_SHARING.md) |

## 📊 Documentation Standards

Each module document includes:
- ✅ Overview with architecture diagrams
- ✅ Implementation details with code snippets
- ✅ Network protocol specifications
- ✅ UI component descriptions
- ✅ Technical specifications table
- ✅ Error handling strategies
- ✅ Performance characteristics
- ✅ Testing checklist
- ✅ Known limitations
- ✅ Future enhancement ideas

## 🔍 Key Features Across All Modules

### Real-Time Communication
- Video: 30 FPS streaming with dynamic grid
- Audio: 44.1 kHz with jitter buffer and noise gate
- Screen: 10 FPS presenter mode with spotlight layout
- Chat: Instant messaging (group + private)
- Files: Upload/download with progress tracking

### Robust Design
- Multi-threaded server architecture
- Separate TCP/UDP channels per module
- Thread-safe data structures with locks
- Comprehensive error handling
- Cross-platform compatibility (Windows/Linux)

### User Experience
- Intuitive PyQt6 interface
- Material Design icons
- Real-time notifications
- Progress tracking for long operations
- Collapsible panels for clean layout

## 📁 File Organization

```
projekt/
├── docs/                       <- You are here!
│   ├── INDEX.md               <- This file
│   ├── README.md              <- Original project README
│   ├── QUICKSTART.md          
│   ├── ARCHITECTURE.md        
│   ├── MODULE1_SUMMARY.md     
│   ├── MODULE2_SUMMARY.md     
│   ├── MODULE2_TESTING.md     
│   ├── MODULE3_SCREEN_SHARING.md
│   ├── MODULE4_GROUP_CHAT.md  
│   ├── MODULE5_FILE_SHARING.md
│   ├── BUILD_INSTRUCTIONS.md  
│   ├── INSTALLATION_AND_TESTING.md
│   ├── UI_IMPROVEMENTS.md     
│   ├── LAYOUT_GUIDE.md        
│   ├── MATERIAL_ICONS.md      
│   └── AUDIO_FIXES.md         
├── src/
│   ├── client/
│   │   └── client.py          <- Main client application (3912 lines)
│   ├── server/
│   │   └── server.py          <- Server application (920 lines)
│   └── common/
│       └── config.py          <- Shared configuration (59 lines)
├── build/                      <- Build artifacts
├── requirements.txt            <- Python dependencies
├── build_client.bat/sh         <- Client build scripts
├── build_server.bat/sh         <- Server build scripts
└── start_client.bat/sh         <- Client launch scripts
```

## 🆘 Troubleshooting

### Audio Issues
→ See [AUDIO_FIXES.md](AUDIO_FIXES.md) and [MODULE2_TESTING.md](MODULE2_TESTING.md)

### Build Issues
→ See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)

### Network/Connection Issues
→ See [ARCHITECTURE.md](ARCHITECTURE.md) for port configuration

### UI/Layout Issues
→ See [LAYOUT_GUIDE.md](LAYOUT_GUIDE.md) and [UI_IMPROVEMENTS.md](UI_IMPROVEMENTS.md)

## 🎓 Academic Context

**Course**: Computer Networks (SEM 5)  
**Institution**: IIITDM Kancheepuram  
**Project**: LAN Video Conferencing Application  
**Objective**: Implement a complete video conferencing system demonstrating:
- Client-server architecture
- TCP/UDP protocol usage
- Real-time media streaming
- Multi-threaded programming
- Network programming concepts

## 📝 Contributing Guidelines

When updating documentation:
1. Use the established template structure (see any MODULE doc)
2. Include code snippets for technical explanations
3. Update testing checklists for new features
4. Document network protocol changes
5. Update this INDEX.md for new documents

## 🔗 Related Resources

- **PyQt6 Documentation**: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **OpenCV Documentation**: https://docs.opencv.org/
- **PyAudio Documentation**: https://people.csail.mit.edu/hubert/pyaudio/docs/
- **Socket Programming**: Python `socket` module documentation

---

**Documentation Maintained By**: Bhadresh L and Santhana Srinivasan R
**Last Updated**: Nov, 2025  
**Total Documentation**: 15 files covering all aspects of the project
