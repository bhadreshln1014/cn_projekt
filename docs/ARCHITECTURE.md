# System Architecture Documentation

## Overview
The LAN-Based Multi-User Communication Application follows a **client-server architecture** with a star topology, where all communication flows through a central server.

---

## Network Topology

```
                          ┌─────────────────────┐
                          │                     │
                          │   Central Server    │
                          │   (192.168.1.100)   │
                          │                     │
                          │  TCP Port: 5000     │
                          │  UDP Port: 5001     │
                          │                     │
                          └──────────┬──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
            ┌───────▼──────┐  ┌──────▼──────┐  ┌─────▼────────┐
            │              │  │             │  │              │
            │  Client 1    │  │  Client 2   │  │  Client 3    │
            │  (Alice)     │  │  (Bob)      │  │  (Charlie)   │
            │              │  │             │  │              │
            │  ID: 0       │  │  ID: 1      │  │  ID: 2       │
            └──────────────┘  └─────────────┘  └──────────────┘
```

---

## Component Architecture

### Server Components

```
┌─────────────────────────────────────────────────────────┐
│                    SERVER APPLICATION                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         Main Thread (Connection Acceptor)       │    │
│  │  - Listens on TCP port 5000                     │    │
│  │  - Accepts new client connections               │    │
│  │  - Spawns client handler threads                │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │       UDP Video Receiver Thread                 │    │
│  │  - Listens on UDP port 5001                     │    │
│  │  - Receives video frames from clients           │    │
│  │  - Broadcasts frames to other clients           │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │     Client Handler Threads (one per client)     │    │
│  │  - Manages TCP connection to specific client    │    │
│  │  - Handles control messages (PING, etc.)        │    │
│  │  - Updates client metadata                      │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │              Data Structures                     │    │
│  │                                                  │    │
│  │  clients = {                                     │    │
│  │    client_id: {                                  │    │
│  │      'tcp_conn': socket,                         │    │
│  │      'address': (ip, port),                      │    │
│  │      'udp_address': (ip, port),                  │    │
│  │      'username': str                             │    │
│  │    }                                             │    │
│  │  }                                               │    │
│  │                                                  │    │
│  │  video_frames = {                                │    │
│  │    client_id: frame_data                         │    │
│  │  }                                               │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Client Components

```
┌─────────────────────────────────────────────────────────┐
│                   CLIENT APPLICATION                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │              Main/GUI Thread                    │    │
│  │  - Renders Tkinter GUI                          │    │
│  │  - Updates video grid at ~30 FPS                │    │
│  │  - Handles user input                           │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │        Video Capture Thread                     │    │
│  │  - Captures frames from webcam                  │    │
│  │  - Compresses to JPEG                           │    │
│  │  - Sends via UDP to server                      │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │      TCP Control Receiver Thread                │    │
│  │  - Receives control messages from server        │    │
│  │  - Updates user list                            │    │
│  │  - Handles server notifications                 │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │       UDP Video Receiver Thread                 │    │
│  │  - Receives video frames from server            │    │
│  │  - Decompresses JPEG data                       │    │
│  │  - Stores in video_streams dict                 │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │              Data Structures                     │    │
│  │                                                  │    │
│  │  video_streams = {                               │    │
│  │    client_id: frame (numpy array)                │    │
│  │  }                                               │    │
│  │                                                  │    │
│  │  users = {                                       │    │
│  │    client_id: username                           │    │
│  │  }                                               │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Communication Flow

### 1. Client Connection Flow

```
Client                          Server
  │                               │
  │  TCP SYN (Port 5000)         │
  │─────────────────────────────>│
  │                               │
  │  TCP SYN-ACK                 │
  │<─────────────────────────────│
  │                               │
  │  "CONNECT:Alice"             │
  │─────────────────────────────>│
  │                               │ [Assign ID: 0]
  │                               │ [Store client info]
  │  "ID:0"                      │
  │<─────────────────────────────│
  │                               │
  │                               │ [Broadcast user list to all]
  │  "USERS:<serialized_list>"   │
  │<─────────────────────────────│
  │                               │
```

### 2. Video Streaming Flow

```
Alice (ID:0)                Server                  Bob (ID:1)
     │                         │                         │
     │ [Capture frame]         │                         │
     │ [Compress to JPEG]      │                         │
     │                         │                         │
     │ UDP: [0][JPEG_DATA]    │                         │
     │────────────────────────>│                         │
     │                         │ [Extract ID:0]          │
     │                         │ [Store frame]           │
     │                         │                         │
     │                         │ UDP: [0][JPEG_DATA]    │
     │                         │────────────────────────>│
     │                         │                         │ [Receive frame]
     │                         │                         │ [Decode JPEG]
     │                         │                         │ [Display Alice]
     │                         │                         │
     │                         │                         │ [Capture frame]
     │                         │                         │ [Compress]
     │                         │                         │
     │                         │ UDP: [1][JPEG_DATA]    │
     │                         │<────────────────────────│
     │                         │                         │
     │ UDP: [1][JPEG_DATA]    │                         │
     │<────────────────────────│                         │
     │                         │                         │
     │ [Receive frame]         │                         │
     │ [Decode JPEG]           │                         │
     │ [Display Bob]           │                         │
```

### 3. User Disconnection Flow

```
Client (Alice)                 Server                    Other Clients
     │                           │                              │
     │ [Close application]       │                              │
     │                           │                              │
     │ TCP FIN                   │                              │
     │──────────────────────────>│                              │
     │                           │ [Detect disconnection]       │
     │                           │ [Remove from clients dict]   │
     │                           │ [Remove from video_frames]   │
     │                           │                              │
     │                           │ "USERS:<updated_list>"      │
     │                           │─────────────────────────────>│
     │                           │                              │
     │                           │                              │ [Update UI]
     │                           │                              │ [Remove Alice's video]
```

---

## Data Packet Formats

### TCP Control Messages

#### CONNECT (Client → Server)
```
Format: "CONNECT:<username>"
Example: "CONNECT:Alice"
```

#### ID Assignment (Server → Client)
```
Format: "ID:<client_id>"
Example: "ID:0"
```

#### User List Broadcast (Server → All Clients)
```
Format: "USERS:<hex_encoded_pickle>"
Example: "USERS:80049522000000..."

Decoded structure:
[
  {'id': 0, 'username': 'Alice'},
  {'id': 1, 'username': 'Bob'},
  {'id': 2, 'username': 'Charlie'}
]
```

#### Heartbeat (Client ↔ Server)
```
Request: "PING"
Response: "PONG"
```

### UDP Video Packets

```
┌────────────────┬──────────────────────────────────┐
│  Client ID     │      JPEG Frame Data             │
│  (4 bytes)     │      (Variable length)           │
│  uint32        │      Raw bytes                   │
└────────────────┴──────────────────────────────────┘
    │                      │
    │                      │
    └─> Identifies sender  └─> Compressed video frame

Total Size: ~50 KB per frame (varies with quality)
```

---

## Threading Model

### Server Threading

```
┌─────────────────────────────────────────────┐
│             Main Process                     │
│                                              │
│  ┌────────────────────────────────────┐    │
│  │  Main Thread                        │    │
│  │  - Initialize sockets               │    │
│  │  - Start UDP receiver thread        │    │
│  │  - Accept connections (blocking)    │    │
│  └────────────────────────────────────┘    │
│                                              │
│  ┌────────────────────────────────────┐    │
│  │  UDP Receiver Thread (daemon)       │    │
│  │  - Continuous loop                  │    │
│  │  - Recvfrom() on UDP socket         │    │
│  │  - Broadcast to other clients       │    │
│  └────────────────────────────────────┘    │
│                                              │
│  ┌────────────────────────────────────┐    │
│  │  Client Handler 1 (daemon)          │    │
│  │  - Handle Alice's TCP connection    │    │
│  └────────────────────────────────────┘    │
│                                              │
│  ┌────────────────────────────────────┐    │
│  │  Client Handler 2 (daemon)          │    │
│  │  - Handle Bob's TCP connection      │    │
│  └────────────────────────────────────┘    │
│                                              │
│  ...more client handlers...                │
│                                              │
└─────────────────────────────────────────────┘
```

### Client Threading

```
┌─────────────────────────────────────────────┐
│             Main Process                     │
│                                              │
│  ┌────────────────────────────────────┐    │
│  │  Main/GUI Thread                    │    │
│  │  - Tkinter event loop               │    │
│  │  - Update video grid                │    │
│  │  - Handle user input                │    │
│  └────────────────────────────────────┘    │
│                                              │
│  ┌────────────────────────────────────┐    │
│  │  Video Capture Thread (daemon)      │    │
│  │  - Read from webcam                 │    │
│  │  - Compress frame                   │    │
│  │  - Send via UDP                     │    │
│  └────────────────────────────────────┘    │
│                                              │
│  ┌────────────────────────────────────┐    │
│  │  TCP Receiver Thread (daemon)       │    │
│  │  - Receive control messages         │    │
│  │  - Update user list                 │    │
│  └────────────────────────────────────┘    │
│                                              │
│  ┌────────────────────────────────────┐    │
│  │  UDP Receiver Thread (daemon)       │    │
│  │  - Receive video frames             │    │
│  │  - Decode and store                 │    │
│  └────────────────────────────────────┘    │
│                                              │
└─────────────────────────────────────────────┘
```

---

## State Diagrams

### Client Connection State

```
     ┌──────────────┐
     │ Disconnected │
     └──────┬───────┘
            │ connect_to_server()
            │
            ▼
     ┌──────────────┐
     │  Connecting  │
     └──────┬───────┘
            │ Receive ID
            │
            ▼
     ┌──────────────┐
     │  Connected   │◄──┐
     └──────┬───────┘   │
            │            │ Heartbeat
            │            │
            │            │
            ▼            │
     ┌──────────────┐   │
     │   Active     │───┘
     │  (Streaming) │
     └──────┬───────┘
            │ disconnect()
            │ or error
            ▼
     ┌──────────────┐
     │ Disconnected │
     └──────────────┘
```

### Video Stream State

```
     ┌──────────────┐
     │   No Camera  │
     └──────┬───────┘
            │ start_video_capture()
            │
            ▼
     ┌──────────────┐
     │  Capturing   │
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  Compressing │
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │   Sending    │───┐
     └──────┬───────┘   │
            │            │
            └────────────┘
              (Loop at ~30 FPS)
```

---

## Security Considerations

### Current Implementation
- ⚠️ **No encryption** (plaintext communication)
- ⚠️ **No authentication** (anyone can connect)
- ⚠️ **No authorization** (all users have same privileges)
- ⚠️ **No input validation** (vulnerable to malformed data)

### Recommendations for Production
1. Implement TLS/SSL for TCP connections
2. Add password/token-based authentication
3. Validate and sanitize all user input
4. Rate limiting to prevent DoS
5. Encrypt UDP video packets (e.g., DTLS)
6. Add user roles and permissions

---

## Scalability Analysis

### Current Limits
- **Max Users**: 10 (configurable in `config.py`)
- **Max Displayed Streams**: 9 (3×3 grid)
- **Bandwidth per Client**: ~400 KB/s upload, ~3.6 MB/s download (10 users)
- **Server Bandwidth**: ~4 MB/s total

### Bottlenecks
1. **Server CPU**: Video relay (minimal processing)
2. **Network Bandwidth**: Most significant bottleneck
3. **Client GPU/CPU**: Video decoding and rendering
4. **Client Network**: Upload bandwidth for video stream

### Scaling Strategies
- Use multicast instead of unicast for video distribution
- Implement selective forwarding (only active speaker)
- Add hardware-accelerated video encoding/decoding
- Use more efficient codecs (H.264, VP8)
- Implement adaptive bitrate based on network conditions

---

## Error Handling

### Server-Side
- Connection errors: Log and continue accepting new connections
- Broken pipes: Clean up client resources and notify others
- Port in use: Display error and exit gracefully
- Full capacity: Reject new connections with error message

### Client-Side
- Connection refused: Display error dialog with retry option
- Camera not available: Disable video capture, continue with audio/chat
- Network timeout: Attempt reconnection with exponential backoff
- Frame decode error: Skip frame, continue with next

---

## Performance Optimization

### Implemented Optimizations
1. **JPEG Compression**: Reduces frame size by ~95%
2. **UDP for Video**: Eliminates TCP overhead
3. **Thread-per-client**: Concurrent handling
4. **Latest-frame-only**: Discard old frames
5. **Minimal Server Processing**: Direct relay, no transcoding

### Future Optimizations
1. **Hardware Acceleration**: Use GPU for encoding/decoding
2. **Frame Skipping**: Adaptive FPS based on bandwidth
3. **Resolution Scaling**: Lower resolution for remote clients
4. **Connection Pooling**: Reuse sockets
5. **Zero-copy**: Use memory mapping for frame transfers

---

This architecture provides a solid foundation for Module 1 and can be extended for additional modules (audio, chat, screen sharing, file transfer).
