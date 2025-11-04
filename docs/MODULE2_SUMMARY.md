# Module 2: Multi-User Audio Conferencing

## Overview
Module 2 implements real-time multi-user audio conferencing with server-side mixing, enabling multiple clients to communicate through voice simultaneously.

## Architecture

### Audio Flow
```
Client 1 Microphone → UDP Audio Packet → Server
Client 2 Microphone → UDP Audio Packet → Server
Client N Microphone → UDP Audio Packet → Server
                                ↓
                        Server Audio Mixer
                    (NumPy-based averaging)
                                ↓
                        Mixed Audio Stream
                                ↓
            ┌───────────────────┼───────────────────┐
            ↓                   ↓                   ↓
    Client 1 Speakers   Client 2 Speakers   Client N Speakers
```

### Network Protocol
- **Transport**: UDP (for low-latency streaming)
- **Port**: 5002 (SERVER_AUDIO_PORT)
- **Packet Format**: `[client_id (variable length)] + [audio_data]`
- **Audio Format**: 16-bit PCM, mono, 44100 Hz sample rate
- **Chunk Size**: 1024 samples (~23ms at 44100 Hz)

## Technical Specifications

### Audio Configuration (config.py)
```python
SERVER_AUDIO_PORT = 5002        # UDP port for audio streaming
AUDIO_RATE = 44100              # Sample rate (Hz)
AUDIO_CHUNK = 1024              # Samples per chunk
AUDIO_CHANNELS = 1              # Mono audio
AUDIO_FORMAT = pyaudio.paInt16  # 16-bit PCM
```

### Server-Side Implementation

#### Audio Mixing Algorithm
The server employs a NumPy-based averaging algorithm to mix audio streams:

1. **Collection Phase**: Receive audio packets from all clients within a time window
2. **Buffering**: Store recent audio chunks in `audio_buffers` dictionary
3. **Mixing Phase**:
   ```python
   # Convert all audio chunks to NumPy arrays
   audio_arrays = [np.frombuffer(data, dtype=np.int16) for data in chunks]
   
   # Average all streams element-wise
   mixed = np.mean(audio_arrays, axis=0).astype(np.int16)
   
   # Convert back to bytes
   mixed_bytes = mixed.tobytes()
   ```
4. **Broadcasting**: Send mixed audio to all connected clients

#### Key Methods
- **`receive_and_mix_audio()`**: Thread that receives audio packets from clients
  - Extracts client_id from packet
  - Stores audio data in buffer
  - Validates packet integrity

- **`mix_and_broadcast_audio()`**: Thread that performs mixing and broadcasting
  - Runs every ~23ms (AUDIO_CHUNK / AUDIO_RATE)
  - Mixes all buffered audio chunks
  - Broadcasts to all clients via UDP
  - Clears buffers after broadcast

### Client-Side Implementation

#### Audio Capture
**Method**: `capture_and_send_audio()`
```python
# Open microphone stream with PyAudio
stream = pyaudio.open(format=AUDIO_FORMAT,
                      channels=AUDIO_CHANNELS,
                      rate=AUDIO_RATE,
                      input=True,
                      frames_per_buffer=AUDIO_CHUNK)

# Capture loop
while self.audio_capturing:
    audio_data = stream.read(AUDIO_CHUNK)
    packet = self.client_id.encode() + audio_data
    self.audio_udp_socket.sendto(packet, (self.server_ip, SERVER_AUDIO_PORT))
```

#### Audio Playback
**Method**: `receive_audio_stream()`
```python
# Open speaker stream with PyAudio
stream = pyaudio.open(format=AUDIO_FORMAT,
                      channels=AUDIO_CHANNELS,
                      rate=AUDIO_RATE,
                      output=True,
                      frames_per_buffer=AUDIO_CHUNK)

# Playback loop
while self.audio_playing:
    data, addr = self.audio_udp_socket.recvfrom(65535)
    stream.write(data)
```

#### GUI Controls
Three audio control buttons with emoji indicators:
- **🎥 Camera**: Toggle video capture on/off
- **🎤 Microphone**: Toggle audio capture (mute/unmute)
- **🔊 Speaker**: Toggle audio playback (deafen/undeafen)

Toggle states are visually indicated:
- Active: 🎤 Microphone (green background)
- Inactive: 🎤 Microphone (red background)

## Threading Model

### Server Threads
1. **TCP Control Thread**: Handles client connections/disconnections
2. **UDP Video Receiver**: Receives video frames from clients
3. **UDP Video Broadcaster**: Broadcasts video to all clients
4. **UDP Audio Receiver**: `receive_and_mix_audio()` - Receives audio packets
5. **Audio Mixer/Broadcaster**: `mix_and_broadcast_audio()` - Mixes and broadcasts audio

### Client Threads
1. **TCP Receiver**: Receives control messages (user list updates)
2. **UDP Video Receiver**: Receives video frames from server
3. **UDP Video Sender**: `capture_and_send()` - Captures and sends video
4. **UDP Audio Sender**: `capture_and_send_audio()` - Captures and sends audio
5. **UDP Audio Receiver**: `receive_audio_stream()` - Receives and plays mixed audio
6. **GUI Thread**: Main thread running Tkinter event loop

## Resource Management

### Initialization
```python
# PyAudio instance
self.pyaudio_instance = pyaudio.PyAudio()

# Audio streams
self.audio_stream_input = None   # Microphone
self.audio_stream_output = None  # Speakers

# UDP socket
self.audio_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
```

### Cleanup (disconnect)
```python
# Stop audio streams
if self.audio_stream_input:
    self.audio_stream_input.stop_stream()
    self.audio_stream_input.close()

if self.audio_stream_output:
    self.audio_stream_output.stop_stream()
    self.audio_stream_output.close()

# Terminate PyAudio
if self.pyaudio_instance:
    self.pyaudio_instance.terminate()

# Close socket
if self.audio_udp_socket:
    self.audio_udp_socket.close()
```

## Performance Characteristics

### Latency
- **Network Latency**: ~1-5ms (LAN)
- **Capture Latency**: ~23ms (AUDIO_CHUNK / AUDIO_RATE)
- **Processing Latency**: ~1-2ms (NumPy mixing)
- **Total End-to-End**: ~25-30ms

### Bandwidth Usage
- **Per Client Upload**: ~88 KB/s (44100 Hz × 2 bytes × 1 channel)
- **Per Client Download**: ~88 KB/s (mixed audio stream)
- **Server Bandwidth**: ~88 KB/s upload + (88 KB/s × N clients download)

### CPU Usage
- **Client**: Low (PyAudio handles most audio processing)
- **Server**: Moderate (NumPy mixing is efficient, scales with client count)

## Audio Quality

### Mixing Quality
The averaging algorithm maintains audio quality while preventing clipping:
- **No Amplification**: Output volume = average of inputs
- **No Clipping**: Values remain within int16 range (-32768 to 32767)
- **Trade-off**: Volume decreases with more simultaneous speakers
- **Solution**: Users can increase speaker/microphone volume as needed

### Codec
- **Format**: Uncompressed PCM (pulse-code modulation)
- **Bit Depth**: 16-bit (CD quality)
- **Sample Rate**: 44100 Hz (CD quality)
- **Channels**: Mono (reduces bandwidth by 50% vs stereo)

## Error Handling

### Network Errors
- UDP packet loss is tolerated (minor audio glitches)
- Client disconnection detected via TCP control channel
- Stale audio buffers cleared periodically

### Hardware Errors
- PyAudio exceptions caught during stream operations
- Graceful degradation if microphone/speakers unavailable
- Toggle buttons allow recovery from hardware failures

## Testing Checklist

### Basic Functionality
- [ ] Client can capture audio from microphone
- [ ] Server receives audio packets from client
- [ ] Server mixes multiple audio streams
- [ ] Client receives and plays mixed audio
- [ ] Audio is synchronized with video

### UI Controls
- [ ] Microphone toggle stops/starts audio capture
- [ ] Speaker toggle stops/starts audio playback
- [ ] Visual feedback (button colors) updates correctly
- [ ] Controls work independently of each other

### Multi-User Scenarios
- [ ] 2 clients: Both can hear each other
- [ ] 3+ clients: All can hear mixed audio from all others
- [ ] One client muted: Others don't hear that client
- [ ] One client deafened: That client doesn't hear others
- [ ] Client disconnect: Audio stream stops cleanly

### Performance
- [ ] Latency under 50ms on LAN
- [ ] No audio stuttering with 4+ clients
- [ ] CPU usage reasonable on both client and server
- [ ] Network bandwidth within expected range

### Edge Cases
- [ ] Client with no microphone (capture fails gracefully)
- [ ] Client with no speakers (playback fails gracefully)
- [ ] Rapid toggle on/off (no resource leaks)
- [ ] All clients muted (server sends silence)
- [ ] Server restart (clients detect and handle disconnection)

## Known Limitations

1. **Volume Scaling**: With many simultaneous speakers, average volume decreases
2. **No Echo Cancellation**: Clients may need headphones to prevent feedback
3. **No Noise Suppression**: Background noise is transmitted
4. **No Compression**: Uses full 88 KB/s per client (could use Opus/Speex for reduction)
5. **Mono Only**: Stereo would double bandwidth

## Future Enhancements

### Potential Improvements
1. **Automatic Gain Control (AGC)**: Normalize volume levels
2. **Echo Cancellation**: Allow speaker use without headphones
3. **Noise Suppression**: Filter background noise
4. **Audio Compression**: Use Opus codec for 10x bandwidth reduction
5. **Stereo Support**: Enhance audio quality with stereo
6. **VAD (Voice Activity Detection)**: Only transmit when speaking
7. **Individual Volume Control**: Per-user volume sliders
8. **Audio Recording**: Save conference audio to file

### Advanced Features
1. **Spatial Audio**: 3D positioning of audio sources
2. **Audio Effects**: Reverb, equalization, filters
3. **Music Sharing**: High-quality audio for music playback
4. **Transcription**: Real-time speech-to-text
5. **Translation**: Multi-language support

## Integration with Module 1

Module 2 seamlessly integrates with the existing video conferencing system:
- **Same Server Instance**: Both video and audio use the same VideoConferenceServer
- **Same Client Instance**: Both video and audio use the same VideoConferenceClient
- **Independent Controls**: Video and audio can be toggled independently
- **Synchronized GUI**: All controls in one interface
- **Unified Resource Cleanup**: Both systems cleaned up in disconnect()

## Conclusion

Module 2 provides robust, low-latency audio conferencing that complements the video system from Module 1. The server-side mixing approach ensures scalability and reduces client-side processing requirements. The implementation prioritizes simplicity and reliability over advanced features, making it suitable for LAN-based conferencing applications.

---

**Next Steps**: Test the complete system with multiple clients and proceed to Module 3 implementation (likely text chat, file transfer, or screen sharing).
