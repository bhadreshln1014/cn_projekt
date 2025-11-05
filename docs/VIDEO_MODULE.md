# Video Conferencing Module - Technical Documentation

**Computer Networks Project**  
**Module**: Multi-User Video Conferencing  
**Developers**: Bhadresh L and Santhana Srinivasan R

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Implementation Details](#implementation-details)
4. [Protocol Specification](#protocol-specification)
5. [Data Flow](#data-flow)
6. [Code Walkthrough](#code-walkthrough)
7. [Performance Optimization](#performance-optimization)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The video conferencing module enables real-time video communication between multiple users on a LAN. It implements a client-server architecture where clients capture and transmit video streams to a central server, which then broadcasts these streams to all connected clients.

### Key Features
- **Multi-stream Support**: Up to 10 simultaneous video feeds
- **Real-time Transmission**: UDP protocol for low-latency streaming
- **Adaptive Layout**: Automatic grid arrangement of video feeds
- **Compression**: JPEG-based frame compression for bandwidth efficiency
- **Thread-safe Operations**: Concurrent capture, transmission, and rendering

### Technical Specifications
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Resolution | 640x480 pixels | Balance between quality and bandwidth |
| Frame Rate | 30 FPS | Standard rate for smooth video |
| Compression | JPEG (Quality: 60) | Good quality with ~10:1 compression |
| Protocol | UDP | Low latency prioritized over reliability |
| Port | 5001 | Dedicated video streaming port |
| Chunk Size | 60,000 bytes | Fits within UDP packet limits |
| Bandwidth | ~300 KB/s per stream | Calculated: 640×480×0.6÷30 FPS |

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT SIDE                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │   Webcam     │─────▶│ Video Capture│                │
│  │   (OpenCV)   │      │   Thread     │                │
│  └──────────────┘      └──────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │  Compression  │                │
│                        │  (JPEG Q=60)  │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ UDP Transmit  │                │
│                        │  (Port 5001)  │                │
│                        └───────┬───────┘                │
│                                │                         │
└────────────────────────────────┼─────────────────────────┘
                                 │
                                 │ Video Data
                                 │
┌────────────────────────────────▼─────────────────────────┐
│                    SERVER SIDE                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│                        ┌───────────────┐                │
│                        │  UDP Receive  │                │
│                        │  (Port 5001)  │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │  Frame Store  │                │
│                        │  {client_id:  │                │
│                        │   frame_data} │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │  Broadcast    │                │
│                        │  to All       │                │
│                        │  Clients      │                │
│                        └───────┬───────┘                │
│                                │                         │
└────────────────────────────────┼─────────────────────────┘
                                 │
                                 │ Broadcast
                                 │
┌────────────────────────────────▼─────────────────────────┐
│                CLIENT RECEIVE & DISPLAY                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│                        ┌───────────────┐                │
│                        │  UDP Receive  │                │
│                        │ (Multi-stream)│                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ Decompress    │                │
│                        │ (JPEG Decode) │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │  PyQt6 Grid   │                │
│                        │  Rendering    │                │
│                        └───────────────┘                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. Video Capture (Client Side)

**Location**: `src/client/client.py` - Method `capture_video()`

#### Initialization
```python
self.camera = cv2.VideoCapture(0)  # Open default webcam
self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)   # 640
self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT) # 480
self.camera.set(cv2.CAP_PROP_FPS, VIDEO_FPS)             # 30
```

#### Capture Loop
The capture thread runs continuously when video is enabled:

1. **Frame Acquisition**:
   ```python
   ret, frame = self.camera.read()
   ```
   - `ret`: Boolean indicating success
   - `frame`: NumPy array (480×640×3) in BGR format

2. **Compression**:
   ```python
   encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), VIDEO_QUALITY]
   result, encoded_frame = cv2.imencode('.jpg', frame, encode_param)
   ```
   - Converts BGR frame to JPEG
   - Quality parameter: 60 (range: 0-100)
   - Typical compression: 10:1 ratio
   - Output: Byte array (~10-20 KB per frame)

3. **Packetization**:
   ```python
   data = pickle.dumps(encoded_frame)
   message = struct.pack("Q", len(data)) + data
   ```
   - Serialize compressed frame using pickle
   - Prepend 8-byte header with payload size
   - Header format: `"Q"` = unsigned long long (8 bytes)

4. **Transmission**:
   ```python
   self.udp_socket.sendto(message, (self.server_address, SERVER_UDP_PORT))
   ```
   - Send via UDP to server
   - No acknowledgment required
   - Destination: Server IP, Port 5001

5. **Frame Rate Control**:
   ```python
   time.sleep(1.0 / VIDEO_FPS)  # Sleep ~33ms between frames
   ```
   - Ensures 30 FPS maximum
   - Prevents bandwidth saturation

#### Error Handling
- Camera failure: Logs error, stops capture thread
- Encoding failure: Skips frame, continues loop
- Socket errors: Attempts reconnection

---

### 2. Video Reception & Broadcasting (Server Side)

**Location**: `src/server/server.py` - Method `receive_video_streams()`

#### Reception Loop
```python
def receive_video_streams(self):
    while self.running:
        try:
            # Receive UDP packet
            data, addr = self.udp_socket.recvfrom(MAX_PACKET_SIZE)
            
            # Extract client ID from address mapping
            client_id = self.find_client_by_udp_address(addr)
            
            # Store frame in buffer
            with self.frames_lock:
                self.video_frames[client_id] = data
            
            # Broadcast to all other clients
            self.broadcast_video_frame(client_id, data)
            
        except Exception as e:
            print(f"Error receiving video: {e}")
```

#### Key Operations:

1. **Client Identification**:
   - Server maps UDP addresses to client IDs
   - First video packet from client registers UDP address
   - Subsequent packets identified via address lookup

2. **Frame Storage**:
   ```python
   self.video_frames[client_id] = data
   ```
   - Dictionary stores latest frame per client
   - Thread-safe access via `frames_lock`
   - Old frames automatically overwritten

3. **Broadcasting**:
   ```python
   def broadcast_video_frame(self, sender_id, frame_data):
       with self.clients_lock:
           for client_id, client_info in self.clients.items():
               if client_id != sender_id:  # Don't send back to sender
                   udp_addr = client_info['udp_address']
                   if udp_addr:
                       self.udp_socket.sendto(frame_data, udp_addr)
   ```
   - Iterates through all connected clients
   - Excludes original sender
   - Sends identical packet to each recipient

---

### 3. Video Reception & Display (Client Side)

**Location**: `src/client/client.py` - Method `receive_video_streams()`

#### Reception Thread
```python
def receive_video_streams(self):
    while self.connected:
        try:
            # Receive packet
            data, _ = self.udp_socket.recvfrom(MAX_PACKET_SIZE)
            
            # Parse header
            payload_size = struct.unpack("Q", data[:8])[0]
            frame_data = data[8:8+payload_size]
            
            # Deserialize
            encoded_frame = pickle.loads(frame_data)
            
            # Decompress
            frame = cv2.imdecode(encoded_frame, cv2.IMREAD_COLOR)
            
            # Identify sender (from packet metadata)
            sender_id = self.identify_sender(data)
            
            # Store in stream buffer
            with self.streams_lock:
                self.video_streams[sender_id] = frame
                self.video_stream_timestamps[sender_id] = time.time()
            
        except Exception as e:
            print(f"Error receiving video: {e}")
```

#### Display Update
Executed by GUI thread at regular intervals (QTimer):

```python
def update_video_displays(self):
    with self.streams_lock:
        for client_id, frame in self.video_streams.items():
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to QImage
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, 
                            QImage.Format.Format_RGB888)
            
            # Create QPixmap and display
            pixmap = QPixmap.fromImage(qt_image)
            
            # Scale to fit label
            scaled_pixmap = pixmap.scaled(
                self.video_labels[client_id].size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Update GUI
            self.video_labels[client_id].setPixmap(scaled_pixmap)
```

---

## Protocol Specification

### Packet Structure

#### Video Data Packet (UDP)
```
┌────────────────────────────────────────────────────────┐
│  Header (8 bytes)                                      │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Payload Size (unsigned 64-bit integer)           │ │
│  │ Format: "Q" in struct.pack()                     │ │
│  └──────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────┤
│  Payload (variable size, typically 10-20 KB)          │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Pickled Data containing:                         │ │
│  │   - Encoded JPEG frame (NumPy array)             │ │
│  │   - Metadata (implicit in pickle)                │ │
│  └──────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
Total Size: ~10-20 KB per frame
```

### Message Flow Sequence

```
Client A                Server                 Client B
   │                       │                       │
   │  1. Video Frame       │                       │
   │─────────────────────▶ │                       │
   │   (UDP, Port 5001)    │                       │
   │                       │                       │
   │                       │  2. Store Frame       │
   │                       │  video_frames[A]      │
   │                       │                       │
   │                       │  3. Broadcast         │
   │                       │─────────────────────▶ │
   │                       │   (UDP, Port 5001)    │
   │                       │                       │
   │                       │                       │  4. Decompress
   │                       │                       │     & Display
   │                       │                       │
   │  5. Video Frame       │                       │
   │ ◀─────────────────────│                       │
   │   (from Client B)     │  6. Frame from B      │
   │                       │ ◀─────────────────────│
   │                       │                       │
```

---

## Data Flow

### Complete Video Pipeline

```
┌────────────────────────────────────────────────────────────────┐
│ STEP 1: CAPTURE (Client A)                                     │
├────────────────────────────────────────────────────────────────┤
│ Webcam → OpenCV → NumPy Array (640×480×3 BGR)                 │
│ Size: ~921,600 bytes (uncompressed)                           │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 2: COMPRESSION                                            │
├────────────────────────────────────────────────────────────────┤
│ cv2.imencode('.jpg', frame, quality=60)                        │
│ Output: ~15 KB (10:1 compression ratio)                       │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 3: SERIALIZATION                                          │
├────────────────────────────────────────────────────────────────┤
│ pickle.dumps(encoded_frame)                                    │
│ Adds minimal overhead (~100 bytes)                            │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 4: PACKETIZATION                                          │
├────────────────────────────────────────────────────────────────┤
│ struct.pack("Q", size) + data                                  │
│ Total packet: ~15 KB                                           │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 5: TRANSMISSION (UDP)                                     │
├────────────────────────────────────────────────────────────────┤
│ Client A → Server (192.168.1.100:5001)                        │
│ No acknowledgment, fire-and-forget                            │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 6: SERVER PROCESSING                                      │
├────────────────────────────────────────────────────────────────┤
│ 1. Receive packet                                              │
│ 2. Identify sender (Client A)                                 │
│ 3. Store: video_frames[A] = packet                            │
│ 4. Broadcast to all except A                                  │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 7: CLIENT B RECEPTION                                     │
├────────────────────────────────────────────────────────────────┤
│ Server → Client B (UDP packet)                                │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 8: DEPACKETIZATION                                        │
├────────────────────────────────────────────────────────────────┤
│ Extract header: size = struct.unpack("Q", data[:8])           │
│ Extract payload: frame_data = data[8:8+size]                  │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 9: DESERIALIZATION                                        │
├────────────────────────────────────────────────────────────────┤
│ encoded_frame = pickle.loads(frame_data)                       │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 10: DECOMPRESSION                                         │
├────────────────────────────────────────────────────────────────┤
│ frame = cv2.imdecode(encoded_frame, cv2.IMREAD_COLOR)          │
│ Back to NumPy array (640×480×3)                                │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 11: GUI RENDERING                                         │
├────────────────────────────────────────────────────────────────┤
│ 1. Convert BGR → RGB                                           │
│ 2. Create QImage                                               │
│ 3. Create QPixmap                                              │
│ 4. Scale to fit QLabel                                         │
│ 5. Display in video grid                                       │
└────────────────────────────────────────────────────────────────┘
```

---

## Code Walkthrough

### Client-Side Video Capture Thread

```python
def capture_video(self):
    """
    Video capture thread - runs continuously while capturing is True
    Captures frames from webcam, compresses, and sends to server
    """
    while self.capturing:
        try:
            # Read frame from webcam
            ret, frame = self.camera.read()
            
            if not ret:
                print("Failed to capture frame")
                continue
            
            # Compress frame to JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), VIDEO_QUALITY]
            result, encoded_frame = cv2.imencode('.jpg', frame, encode_param)
            
            if not result:
                print("Failed to encode frame")
                continue
            
            # Serialize encoded frame
            data = pickle.dumps(encoded_frame)
            
            # Create packet with size header
            message = struct.pack("Q", len(data)) + data
            
            # Send via UDP
            try:
                self.udp_socket.sendto(
                    message, 
                    (self.server_address, SERVER_UDP_PORT)
                )
            except socket.error as e:
                print(f"Socket error sending video: {e}")
            
            # Control frame rate (30 FPS)
            time.sleep(1.0 / VIDEO_FPS)
            
        except Exception as e:
            print(f"Error in video capture: {e}")
            break
    
    # Cleanup when capturing stops
    if self.camera:
        self.camera.release()
        self.camera = None
```

### Server-Side Broadcasting Logic

```python
def receive_video_streams(self):
    """
    Receive video frames from clients and broadcast to all others
    Runs in dedicated thread on server
    """
    while self.running:
        try:
            # Receive UDP packet (blocking call)
            data, addr = self.udp_socket.recvfrom(MAX_PACKET_SIZE)
            
            # Find which client sent this frame
            client_id = None
            with self.clients_lock:
                for cid, info in self.clients.items():
                    if info.get('udp_address') == addr:
                        client_id = cid
                        break
                    elif info.get('udp_address') is None:
                        # First video packet from this client
                        info['udp_address'] = addr
                        client_id = cid
                        break
            
            if client_id is not None:
                # Store latest frame
                with self.frames_lock:
                    self.video_frames[client_id] = data
                
                # Broadcast to all other clients
                with self.clients_lock:
                    for cid, info in self.clients.items():
                        if cid != client_id:  # Don't send back to sender
                            udp_addr = info.get('udp_address')
                            if udp_addr:
                                try:
                                    self.udp_socket.sendto(data, udp_addr)
                                except socket.error:
                                    pass  # Client may have disconnected
                                    
        except Exception as e:
            if self.running:
                print(f"[{self.get_timestamp()}] Error in video streaming: {e}")
```

### Client-Side Video Display

```python
def update_video_displays(self):
    """
    Update video feed displays in the GUI
    Called periodically by QTimer (every 33ms for ~30 FPS)
    """
    with self.streams_lock:
        # Get list of active video streams
        active_streams = list(self.video_streams.keys())
        
        # Remove stale streams (no update in 3 seconds)
        current_time = time.time()
        for client_id in list(self.video_stream_timestamps.keys()):
            if current_time - self.video_stream_timestamps[client_id] > 3.0:
                if client_id in self.video_streams:
                    del self.video_streams[client_id]
                del self.video_stream_timestamps[client_id]
        
        # Update each video display
        for client_id, frame in self.video_streams.items():
            if frame is None:
                continue
            
            # Create QLabel if it doesn't exist
            if client_id not in self.video_labels:
                self.create_video_label(client_id)
            
            # Convert OpenCV BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Get frame dimensions
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
            
            # Scale to fit label while maintaining aspect ratio
            label = self.video_labels[client_id]
            scaled_pixmap = pixmap.scaled(
                label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Update label
            label.setPixmap(scaled_pixmap)
```

---

## Performance Optimization

### 1. **Bandwidth Optimization**

#### JPEG Compression
- **Quality Setting**: 60 (balance between quality and size)
- **Compression Ratio**: ~10:1
- **Raw frame**: 640×480×3 = 921,600 bytes
- **Compressed**: ~15 KB
- **Savings**: ~98% bandwidth reduction

#### Frame Rate Control
```python
time.sleep(1.0 / VIDEO_FPS)  # 30 FPS = ~33ms per frame
```
- Prevents overwhelming network
- CPU-friendly on both client and server

### 2. **CPU Optimization**

#### Thread Separation
- **Capture Thread**: Dedicated to camera I/O
- **Transmit Thread**: Minimal processing, just send
- **Receive Thread**: UDP reception only
- **GUI Thread**: Display updates only

Benefits:
- No blocking operations in GUI thread
- Camera capture never stalls
- Network I/O independent of processing

#### Frame Skipping Strategy
```python
if not ret:
    continue  # Skip failed frames, don't retry
```
- Failed captures don't block pipeline
- Missing frames acceptable in real-time video

### 3. **Memory Management**

#### Single Frame Storage
```python
self.video_frames[client_id] = data  # Overwrites old frame
```
- No frame buffering on server
- Latest frame only (reduces memory)
- Old frames garbage collected automatically

#### Client-Side Buffer
```python
self.video_streams = {}  # Dict, not queue
```
- Stores only latest frame per user
- No accumulation of old frames
- Memory usage: O(number of users), not O(frames)

### 4. **Network Optimization**

#### UDP Selection
- **Pros**: 
  - Low latency (~1-2ms)
  - No connection overhead
  - No retransmission delays
- **Cons**: 
  - Packet loss possible (acceptable for video)
  - No ordering guarantee (mitigated by overwriting)

#### Packet Size
```python
MAX_PACKET_SIZE = 65507  # Maximum UDP packet
CHUNK_SIZE = 60000       # Video chunk size
```
- Fits within single UDP datagram
- No fragmentation at application layer
- Some IP fragmentation may occur (handled by OS)

### 5. **GUI Optimization**

#### QTimer-Based Updates
```python
self.video_timer = QTimer()
self.video_timer.timeout.connect(self.update_video_displays)
self.video_timer.start(33)  # ~30 FPS
```
- Decouples reception from display
- Smooth rendering even with jitter
- Qt's event loop handles scheduling

#### Scaled Rendering
```python
scaled_pixmap = pixmap.scaled(
    label.size(),
    Qt.AspectRatioMode.KeepAspectRatio,
    Qt.TransformationMode.SmoothTransformation
)
```
- Downscales large feeds for display
- Maintains aspect ratio
- Smooth transformation for quality

---

## Troubleshooting

### Common Issues

#### 1. No Video Received

**Symptoms**:
- Black screen in video panel
- No error messages

**Diagnosis**:
```python
# Add debug logging in receive_video_streams()
print(f"Received video packet from {addr}, size: {len(data)}")
```

**Solutions**:
- Check firewall allows UDP port 5001
- Verify webcam not in use by another app
- Confirm `capturing` flag is True
- Check UDP socket properly bound

#### 2. Choppy Video

**Symptoms**:
- Video stutters or freezes
- Low effective frame rate

**Causes & Solutions**:

| Cause | Solution |
|-------|----------|
| Network congestion | Reduce VIDEO_QUALITY to 40-50 |
| CPU overload | Close other applications |
| Slow webcam | Check camera FPS settings |
| Wi-Fi latency | Switch to wired Ethernet |

#### 3. Video Lag/Delay

**Symptoms**:
- Noticeable delay (>200ms)

**Diagnosis**:
```python
# Measure round-trip time
send_time = time.time()
# ... after receiving frame back ...
latency = time.time() - send_time
print(f"Video latency: {latency*1000:.2f} ms")
```

**Solutions**:
- Expected latency: 33ms (1 frame) + network
- Acceptable: <100ms
- If >200ms: Check network switch/router

#### 4. High Bandwidth Usage

**Symptoms**:
- Network saturation
- Slow other applications

**Measurement**:
```python
# Calculate actual bandwidth
frames_sent = 0
start_time = time.time()
total_bytes = 0

# In capture loop:
total_bytes += len(message)
frames_sent += 1

# Every second:
if time.time() - start_time >= 1.0:
    bandwidth_mbps = (total_bytes * 8) / 1_000_000
    print(f"Video bandwidth: {bandwidth_mbps:.2f} Mbps")
```

**Optimization**:
- Reduce VIDEO_QUALITY (each 10 points ≈ 10% bandwidth)
- Lower resolution: 480×360 instead of 640×480
- Reduce FPS: 24 instead of 30

#### 5. Memory Leak

**Symptoms**:
- Memory usage grows over time
- Application becomes sluggish

**Diagnosis**:
```python
import tracemalloc
tracemalloc.start()

# ... run application ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

**Common Causes**:
- Not releasing camera: `camera.release()` when done
- Accumulating frames: Use dict, not list
- QPixmap not garbage collected: Keep references minimal

---

## Performance Metrics

### Expected Performance

| Metric | Value | Notes |
|--------|-------|-------|
| Frame Rate | 30 FPS | Configurable |
| Latency | 50-100 ms | Client → Server → Client |
| Bandwidth (upload) | ~300 KB/s | Per client |
| Bandwidth (download) | ~300 KB/s × (N-1) | N = number of users |
| CPU (client) | 5-10% | Varies by device |
| CPU (server) | 2-5% per client | On modern hardware |
| Memory (client) | ~50 MB | For video module only |
| Memory (server) | ~10 MB per client | Frame storage |

### Scalability

**Maximum Users**: 10 (configurable in config.py)

**Bandwidth Calculation**:
- 1 user: 300 KB/s upload, minimal download
- 5 users: 300 KB/s upload, 1.2 MB/s download
- 10 users: 300 KB/s upload, 2.7 MB/s download

**Server Requirements**:
- 10 users: ~50% CPU on dual-core processor
- Network: Gigabit Ethernet recommended
- RAM: ~500 MB for video frames

---

## Future Enhancements

1. **Adaptive Bitrate**: Adjust quality based on network conditions
2. **H.264 Encoding**: Better compression than JPEG
3. **P2P Mode**: Direct client-to-client for lower latency
4. **Recording**: Save video streams to disk
5. **Virtual Backgrounds**: Background blur/replacement
6. **Active Speaker Detection**: Highlight current speaker
7. **Bandwidth Limiting**: Cap maximum bitrate per user

---

**End of Video Module Documentation**
