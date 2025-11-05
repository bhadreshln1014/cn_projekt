# Screen Sharing Module - Technical Documentation

**Computer Networks Project**  
**Module**: Screen/Slide Sharing & Presentation  
**Developers**: Bhadresh L and Santhana Srinivasan R

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Implementation Details](#implementation-details)
4. [Presenter Control Protocol](#presenter-control-protocol)
5. [Screen Capture & Transmission](#screen-capture--transmission)
6. [Data Flow](#data-flow)
7. [Code Walkthrough](#code-walkthrough)
8. [Performance Considerations](#performance-considerations)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The screen sharing module allows one user at a time to broadcast their screen to all other participants. This is ideal for presentations, demonstrations, and collaborative work where visual context needs to be shared.

### Key Features
- **Single Presenter Mode**: Only one user can share screen at a time
- **Full Screen Capture**: Captures entire screen using MSS library
- **Dual Protocol**: TCP for control, UDP for frame data
- **Optimized Resolution**: 960×540 (16:9 aspect ratio) for balance
- **Lower Frame Rate**: 10 FPS to conserve bandwidth
- **Request/Grant System**: Prevents conflicts when multiple users try to present
- **Automatic Cleanup**: Screen sharing stops when presenter disconnects

### Technical Specifications
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Resolution | 960×540 pixels | Balances clarity and packet size |
| Frame Rate | 10 FPS | Sufficient for slides/screen, low bandwidth |
| Compression | JPEG (Quality: 50) | Fits within UDP packet limits |
| Control Protocol | TCP | Ensures reliable presenter commands |
| Data Protocol | UDP | Fast screen frame delivery |
| Control Port | 5003 | Dedicated TCP for presenter control |
| Data Port | 5004 | Dedicated UDP for screen frames |
| Max Packet Size | 65,000 bytes | Safely below UDP limit (65,507) |
| Bandwidth | ~150 KB/s | 10 frames × 15 KB per second |

### Presenter States
```
┌─────────────┐  REQUEST_PRESENTER  ┌──────────────┐
│   No One    │───────────────────▶ │  Presenter   │
│ Presenting  │◀───────────────────│   Active     │
└─────────────┘  RELEASE_PRESENTER  └──────────────┘
                 (or disconnect)
```

---

## Architecture

### Component Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                   PRESENTER CLIENT                             │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐      ┌────────────────────┐                │
│  │ User Clicks  │─────▶│ Request Presenter  │                │
│  │ "Start Share"│      │ Role (TCP)         │                │
│  └──────────────┘      └────────┬───────────┘                │
│                                  │                             │
│                                  ▼                             │
│                        ┌─────────────────────┐                │
│                        │ Server Grants/      │                │
│                        │ Denies Access       │                │
│                        └────────┬────────────┘                │
│                                  │ GRANTED                     │
│                                  ▼                             │
│                        ┌─────────────────────┐                │
│                        │ Screen Capture      │                │
│                        │ Thread Starts       │                │
│                        └────────┬────────────┘                │
│                                  │                             │
│  ┌──────────────┐               │                             │
│  │ Full Screen  │◀──────────────┘                             │
│  │ (MSS)        │                                              │
│  └──────┬───────┘                                              │
│         │                                                      │
│         ▼                                                      │
│  ┌──────────────┐                                              │
│  │ Resize to    │                                              │
│  │ 960×540      │                                              │
│  └──────┬───────┘                                              │
│         │                                                      │
│         ▼                                                      │
│  ┌──────────────┐                                              │
│  │ Compress     │                                              │
│  │ JPEG Q=50    │                                              │
│  └──────┬───────┘                                              │
│         │                                                      │
│         ▼                                                      │
│  ┌──────────────┐                                              │
│  │ Add Header   │                                              │
│  │ (Client ID)  │                                              │
│  └──────┬───────┘                                              │
│         │                                                      │
│         ▼                                                      │
│  ┌──────────────┐                                              │
│  │ UDP Send     │                                              │
│  │ Port 5004    │                                              │
│  └──────┬───────┘                                              │
│         │                                                      │
└─────────┼────────────────────────────────────────────────────┘
          │
          │ Screen Frame Data
          │
┌─────────▼────────────────────────────────────────────────────┐
│                    SERVER SIDE                                │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────┐      ┌───────────────────┐          │
│  │ TCP Control Socket │      │ UDP Data Socket   │          │
│  │ (Port 5003)        │      │ (Port 5004)       │          │
│  └────────┬───────────┘      └───────┬───────────┘          │
│           │                           │                       │
│           ▼                           ▼                       │
│  ┌────────────────────┐      ┌───────────────────┐          │
│  │ Presenter State    │      │ Receive Frame     │          │
│  │ Management         │      │ from Presenter    │          │
│  │ • presenter_id     │      └───────┬───────────┘          │
│  │ • Grant/Deny       │              │                       │
│  │ • Release          │              ▼                       │
│  └────────────────────┘      ┌───────────────────┐          │
│                               │ Store Latest      │          │
│                               │ Frame             │          │
│                               └───────┬───────────┘          │
│                                       │                       │
│                                       ▼                       │
│                               ┌───────────────────┐          │
│                               │ Broadcast to      │          │
│                               │ All Viewers       │          │
│                               └───────┬───────────┘          │
│                                       │                       │
└───────────────────────────────────────┼───────────────────────┘
                                        │
                                        │ Broadcast
                                        │
┌───────────────────────────────────────▼───────────────────────┐
│                    VIEWER CLIENTS                              │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│                        ┌───────────────────┐                 │
│                        │ Receive Frame     │                 │
│                        │ (UDP)             │                 │
│                        └───────┬───────────┘                 │
│                                │                              │
│                                ▼                              │
│                        ┌───────────────────┐                 │
│                        │ Extract Presenter │                 │
│                        │ ID from Header    │                 │
│                        └───────┬───────────┘                 │
│                                │                              │
│                                ▼                              │
│                        ┌───────────────────┐                 │
│                        │ Decompress JPEG   │                 │
│                        └───────┬───────────┘                 │
│                                │                              │
│                                ▼                              │
│                        ┌───────────────────┐                 │
│                        │ Display in        │                 │
│                        │ Screen Panel      │                 │
│                        │ (Full or Scaled)  │                 │
│                        └───────────────────┘                 │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. Presenter Request Protocol

**Location**: `src/client/client.py` - Method `toggle_screen_share()`

#### Request Sequence

```python
def toggle_screen_share(self):
    """
    Start or stop screen sharing
    Uses TCP control connection to request/release presenter role
    """
    if not self.is_presenting:
        # Request to become presenter
        try:
            # Connect to screen sharing control port
            self.screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.screen_socket.connect((self.server_address, SERVER_SCREEN_PORT))
            
            # Send presenter request
            self.screen_socket.send("REQUEST_PRESENTER\n".encode('utf-8'))
            
            # Wait for response
            response = self.screen_socket.recv(1024).decode('utf-8').strip()
            
            if response == "PRESENTER_OK":
                # Granted presenter role
                self.is_presenting = True
                self.current_presenter_id = self.client_id
                
                # Create UDP socket for screen data
                self.screen_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
                # Start screen capture thread
                self.screen_capture_thread = threading.Thread(
                    target=self.capture_screen,
                    daemon=True
                )
                self.screen_capture_thread.start()
                
                print(f"[{self.get_timestamp()}] Screen sharing started")
                
            elif response == "PRESENTER_DENIED":
                # Another user is already presenting
                print(f"[{self.get_timestamp()}] Screen sharing denied - another user is presenting")
                self.screen_socket.close()
                self.screen_socket = None
                # Show warning to user
                self.screen_share_denied_signal.emit("Another user is currently presenting")
                
        except Exception as e:
            print(f"Error starting screen share: {e}")
            self.screen_share_error_signal.emit(str(e))
    else:
        # Stop presenting
        self.stop_screen_share()
```

#### Server-Side Handling

**Location**: `src/server/server.py` - Method `handle_screen_share()`

```python
def handle_screen_share(self, conn, address):
    """
    Handle screen sharing control connection from client
    Manages presenter role assignment
    """
    client_id = None
    
    try:
        while self.running:
            data = conn.recv(1024).decode('utf-8').strip()
            
            if not data:
                break
            
            if data == "REQUEST_PRESENTER":
                # Client wants to become presenter
                with self.presenter_lock:
                    if self.presenter_id is None or self.presenter_id == client_id:
                        # Grant presenter role
                        self.presenter_id = client_id
                        conn.send("PRESENTER_OK\n".encode('utf-8'))
                        print(f"[{self.get_timestamp()}] Client {client_id} is now presenting")
                        self.broadcast_presenter_status()
                    else:
                        # Another user is presenting
                        conn.send("PRESENTER_DENIED\n".encode('utf-8'))
                        print(f"[{self.get_timestamp()}] Denied presenter request from {client_id} (presenter: {self.presenter_id})")
                        
            elif data == "RELEASE_PRESENTER":
                # Client releasing presenter role
                with self.presenter_lock:
                    if self.presenter_id == client_id:
                        self.presenter_id = None
                        self.broadcast_presenter_status()
                        print(f"[{self.get_timestamp()}] Client {client_id} stopped presenting")
                        
    except Exception as e:
        print(f"[{self.get_timestamp()}] Error in screen share control: {e}")
    
    finally:
        # Cleanup on disconnect
        with self.presenter_lock:
            if self.presenter_id == client_id:
                self.presenter_id = None
                self.broadcast_presenter_status()
```

---

### 2. Screen Capture (Presenter)

**Location**: `src/client/client.py` - Method `capture_screen()`

#### Capture Loop

```python
def capture_screen(self):
    """
    Screen capture thread - continuously captures screen and sends to server
    Uses MSS library for fast screen capture
    """
    with mss.mss() as sct:
        # Get primary monitor
        monitor = sct.monitors[1]  # Monitor 0 is all monitors combined
        
        while self.is_presenting:
            try:
                # Capture screen
                screenshot = sct.grab(monitor)
                
                # Convert to PIL Image
                img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                
                # Resize to target resolution (960×540)
                img_resized = img.resize(
                    (SCREEN_WIDTH, SCREEN_HEIGHT),
                    Image.Resampling.LANCZOS  # High-quality downsampling
                )
                
                # Convert PIL Image to OpenCV format
                frame = cv2.cvtColor(np.array(img_resized), cv2.COLOR_RGB2BGR)
                
                # Compress to JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), SCREEN_QUALITY]
                result, encoded_frame = cv2.imencode('.jpg', frame, encode_param)
                
                if not result:
                    continue
                
                # Serialize frame
                data = pickle.dumps(encoded_frame)
                
                # Add header with presenter ID (4 bytes)
                header = struct.pack('I', self.client_id)
                
                # Create packet
                message = header + struct.pack("Q", len(data)) + data
                
                # Check packet size
                if len(message) > MAX_SCREEN_PACKET_SIZE:
                    print(f"Warning: Screen packet too large ({len(message)} bytes), skipping")
                    continue
                
                # Send via UDP
                try:
                    self.screen_udp_socket.sendto(
                        message,
                        (self.server_address, SERVER_SCREEN_UDP_PORT)
                    )
                    
                    # Store frame locally so presenter can see their own screen
                    with self.screen_lock:
                        self.shared_screen_frame = frame
                        
                except socket.error as e:
                    print(f"Socket error sending screen: {e}")
                
                # Control frame rate (10 FPS)
                time.sleep(1.0 / SCREEN_FPS)
                
            except Exception as e:
                print(f"Error capturing screen: {e}")
                break
```

#### MSS Library Advantages
- **Speed**: 10-100x faster than PIL/Pillow screenshots
- **Cross-platform**: Works on Windows, macOS, Linux
- **No dependencies**: Pure Python with C extensions
- **Multi-monitor**: Can capture specific monitors

---

### 3. Screen Frame Broadcasting (Server)

**Location**: `src/server/server.py` - Method `receive_screen_streams()`

```python
def receive_screen_streams(self):
    """
    Receive screen frames from presenter and broadcast to all viewers
    Runs continuously in dedicated thread
    """
    while self.running:
        try:
            # Receive screen frame packet
            data, addr = self.screen_udp_socket.recvfrom(MAX_SCREEN_PACKET_SIZE)
            
            # Extract presenter ID from header
            if len(data) < 12:  # Minimum: 4 (ID) + 8 (size)
                continue
            
            presenter_id = struct.unpack('I', data[:4])[0]
            
            # Verify this client is the current presenter
            with self.presenter_lock:
                if self.presenter_id != presenter_id:
                    # Not the current presenter, ignore
                    continue
            
            # Store screen UDP address if not already stored
            with self.clients_lock:
                if presenter_id in self.clients:
                    if self.clients[presenter_id].get('screen_udp_address') is None:
                        self.clients[presenter_id]['screen_udp_address'] = addr
            
            # Store latest screen frame
            with self.screen_frame_lock:
                self.current_screen_frame = data
            
            # Broadcast to all clients (including presenter)
            with self.clients_lock:
                for client_id, client_info in self.clients.items():
                    udp_addr = client_info.get('udp_address')
                    if udp_addr:
                        try:
                            # Send screen frame to client
                            self.screen_udp_socket.sendto(data, udp_addr)
                        except socket.error:
                            pass  # Client may have disconnected
                            
        except Exception as e:
            if self.running:
                print(f"[{self.get_timestamp()}] Error in screen streaming: {e}")
```

---

### 4. Screen Display (Viewers)

**Location**: `src/client/client.py` - Method `receive_screen_streams()`

```python
def receive_screen_streams(self):
    """
    Receive shared screen frames from server and display
    """
    while self.connected:
        try:
            # Receive screen packet (reusing UDP video socket)
            data, _ = self.udp_socket.recvfrom(MAX_SCREEN_PACKET_SIZE)
            
            # Check if this is a screen share packet (has presenter ID header)
            if len(data) >= 12:
                # Extract presenter ID
                presenter_id = struct.unpack('I', data[:4])[0]
                
                # Extract frame data
                payload_size = struct.unpack('Q', data[4:12])[0]
                frame_data = data[12:12+payload_size]
                
                # Deserialize
                encoded_frame = pickle.loads(frame_data)
                
                # Decompress JPEG
                frame = cv2.imdecode(encoded_frame, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # Update presenter ID
                    self.current_presenter_id = presenter_id
                    
                    # Store screen frame
                    with self.screen_lock:
                        self.shared_screen_frame = frame
                        
        except Exception as e:
            if self.connected:
                print(f"Error receiving screen: {e}")
```

#### Display Update

```python
def update_screen_display(self):
    """
    Update shared screen display in GUI
    Called periodically by QTimer
    """
    with self.screen_lock:
        if self.shared_screen_frame is not None:
            # Show screen panel if hidden
            if not self.screen_sharing_active:
                self.screen_sharing_active = True
                self.show_screen_panel()
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(self.shared_screen_frame, cv2.COLOR_BGR2RGB)
            
            # Get dimensions
            height, width, channels = rgb_frame.shape
            bytes_per_line = channels * width
            
            # Create QImage
            qt_image = QImage(
                rgb_frame.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            )
            
            # Convert to QPixmap
            pixmap = QPixmap.fromImage(qt_image)
            
            # Scale to fit screen label
            scaled_pixmap = pixmap.scaled(
                self.screen_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Update display
            self.screen_label.setPixmap(scaled_pixmap)
        else:
            # No screen being shared
            if self.screen_sharing_active:
                self.screen_sharing_active = False
                self.hide_screen_panel()
```

---

## Data Flow

### Complete Screen Sharing Flow

```
┌────────────────────────────────────────────────────────────────┐
│ STEP 1: PRESENTER INITIALIZATION                               │
├────────────────────────────────────────────────────────────────┤
│ User clicks "Start Screen Share" button                       │
│ TCP connection established to port 5003                       │
│ Send: "REQUEST_PRESENTER\n"                                   │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 2: SERVER ARBITRATION                                     │
├────────────────────────────────────────────────────────────────┤
│ Server checks presenter_id status                             │
│ IF presenter_id is None:                                      │
│   - Set presenter_id = requesting_client_id                   │
│   - Send: "PRESENTER_OK\n"                                    │
│ ELSE:                                                          │
│   - Send: "PRESENTER_DENIED\n"                                │
│   - Close connection                                          │
└────────────────────────────────────────────────────────────────┘
                            ↓ GRANTED
┌────────────────────────────────────────────────────────────────┐
│ STEP 3: SCREEN CAPTURE (Presenter Client)                     │
├────────────────────────────────────────────────────────────────┤
│ MSS captures full screen → Raw pixel data                     │
│ Size: Varies (e.g., 1920×1080×3 = 6.2 MB uncompressed)       │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 4: PREPROCESSING                                          │
├────────────────────────────────────────────────────────────────┤
│ Convert MSS screenshot to PIL Image                           │
│ Resize: 960×540 (Lanczos resampling)                          │
│ Convert to OpenCV BGR format                                  │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 5: COMPRESSION                                            │
├────────────────────────────────────────────────────────────────┤
│ JPEG encoding, quality = 50                                   │
│ Result: ~10-20 KB (compression ratio ~50:1)                   │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 6: PACKETIZATION                                          │
├────────────────────────────────────────────────────────────────┤
│ Header: Presenter ID (4 bytes unsigned int)                   │
│ Size: Payload length (8 bytes unsigned long long)             │
│ Payload: Pickled JPEG data                                    │
│ Total: ~10-20 KB                                               │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 7: UDP TRANSMISSION                                       │
├────────────────────────────────────────────────────────────────┤
│ Send to server:5004 via UDP                                   │
│ No acknowledgment                                              │
│ Rate: 10 packets/second (10 FPS)                              │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 8: SERVER VALIDATION                                      │
├────────────────────────────────────────────────────────────────┤
│ Extract presenter_id from packet header                       │
│ Verify presenter_id matches current presenter                 │
│ IF match:                                                      │
│   - Store as current_screen_frame                             │
│   - Broadcast to all clients                                  │
│ ELSE:                                                          │
│   - Ignore packet (presenter changed)                         │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 9: BROADCAST                                              │
├────────────────────────────────────────────────────────────────┤
│ Server sends same packet to all clients (including presenter) │
│ Uses each client's registered UDP address                     │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 10: VIEWER RECEPTION                                      │
├────────────────────────────────────────────────────────────────┤
│ Receive packet on UDP socket                                  │
│ Parse header to identify as screen share packet               │
│ Extract presenter_id and frame data                           │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 11: DECOMPRESSION                                         │
├────────────────────────────────────────────────────────────────┤
│ Unpickle payload → JPEG byte array                            │
│ cv2.imdecode() → OpenCV BGR image (960×540)                   │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 12: DISPLAY                                               │
├────────────────────────────────────────────────────────────────┤
│ Convert BGR → RGB                                              │
│ Create QImage → QPixmap                                        │
│ Scale to fit screen panel (maintain aspect ratio)             │
│ Display in dedicated screen sharing panel                     │
└────────────────────────────────────────────────────────────────┘
```

---

## Protocol Specification

### Control Messages (TCP, Port 5003)

#### Client → Server
```
REQUEST_PRESENTER\n     - Request to become presenter
RELEASE_PRESENTER\n     - Release presenter role
```

#### Server → Client
```
PRESENTER_OK\n          - Presenter role granted
PRESENTER_DENIED\n      - Another user is presenting
```

#### Server → All Clients (Broadcast)
```
PRESENTER:<client_id>:<username>\n     - New presenter announced
PRESENTER:NONE\n                       - No one presenting
```

### Data Packets (UDP, Port 5004)

```
┌────────────────────────────────────────────────────────┐
│  Header: Presenter ID (4 bytes)                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Format: "I" (unsigned int)                       │ │
│  │ Value: Client ID of presenter                    │ │
│  └──────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────┤
│  Size Field (8 bytes)                                  │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Format: "Q" (unsigned long long)                 │ │
│  │ Value: Length of payload in bytes                │ │
│  └──────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────┤
│  Payload (variable, ~10-20 KB)                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Pickled JPEG-compressed screen frame             │ │
│  │ Original resolution: 960×540 BGR                 │ │
│  │ Compressed to ~10-20 KB                          │ │
│  └──────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
Total Size: 12 + payload ≈ 10-20 KB per frame
```

---

## Performance Considerations

### Bandwidth Analysis

**Per Frame**:
- Original screen: 1920×1080×3 = 6.2 MB
- Resized: 960×540×3 = 1.5 MB
- Compressed (Q=50): ~15 KB
- **Compression ratio**: ~100:1

**Per Second**:
- Frame rate: 10 FPS
- Bandwidth: 15 KB × 10 = **150 KB/s**
- Compare to video: 300 KB/s (2× more efficient)

**For N Viewers**:
- Presenter upload: 150 KB/s
- Presenter download: 0 (or 150 KB/s if receiving own stream)
- Server outbound: 150 KB/s × N
- Each viewer download: 150 KB/s

### Latency Analysis

| Component | Latency |
|-----------|---------|
| Screen capture (MSS) | ~5-10 ms |
| Resize + compress | ~10-20 ms |
| Network (Client→Server) | 1-5 ms |
| Server validation | <1 ms |
| Network (Server→Viewer) | 1-5 ms |
| Decompress + display | ~5-10 ms |
| **Total** | **~25-50 ms** |

Plus frame interval: 100 ms (10 FPS)  
**Total perceived latency**: ~125-150 ms

### CPU Usage

**Presenter**:
- Screen capture: ~3-5% CPU
- Resize: ~2-3% CPU
- JPEG compression: ~3-5% CPU
- **Total**: ~10-15% CPU

**Server**:
- Validation + broadcast: ~1-2% CPU per presenter
- No re-encoding, just forwarding

**Viewers**:
- JPEG decompression: ~2-3% CPU
- Display rendering: ~1-2% CPU
- **Total**: ~3-5% CPU

### Quality vs. Size Trade-off

| Quality | Size | Bandwidth (10 FPS) | Use Case |
|---------|------|-------------------|----------|
| 30 | ~8 KB | 80 KB/s | Low bandwidth, text-heavy slides |
| 50 | ~15 KB | 150 KB/s | **Default**, good balance |
| 70 | ~25 KB | 250 KB/s | High quality, detailed images |
| 90 | ~40 KB | 400 KB/s | Near-lossless, photo editing |

---

## Troubleshooting

### Common Issues

#### 1. Cannot Start Screen Sharing

**Symptoms**:
- "Start Screen Share" button doesn't work
- Error message: "Presenter denied"

**Diagnosis**:
```python
# Check presenter status on server
print(f"Current presenter: {self.presenter_id}")

# Check TCP connection
if self.screen_socket is None:
    print("Screen socket not connected")
```

**Solutions**:
- Verify another user is not already presenting
- Check TCP port 5003 is not blocked
- Ensure server screen sharing thread is running
- Verify client has TCP connection to server

#### 2. Screen Not Visible to Viewers

**Symptoms**:
- Presenter sees their screen
- Viewers see black/empty screen panel

**Diagnosis**:
```python
# On server: Check if frames are being received
print(f"Received screen frame from {presenter_id}, size: {len(data)}")

# On viewer: Check if frames are being received
print(f"Received screen frame, presenter: {presenter_id}")
```

**Solutions**:
- Check UDP port 5004 not blocked by firewall
- Verify server is broadcasting to all clients
- Confirm viewers' UDP addresses registered with server
- Check packet size < MAX_SCREEN_PACKET_SIZE

#### 3. Choppy/Laggy Screen Sharing

**Symptoms**:
- Screen updates slowly
- Frames skipped or delayed

**Causes & Solutions**:

| Cause | Solution |
|-------|----------|
| Low bandwidth | Reduce SCREEN_QUALITY to 30-40 |
| High CPU on presenter | Close unnecessary applications |
| Network congestion | Reduce video quality/FPS |
| Large screen resolution | Already optimized at 960×540 |

#### 4. Screen Share Packet Too Large

**Symptoms**:
- Console warning: "Screen packet too large"
- Screen not transmitting

**Diagnosis**:
```python
message_size = len(header) + len(size_field) + len(payload)
print(f"Packet size: {message_size} bytes (max: {MAX_SCREEN_PACKET_SIZE})")
```

**Solutions**:
- Reduce SCREEN_QUALITY (50 → 40 → 30)
- Reduce SCREEN_WIDTH and SCREEN_HEIGHT (960×540 → 800×450)
- Content with high detail may not compress well

#### 5. Presenter Role Stuck

**Symptoms**:
- User disconnected but others can't present
- presenter_id not clearing

**Diagnosis**:
```python
# On server
with self.presenter_lock:
    print(f"Presenter ID: {self.presenter_id}")
    print(f"Presenter in clients: {self.presenter_id in self.clients}")
```

**Solutions**:
```python
# Server should cleanup on disconnect
def handle_client_disconnect(self, client_id):
    with self.presenter_lock:
        if self.presenter_id == client_id:
            self.presenter_id = None
            self.broadcast_presenter_status()
            print(f"Presenter role released (client {client_id} disconnected)")
```

#### 6. Multiple Monitor Issues

**Symptoms**:
- Wrong monitor being captured
- Captured screen too small/large

**Solutions**:
```python
# List available monitors
with mss.mss() as sct:
    print("Available monitors:")
    for i, monitor in enumerate(sct.monitors):
        print(f"  Monitor {i}: {monitor}")

# Capture specific monitor
monitor = sct.monitors[2]  # Change index as needed
screenshot = sct.grab(monitor)
```

---

## Advanced Features (Not Implemented)

### Region/Window Capture
```python
# Capture specific window instead of full screen
import pygetwindow as gw

# Get window
window = gw.getWindowsWithTitle("PowerPoint")[0]

# Set capture region
monitor = {
    'left': window.left,
    'top': window.top,
    'width': window.width,
    'height': window.height
}

screenshot = sct.grab(monitor)
```

### Cursor Overlay
```python
# Draw cursor on screenshot
import win32gui, win32ui, win32con

# Get cursor position
cursor_x, cursor_y = win32gui.GetCursorPos()

# Draw cursor on frame
cv2.circle(frame, (cursor_x, cursor_y), 10, (0, 255, 0), -1)
```

### Annotation Tools
- Drawing tools (pen, highlighter)
- Shapes (rectangle, circle, arrow)
- Text overlay
- Laser pointer effect

### Presenter View
- Show presenter camera in corner of shared screen
- Picture-in-picture mode
- Speaker notes visible only to presenter

---

## Security Considerations

⚠️ **Screen Sharing Security Risks**:

1. **Sensitive Information Exposure**
   - Notifications may appear during sharing
   - Browser tabs/bookmarks visible
   - Desktop files visible
   
   **Mitigations**:
   - Close sensitive applications before sharing
   - Use "Do Not Disturb" mode
   - Consider window capture instead of full screen

2. **No Content Filtering**
   - Server cannot detect inappropriate content
   - All screen content shared as-is
   
3. **No Access Control**
   - Any user can request presenter role
   - First-come-first-served
   
   **Future Enhancement**:
   - Presenter approval by host
   - Role-based permissions

---

## Future Enhancements

1. **Window/Application Sharing**: Share specific window instead of full screen
2. **Presenter Controls**: Pause, laser pointer, annotations
3. **Quality Auto-Adjustment**: Adapt quality based on network conditions
4. **Screen Recording**: Record screen share sessions
5. **Multi-Presenter**: Split-screen view of multiple presenters
6. **Remote Control**: Allow viewers to control presenter's screen (with permission)
7. **H.264 Encoding**: Better compression for screen content
8. **Presenter Queue**: Fair rotation when multiple users want to present

---

**End of Screen Sharing Module Documentation**
