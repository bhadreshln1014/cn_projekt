# Module 2 Audio Testing Guide

## Prerequisites
- Module 1 (video conferencing) working correctly
- Microphone connected and working
- Speakers or headphones connected
- At least 2 computers on the same LAN

## Quick Test (2 Clients)

### Step 1: Start Server
```bash
python src/server/server.py
```
Expected output:
```
[HH:MM:SS] Server started on <IP>:5000
[HH:MM:SS] Video streaming on port 5001
[HH:MM:SS] Audio streaming on port 5002
```

### Step 2: Start Client 1
```bash
python src/client/client.py
```
1. Enter server IP address
2. Enter username (e.g., "Alice")
3. Click "Connect"

Expected behavior:
- Video window opens
- Camera LED turns on
- See your own video feed

### Step 3: Start Client 2
```bash
python src/client/client.py
```
1. Enter same server IP
2. Enter different username (e.g., "Bob")
3. Click "Connect"

Expected behavior:
- Both clients see each other's video
- Grid layout shows 2 video streams

### Step 4: Test Audio
**On Client 1 (Alice):**
1. Speak into microphone: "Hello, can you hear me?"

**On Client 2 (Bob):**
- Should hear Alice's voice through speakers/headphones
- Latency should be under 50ms (nearly instant)

**On Client 2 (Bob):**
1. Speak into microphone: "Yes, I can hear you!"

**On Client 1 (Alice):**
- Should hear Bob's voice
- Should NOT hear echo of own voice (server doesn't send audio back to sender)

### Step 5: Test Microphone Toggle
**On Client 1:**
1. Click "🎤 Microphone" button
   - Button should turn red
   - Microphone icon may show strikethrough (⊗🎤)
2. Speak into microphone

**On Client 2:**
- Should NOT hear Client 1's voice
- Video should still be visible

**On Client 1:**
1. Click "🎤 Microphone" again
   - Button should turn green
2. Speak again

**On Client 2:**
- Should hear Client 1's voice again

### Step 6: Test Speaker Toggle
**On Client 2:**
1. Click "🔊 Speaker" button
   - Button should turn red
2. Have Client 1 speak

**On Client 2:**
- Should NOT hear any audio
- Can still speak (microphone still active)

1. Click "🔊 Speaker" again
   - Button should turn green

**On Client 2:**
- Should hear audio again

### Step 7: Test Simultaneous Speech
**Both Clients:**
1. Speak at the same time
   - Both should hear mixed audio
   - Volume may be slightly lower (averaging effect)
   - No severe distortion or clipping

## Advanced Test (3+ Clients)

### Step 1: Add Third Client
```bash
python src/client/client.py
```
- Enter username "Charlie"
- Connect to server

Expected:
- All 3 clients see each other's video
- Grid layout automatically adjusts

### Step 2: Test Multi-Person Audio
1. **Client 1** speaks alone
   - Clients 2 and 3 hear clearly
2. **Client 2** speaks alone
   - Clients 1 and 3 hear clearly
3. **Client 3** speaks alone
   - Clients 1 and 2 hear clearly
4. **All 3 speak simultaneously**
   - All hear mixed audio
   - Volume lower but intelligible

### Step 3: Test Selective Muting
1. **Client 2** mutes microphone
2. **Clients 1 and 3** speak
   - Only they hear each other
   - Client 2 hears both but isn't heard
3. **Client 2** unmutes
   - All can communicate again

## Performance Monitoring

### Server-Side Metrics
Watch server console for:
```
[HH:MM:SS] Audio packet from user_alice (1024 bytes)
[HH:MM:SS] Audio packet from user_bob (1024 bytes)
[HH:MM:SS] Mixed audio broadcasted to 2 clients
```

### Client-Side Metrics
Monitor client console for:
```
[HH:MM:SS] Started audio capture
[HH:MM:SS] Started audio playback
[HH:MM:SS] Audio streaming active
```

### Network Bandwidth
Expected usage per client:
- **Upload**: ~88 KB/s (audio) + ~100 KB/s (video) = ~188 KB/s
- **Download**: ~88 KB/s (audio) + (~100 KB/s × N clients video) 

For 3 clients:
- Each uploads: ~188 KB/s
- Each downloads: ~88 KB/s + 300 KB/s = ~388 KB/s

## Troubleshooting

### No Audio Heard
**Symptoms**: Video works, but no audio
**Checks**:
1. Server console shows "Audio streaming on port 5002" ✓
2. Client console shows "Started audio capture" and "Started audio playback" ✓
3. Microphone permissions granted (check OS settings)
4. Speaker volume not muted or at 0%
5. Windows: Check "Sound Settings" → ensure correct input/output devices
6. Linux: Check PulseAudio/ALSA mixer settings

**Debug**:
```python
# In client.py, add debug prints in capture_and_send_audio():
print(f"Captured audio: {len(audio_data)} bytes")

# In receive_audio_stream():
print(f"Received audio: {len(data)} bytes")
```

### Audio Cutting Out
**Symptoms**: Audio stutters or drops
**Possible Causes**:
1. Network congestion (check with ping)
2. High CPU usage (check Task Manager / top)
3. Too many clients (reduce count or optimize)

**Solutions**:
- Reduce video quality (lower FPS or resolution)
- Close other network-intensive applications
- Use wired Ethernet instead of Wi-Fi

### Echo/Feedback
**Symptoms**: Hear own voice repeated or loud squealing
**Cause**: Audio from speakers picked up by microphone
**Solution**:
- Use headphones instead of speakers
- Reduce speaker volume
- Move microphone farther from speakers
- (Future) Implement echo cancellation

### High Latency
**Symptoms**: Delay > 100ms between speaking and hearing
**Checks**:
1. Ping server: `ping <server_ip>`
   - Should be < 5ms on LAN
2. Check server CPU usage
   - Should be < 50% for 4 clients
3. Check AUDIO_CHUNK size in config.py
   - Larger chunk = higher latency but less jitter

**Debug Latency**:
Add timestamps to measure round-trip:
```python
# Client speaks "beep" at HH:MM:SS.000
# Client hears mixed "beep" at HH:MM:SS.025
# Latency = 25ms ✓
```

### Microphone Toggle Not Working
**Symptoms**: Button clicks but audio still transmits
**Checks**:
1. Console shows "Stopped audio capture" ✓
2. Check `audio_capturing` flag is False
3. Verify thread actually stopped (debug print in capture loop)

### Speaker Toggle Not Working
**Symptoms**: Button clicks but audio still plays
**Checks**:
1. Console shows "Stopped audio playback" ✓
2. Check `audio_playing` flag is False
3. Verify thread actually stopped

### PyAudio Errors
**Error**: `OSError: [Errno -9997] Invalid sample rate`
**Solution**: Microphone doesn't support 44100 Hz
```python
# In config.py, try different rates:
AUDIO_RATE = 48000  # or 16000, 22050, 44100
```

**Error**: `OSError: [Errno -9996] Invalid output device`
**Solution**: No speakers detected
- Check speaker connection
- Check OS audio output settings
- Try different PyAudio device index

**Error**: `IOError: [Errno -9981] Input overflowed`
**Solution**: CPU can't keep up with audio capture
```python
# In start_audio_capture(), add exception_on_overflow=False:
self.audio_stream_input = self.pyaudio_instance.open(
    format=AUDIO_FORMAT,
    channels=AUDIO_CHANNELS,
    rate=AUDIO_RATE,
    input=True,
    frames_per_buffer=AUDIO_CHUNK,
    exception_on_overflow=False  # Add this
)
```

## Success Criteria

### Functional Requirements
- ✅ Multiple clients can hear each other simultaneously
- ✅ Audio latency under 50ms on LAN
- ✅ Microphone toggle mutes audio transmission
- ✅ Speaker toggle mutes audio reception
- ✅ Audio quality is clear and intelligible
- ✅ No severe distortion or clipping

### Non-Functional Requirements
- ✅ CPU usage reasonable (< 50% on modern CPU for 4 clients)
- ✅ Bandwidth within expected range (~88 KB/s per client)
- ✅ No crashes or freezes during normal operation
- ✅ Clean resource cleanup on disconnect
- ✅ GUI controls responsive and intuitive

## Next Steps After Testing

Once Module 2 is verified working:
1. Document any issues found
2. Optimize performance if needed
3. Prepare for Module 3 implementation
4. Consider additional features:
   - Audio recording
   - Volume controls
   - Noise suppression
   - Echo cancellation

---

**Testing Status**: 
- [ ] Basic 2-client audio tested
- [ ] Microphone toggle tested
- [ ] Speaker toggle tested
- [ ] 3+ client mixing tested
- [ ] Latency measured and acceptable
- [ ] Resource cleanup verified
- [ ] All edge cases handled

**Tested By**: _________________  
**Date**: _________________  
**Notes**: _________________
