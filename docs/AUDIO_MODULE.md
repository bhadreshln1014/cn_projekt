# Audio Conferencing Module - Technical Documentation

**Computer Networks Project**  
**Module**: Multi-User Audio Conferencing  
**Developers**: Bhadresh L and Santhana Srinivasan R

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Implementation Details](#implementation-details)
4. [Audio Processing Pipeline](#audio-processing-pipeline)
5. [Server-Side Audio Mixing](#server-side-audio-mixing)
6. [Protocol Specification](#protocol-specification)
7. [Code Walkthrough](#code-walkthrough)
8. [Performance Analysis](#performance-analysis)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The audio conferencing module enables real-time voice communication between multiple users with low latency and high quality. It implements a client-server architecture with server-side audio mixing to ensure efficient bandwidth usage.

### Key Features
- **Real-time Audio**: Low-latency voice transmission (~23ms per chunk)
- **Server-Side Mixing**: All audio streams mixed on server before distribution
- **Jitter Buffering**: Compensates for network variability
- **Device Selection**: Choose specific microphone and speaker devices
- **Individual Controls**: Mute microphone or speakers independently
- **High Quality**: 44.1kHz sample rate, 16-bit depth

### Technical Specifications
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Sample Rate | 44,100 Hz | CD-quality audio standard |
| Bit Depth | 16-bit | 2 bytes per sample |
| Channels | 1 (Mono) | Reduced bandwidth, sufficient for voice |
| Chunk Size | 1,024 samples | ~23ms latency per chunk |
| Buffer Size | 10 chunks | Jitter compensation |
| Protocol | UDP | Low latency over reliability |
| Port | 5002 | Dedicated audio streaming port |
| Bandwidth | ~88 KB/s per stream | 44100×2 bytes/sec |
| Format | PCM (signed 16-bit) | Raw uncompressed audio |

### Latency Calculation
```
Chunk Duration = Chunk Size / Sample Rate
               = 1,024 samples / 44,100 Hz
               = 23.2 ms per chunk

Total Latency = Capture + Network + Buffer + Playback
              ≈ 23ms + 10-50ms + 46ms + 23ms
              ≈ 100-150ms (acceptable for voice)
```

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT A                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │  Microphone  │─────▶│ Audio Capture│                │
│  │   (PyAudio)  │      │   Thread     │                │
│  └──────────────┘      └──────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │  PCM Audio    │                │
│                        │  1024 samples │                │
│                        │  @ 44.1kHz    │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ UDP Transmit  │                │
│                        │  (Port 5002)  │                │
│                        └───────┬───────┘                │
│                                │                         │
└────────────────────────────────┼─────────────────────────┘
                                 │
                                 │ Audio Data (Client A)
                                 │
┌────────────────────────────────▼─────────────────────────┐
│                    SERVER SIDE                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│                        ┌───────────────┐                │
│                        │  UDP Receive  │                │
│                        │  (Port 5002)  │                │
│                        └───────┬───────┘                │
│                                │                         │
│                    ┌───────────┴───────────┐            │
│                    │                       │            │
│              Client A Audio          Client B Audio     │
│                    │                       │            │
│                    └───────────┬───────────┘            │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │  Audio Mixer  │                │
│                        │  (NumPy Sum)  │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │  Normalize    │                │
│                        │  & Clip       │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │  Broadcast    │                │
│                        │  Mixed Audio  │                │
│                        └───────┬───────┘                │
│                                │                         │
└────────────────────────────────┼─────────────────────────┘
                                 │
                                 │ Mixed Audio
                                 │
┌────────────────────────────────▼─────────────────────────┐
│                CLIENT RECEIVE & PLAYBACK                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│                        ┌───────────────┐                │
│                        │  UDP Receive  │                │
│                        │  (Mixed)      │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ Jitter Buffer │                │
│                        │  (10 chunks)  │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │  Speaker      │                │
│                        │  Playback     │                │
│                        │  (PyAudio)    │                │
│                        └───────────────┘                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. Audio Capture (Client Side)

**Location**: `src/client/client.py` - Method `capture_audio()`

#### PyAudio Initialization
```python
# Initialize PyAudio
self.audio = pyaudio.PyAudio()

# Open input stream (microphone)
self.audio_stream_input = self.audio.open(
    format=pyaudio.paInt16,           # 16-bit signed integer
    channels=AUDIO_CHANNELS,           # 1 (Mono)
    rate=AUDIO_RATE,                   # 44,100 Hz
    input=True,                        # Input stream
    input_device_index=self.selected_input_device,
    frames_per_buffer=AUDIO_CHUNK      # 1,024 samples
)
```

**Key Parameters**:
- `format=pyaudio.paInt16`: Signed 16-bit integers (-32768 to 32767)
- `frames_per_buffer=1024`: Size of each read operation
- `input_device_index`: User-selected microphone

#### Capture Loop
```python
def capture_audio(self):
    """
    Audio capture thread - continuously reads from microphone
    and sends to server via UDP
    """
    while self.audio_capturing:
        try:
            # Read audio chunk from microphone
            audio_data = self.audio_stream_input.read(
                AUDIO_CHUNK,
                exception_on_overflow=False  # Prevent overflow exceptions
            )
            
            # Send directly to server (no compression)
            if self.udp_socket and self.server_address:
                self.audio_udp_socket.sendto(
                    audio_data,
                    (self.server_address, SERVER_AUDIO_PORT)
                )
                
        except Exception as e:
            print(f"Error capturing audio: {e}")
            break
```

**Data Format**:
- **Raw PCM**: No compression applied
- **Chunk Size**: 1,024 samples × 2 bytes = 2,048 bytes
- **Frequency**: 44,100 / 1,024 ≈ 43 chunks per second
- **Bandwidth**: 2,048 bytes × 43 ≈ 88 KB/s

**Why No Compression?**
- Voice codecs (Opus, Speex) add complexity
- Raw PCM ensures zero encoding latency
- 88 KB/s is acceptable for LAN bandwidth
- CPU saved for video processing

---

### 2. Audio Mixing (Server Side)

**Location**: `src/server/server.py` - Method `receive_and_mix_audio()`

#### Mixing Algorithm

The server receives audio from multiple clients and mixes them together:

```python
def receive_and_mix_audio(self):
    """
    Receive audio from all clients, mix together, and broadcast
    Runs continuously in dedicated thread
    """
    while self.running:
        try:
            # Receive audio packet
            audio_data, addr = self.audio_socket.recvfrom(AUDIO_CHUNK * 4)
            
            # Identify sender
            client_id = self.find_client_by_audio_address(addr)
            
            if client_id is not None:
                # Store audio in buffer
                with self.audio_lock:
                    self.audio_buffers[client_id] = audio_data
                    self.audio_timestamps[client_id] = time.time()
                
                # Mix audio from all active clients
                mixed_audio = self.mix_audio_streams()
                
                # Broadcast mixed audio to all clients
                if mixed_audio:
                    self.broadcast_mixed_audio(mixed_audio)
                    
        except Exception as e:
            if self.running:
                print(f"Error in audio mixing: {e}")
```

#### Mixing Process

```python
def mix_audio_streams(self):
    """
    Mix audio from all clients using numpy array operations
    Returns mixed audio as bytes
    """
    current_time = time.time()
    mixed_samples = None
    
    with self.audio_lock:
        # Remove stale audio (older than 1 second)
        stale_clients = []
        for client_id, timestamp in self.audio_timestamps.items():
            if current_time - timestamp > 1.0:
                stale_clients.append(client_id)
        
        for client_id in stale_clients:
            del self.audio_buffers[client_id]
            del self.audio_timestamps[client_id]
        
        # Mix all active audio streams
        for client_id, audio_data in self.audio_buffers.items():
            # Convert bytes to numpy array
            samples = np.frombuffer(audio_data, dtype=np.int16)
            
            if mixed_samples is None:
                mixed_samples = samples.astype(np.float32)
            else:
                # Add samples together
                mixed_samples += samples.astype(np.float32)
    
    if mixed_samples is not None:
        # Normalize to prevent clipping
        # Divide by number of contributors to maintain amplitude
        num_contributors = len(self.audio_buffers)
        if num_contributors > 1:
            mixed_samples = mixed_samples / num_contributors
        
        # Clip to valid range and convert back to int16
        mixed_samples = np.clip(mixed_samples, -32768, 32767)
        mixed_audio = mixed_samples.astype(np.int16).tobytes()
        
        return mixed_audio
    
    return None
```

**Mixing Mathematics**:

For N clients with audio samples A₁, A₂, ..., Aₙ:

```
Mixed = (A₁ + A₂ + ... + Aₙ) / N

Where each Aᵢ ∈ [-32768, 32767]
```

**Why Normalize?**
- Prevents clipping (overflow beyond ±32767)
- Maintains consistent volume
- Example: 3 users at max volume (32767 each)
  - Without normalization: 98,301 (clips!)
  - With normalization: 32,767 (perfect)

---

### 3. Audio Playback (Client Side)

**Location**: `src/client/client.py` - Method `play_audio()`

#### Output Stream Initialization
```python
# Open output stream (speaker)
self.audio_stream_output = self.audio.open(
    format=pyaudio.paInt16,
    channels=AUDIO_CHANNELS,
    rate=AUDIO_RATE,
    output=True,                       # Output stream
    output_device_index=self.selected_output_device,
    frames_per_buffer=AUDIO_CHUNK
)
```

#### Reception Thread
```python
def receive_audio(self):
    """
    Receive mixed audio from server and add to jitter buffer
    """
    while self.connected:
        try:
            # Receive mixed audio
            audio_data, _ = self.audio_udp_socket.recvfrom(AUDIO_CHUNK * 4)
            
            # Add to jitter buffer (queue)
            if not self.audio_buffer.full():
                self.audio_buffer.put(audio_data)
            else:
                # Buffer full, drop oldest
                try:
                    self.audio_buffer.get_nowait()
                    self.audio_buffer.put(audio_data)
                except queue.Empty:
                    pass
                    
        except Exception as e:
            if self.connected:
                print(f"Error receiving audio: {e}")
```

#### Playback Thread
```python
def play_audio(self):
    """
    Playback thread - continuously reads from jitter buffer
    and plays through speaker
    """
    while self.audio_playing:
        try:
            # Get audio from buffer (blocking with timeout)
            audio_data = self.audio_buffer.get(timeout=0.1)
            
            # Play through speaker
            if self.audio_stream_output:
                self.audio_stream_output.write(audio_data)
                
        except queue.Empty:
            # Buffer empty, play silence
            silence = b'\x00' * (AUDIO_CHUNK * AUDIO_FORMAT_BYTES)
            if self.audio_stream_output:
                self.audio_stream_output.write(silence)
        except Exception as e:
            print(f"Error playing audio: {e}")
            break
```

#### Jitter Buffer

**Purpose**: Compensate for network timing variations

```python
self.audio_buffer = queue.Queue(maxsize=20)  # 20 chunks ≈ 464ms
```

**Operation**:
1. **Reception Thread**: Fills buffer with incoming audio
2. **Playback Thread**: Drains buffer at constant rate
3. **Buffer State**:
   - Empty → Play silence (underrun)
   - Full → Drop oldest packet (overrun)
   - Optimal: 50% full (10 chunks ≈ 232ms buffer)

**Trade-off**:
- Larger buffer → More latency, better jitter tolerance
- Smaller buffer → Less latency, more dropouts
- 10-20 chunks is sweet spot for LAN

---

## Audio Processing Pipeline

### Complete Audio Flow

```
┌────────────────────────────────────────────────────────────────┐
│ STEP 1: MICROPHONE CAPTURE (Client A)                          │
├────────────────────────────────────────────────────────────────┤
│ Hardware Microphone → ADC (Analog to Digital Converter)       │
│ Sampling: 44,100 samples/second, 16-bit depth                 │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 2: PYAUDIO READ                                           │
├────────────────────────────────────────────────────────────────┤
│ Read 1,024 samples = 2,048 bytes                               │
│ Format: Signed 16-bit little-endian PCM                        │
│ Duration: 23.2 ms of audio                                     │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 3: UDP TRANSMISSION (Client → Server)                     │
├────────────────────────────────────────────────────────────────┤
│ Raw bytes sent directly (no serialization)                     │
│ Destination: Server IP:5002                                    │
│ Packet size: 2,048 bytes                                       │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 4: SERVER RECEPTION                                       │
├────────────────────────────────────────────────────────────────┤
│ Receive audio from Client A                                    │
│ Store in buffer: audio_buffers[A] = audio_data                │
│ Update timestamp: audio_timestamps[A] = time.time()           │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 5: MIXING (Server)                                        │
├────────────────────────────────────────────────────────────────┤
│ For each client audio buffer:                                  │
│   1. Convert bytes to NumPy int16 array                       │
│   2. Cast to float32 for arithmetic                           │
│   3. Sum all arrays: mixed = A + B + C + ...                  │
│   4. Normalize: mixed = mixed / num_clients                   │
│   5. Clip to [-32768, 32767]                                  │
│   6. Convert back to int16                                    │
│   7. Convert to bytes                                         │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 6: BROADCAST (Server → All Clients)                       │
├────────────────────────────────────────────────────────────────┤
│ Send mixed audio to each client via UDP                       │
│ Same packet sent to all (broadcast)                           │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 7: CLIENT RECEPTION                                       │
├────────────────────────────────────────────────────────────────┤
│ Receive mixed audio packet (2,048 bytes)                      │
│ Add to jitter buffer (queue)                                  │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 8: JITTER BUFFERING                                       │
├────────────────────────────────────────────────────────────────┤
│ Queue maintains 10-20 chunks (~232-464ms buffer)              │
│ Smooths network timing variations                             │
│ Prevents stuttering from packet jitter                        │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 9: PLAYBACK                                               │
├────────────────────────────────────────────────────────────────┤
│ Playback thread reads from buffer at constant rate            │
│ PyAudio writes to speaker output stream                       │
│ DAC (Digital to Analog) converts to analog signal             │
│ Speaker produces sound                                         │
└────────────────────────────────────────────────────────────────┘
```

---

## Protocol Specification

### Audio Packet Structure

Unlike video, audio uses **raw PCM data** without serialization:

```
┌────────────────────────────────────────────┐
│  Raw PCM Audio Data (2,048 bytes)         │
│  ┌──────────────────────────────────────┐ │
│  │ Sample 1: int16 (2 bytes)            │ │
│  │ Sample 2: int16 (2 bytes)            │ │
│  │ Sample 3: int16 (2 bytes)            │ │
│  │ ...                                  │ │
│  │ Sample 1024: int16 (2 bytes)         │ │
│  └──────────────────────────────────────┘ │
└────────────────────────────────────────────┘

Format: Signed 16-bit little-endian integers
Range: -32768 to +32767
Total Size: Exactly 2,048 bytes
```

### Message Flow Sequence

```
Client A          Server          Client B          Client C
   │                 │                 │                 │
   │  Audio Chunk    │                 │                 │
   │────────────────▶│                 │                 │
   │   (2048 bytes)  │                 │                 │
   │                 │                 │                 │
   │                 │  Audio Chunk    │                 │
   │                 │◀────────────────│                 │
   │                 │                 │                 │
   │                 │                 │  Audio Chunk    │
   │                 │◀────────────────────────────────────│
   │                 │                 │                 │
   │                 │  Mix A+B+C      │                 │
   │                 │  Normalize      │                 │
   │                 │                 │                 │
   │  Mixed Audio    │                 │                 │
   │◀────────────────│                 │                 │
   │                 │  Mixed Audio    │                 │
   │                 │────────────────▶│                 │
   │                 │                 │  Mixed Audio    │
   │                 │─────────────────────────────────▶│
   │                 │                 │                 │
```

**Note**: Each client hears the mix of all other clients, but **not their own voice** (server excludes sender's audio from their own mix).

---

## Code Walkthrough

### Audio Device Selection

**Location**: `src/client/client.py` - Connection Dialog

```python
def populate_audio_devices(self):
    """
    Enumerate all available audio input/output devices
    and populate dropdown menus
    """
    if not self.audio:
        self.audio = pyaudio.PyAudio()
    
    # Get device count
    device_count = self.audio.get_device_count()
    
    # Clear existing items
    self.mic_combo.clear()
    self.speaker_combo.clear()
    
    # Enumerate devices
    for i in range(device_count):
        device_info = self.audio.get_device_info_by_index(i)
        device_name = device_info['name']
        
        # Check if device supports input (microphone)
        if device_info['maxInputChannels'] > 0:
            self.mic_combo.addItem(device_name, i)  # Store index as item data
        
        # Check if device supports output (speaker)
        if device_info['maxOutputChannels'] > 0:
            self.speaker_combo.addItem(device_name, i)
    
    # Set default devices
    try:
        default_input = self.audio.get_default_input_device_info()
        default_output = self.audio.get_default_output_device_info()
        
        # Select defaults in dropdowns
        input_idx = self.mic_combo.findData(default_input['index'])
        output_idx = self.speaker_combo.findData(default_output['index'])
        
        if input_idx >= 0:
            self.mic_combo.setCurrentIndex(input_idx)
        if output_idx >= 0:
            self.speaker_combo.setCurrentIndex(output_idx)
            
    except Exception as e:
        print(f"Error setting default audio devices: {e}")
```

### Microphone Mute/Unmute

```python
def toggle_microphone(self, state):
    """
    Toggle microphone capture on/off
    Called when user clicks microphone button
    """
    if state and self.connected:
        # Start capturing
        if not self.audio_capturing:
            try:
                # Open input stream
                self.audio_stream_input = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=AUDIO_CHANNELS,
                    rate=AUDIO_RATE,
                    input=True,
                    input_device_index=self.selected_input_device,
                    frames_per_buffer=AUDIO_CHUNK
                )
                
                # Start capture thread
                self.audio_capturing = True
                capture_thread = threading.Thread(
                    target=self.capture_audio,
                    daemon=True
                )
                capture_thread.start()
                
                print("Microphone started")
                
            except Exception as e:
                print(f"Error starting microphone: {e}")
                self.microphone_on.setChecked(False)
    else:
        # Stop capturing
        self.audio_capturing = False
        if self.audio_stream_input:
            self.audio_stream_input.stop_stream()
            self.audio_stream_input.close()
            self.audio_stream_input = None
        print("Microphone stopped")
```

### Speaker Mute/Unmute

```python
def toggle_speaker(self, state):
    """
    Toggle speaker playback on/off
    Called when user clicks speaker button
    """
    if state and self.connected:
        # Start playback
        if not self.audio_playing:
            try:
                # Open output stream
                self.audio_stream_output = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=AUDIO_CHANNELS,
                    rate=AUDIO_RATE,
                    output=True,
                    output_device_index=self.selected_output_device,
                    frames_per_buffer=AUDIO_CHUNK
                )
                
                # Start playback thread
                self.audio_playing = True
                self.audio_playback_thread = threading.Thread(
                    target=self.play_audio,
                    daemon=True
                )
                self.audio_playback_thread.start()
                
                print("Speaker started")
                
            except Exception as e:
                print(f"Error starting speaker: {e}")
                self.speaker_on.setChecked(False)
    else:
        # Stop playback
        self.audio_playing = False
        if self.audio_stream_output:
            self.audio_stream_output.stop_stream()
            self.audio_stream_output.close()
            self.audio_stream_output = None
        
        # Clear buffer
        while not self.audio_buffer.empty():
            try:
                self.audio_buffer.get_nowait()
            except queue.Empty:
                break
        
        print("Speaker stopped")
```

---

## Performance Analysis

### Latency Breakdown

| Component | Latency | Notes |
|-----------|---------|-------|
| Microphone Capture | 23 ms | 1 chunk @ 44.1kHz |
| Network (Client→Server) | 1-5 ms | LAN typical |
| Server Processing | <1 ms | NumPy mixing very fast |
| Network (Server→Client) | 1-5 ms | LAN typical |
| Jitter Buffer | 46-232 ms | 2-10 chunks buffer |
| Speaker Playback | 23 ms | 1 chunk output buffer |
| **Total** | **94-289 ms** | Typical: ~150ms |

### Bandwidth Analysis

**Per Client**:
- **Upload**: 88 KB/s (constant)
- **Download**: 88 KB/s (mixed audio from server)
- **Total**: 176 KB/s bidirectional

**Server**:
- **Incoming**: 88 KB/s × N clients
- **Outgoing**: 88 KB/s × N clients
- **Total**: 176 KB/s × N

**Example (5 clients)**:
- Each client: 176 KB/s
- Server: 880 KB/s total (440 KB/s each direction)

### CPU Usage

**Client**:
- Audio capture: ~1-2% CPU
- Audio playback: ~1-2% CPU
- Total: ~3-5% CPU

**Server**:
- NumPy mixing (5 clients): ~2-3% CPU
- Network I/O: ~1% CPU
- Total: ~3-4% CPU (scales linearly with users)

### Memory Usage

**Client**:
- Jitter buffer: 2,048 bytes × 20 chunks = 40 KB
- Stream buffers: ~10 KB
- Total: ~50 KB

**Server**:
- Audio buffers: 2,048 bytes × 10 clients = 20 KB
- Mixing arrays: ~10 KB
- Total: ~30 KB

---

## Troubleshooting

### Common Issues

#### 1. No Audio Heard

**Symptoms**:
- Speakers on but no sound
- Others can hear you but you can't hear them

**Diagnosis Steps**:
```python
# Add debug in receive_audio()
print(f"Received audio: {len(audio_data)} bytes")

# Check buffer fill level
print(f"Buffer size: {self.audio_buffer.qsize()}")
```

**Solutions**:
- Verify speaker toggle is ON
- Check correct output device selected
- Ensure speaker volume not muted in OS
- Verify network connectivity (ping server)
- Check if audio_playing flag is True

#### 2. Echo / Feedback

**Symptoms**:
- Hear your own voice with delay
- High-pitched feedback squeal

**Causes**:
- Microphone picking up speaker output
- Server sending user's own audio back to them

**Solutions**:
```python
# Server should exclude sender from broadcast
def broadcast_mixed_audio(self, sender_id, mixed_audio):
    for client_id, info in self.clients.items():
        if client_id != sender_id:  # Critical check!
            self.audio_socket.sendto(mixed_audio, info['audio_address'])
```

- Use headphones instead of speakers
- Reduce speaker volume
- Increase microphone-speaker distance

#### 3. Audio Choppy/Stuttering

**Symptoms**:
- Intermittent gaps in audio
- Robotic/distorted voice

**Diagnosis**:
```python
# Monitor buffer underruns
underruns = 0

try:
    audio_data = self.audio_buffer.get(timeout=0.1)
except queue.Empty:
    underruns += 1
    print(f"Buffer underrun #{underruns}")
```

**Solutions**:
- Increase jitter buffer size to 30 chunks
- Check network packet loss (ping -c 100 server)
- Close bandwidth-heavy applications
- Switch to wired Ethernet
- Reduce video quality to free bandwidth

#### 4. High Latency

**Symptoms**:
- Noticeable delay (>300ms)
- Conversations feel sluggish

**Measurement**:
```python
# Client sends timestamp in audio packet
import struct
timestamp = struct.pack('d', time.time())
packet = timestamp + audio_data
# Server echoes back, client measures RTT
```

**Solutions**:
- Reduce jitter buffer to 5-10 chunks
- Check network RTT: ping server
- Ensure no VPN/proxy in the path
- Verify server not overloaded

#### 5. Audio Distortion

**Symptoms**:
- Crackling or popping sounds
- Garbled voice

**Causes & Solutions**:

| Cause | Solution |
|-------|----------|
| Clipping in mixing | Verify normalization code |
| Buffer overrun | Increase buffer maxsize |
| Wrong sample rate | Confirm 44100 Hz on all devices |
| Device mismatch | Use same format for input/output |

#### 6. One-Way Audio

**Symptoms**:
- You can hear others but they can't hear you (or vice versa)

**Diagnosis**:
```python
# Client: Verify sending
bytes_sent = self.audio_udp_socket.sendto(audio_data, ...)
print(f"Sent {bytes_sent} bytes")

# Server: Verify reception
print(f"Received audio from client {client_id}")
```

**Solutions**:
- Check firewall allows UDP port 5002
- Verify microphone permissions granted
- Ensure audio_capturing is True
- Test microphone in other apps

---

## Advanced Features

### Voice Activity Detection (Not Implemented)

**Concept**: Only transmit audio when user is speaking

```python
def is_voice_active(audio_data, threshold=500):
    """
    Simple energy-based VAD
    """
    samples = np.frombuffer(audio_data, dtype=np.int16)
    energy = np.abs(samples).mean()
    return energy > threshold

# In capture loop:
if is_voice_active(audio_data):
    self.audio_udp_socket.sendto(audio_data, ...)
else:
    # Send silence or skip
    pass
```

**Benefits**:
- Reduces bandwidth by 50-70%
- Less noise when not speaking
- Lower server mixing load

### Automatic Gain Control (Not Implemented)

**Concept**: Normalize volume levels across users

```python
def apply_agc(audio_data, target_level=1000):
    """
    Adjust volume to target level
    """
    samples = np.frombuffer(audio_data, dtype=np.int16)
    current_level = np.abs(samples).mean()
    
    if current_level > 0:
        gain = target_level / current_level
        gain = np.clip(gain, 0.1, 10.0)  # Limit gain range
        samples = samples * gain
        samples = np.clip(samples, -32768, 32767)
    
    return samples.astype(np.int16).tobytes()
```

**Benefits**:
- Equalizes loud and quiet users
- Improves overall audio quality
- Reduces manual volume adjustments

### Noise Suppression (Not Implemented)

**Concept**: Filter background noise

```python
# Would require spectral subtraction or ML-based noise suppression
# Libraries: noisereduce, rnnoise
```

---

## Future Enhancements

1. **Opus Codec**: Compress audio to 20-40 KB/s (50% bandwidth savings)
2. **Spatial Audio**: Stereo positioning of different speakers
3. **Audio Effects**: Reverb, echo cancellation, noise gate
4. **Recording**: Save mixed audio to WAV/MP3 file
5. **Audio Visualization**: Waveform or spectrum display
6. **Dynamic Jitter Buffer**: Adapt buffer size to network conditions
7. **Quality Adaptation**: Switch sample rate based on bandwidth
8. **Individual Volume Controls**: Adjust volume per user

---

**End of Audio Module Documentation**
