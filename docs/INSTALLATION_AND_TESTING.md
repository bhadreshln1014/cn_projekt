# Installation & Testing Guide

## Prerequisites

### Required Software
- **Python 3.8 or higher** ([Download](https://www.python.org/downloads/))
- **Webcam** (built-in or external)
- **Network**: LAN connection or WiFi on same network

### For Windows Users
- Python should be added to PATH during installation
- PowerShell or Command Prompt

### For Linux/Mac Users
- Python 3 is usually pre-installed
- Terminal access
- May need to install `python3-tk` for tkinter

## Installation Steps

### Step 1: Download/Clone the Project
```bash
# If you haven't already, navigate to the project directory
cd projekt
```

### Step 2: Install Dependencies

**Windows:**
```bash
pip install -r requirements.txt
```

**Linux/Mac:**
```bash
pip3 install -r requirements.txt
```

### Step 3: Verify Installation
```bash
# Windows
python -c "import cv2, numpy, PIL; print('All dependencies installed!')"
# Linux/Mac
python3 -c "import cv2, numpy, PIL; print('All dependencies installed!')"
```

## Testing Guide

### Test 1: Local Testing (Single Computer)

This test runs both server and multiple clients on the same machine.

#### Terminal 1 - Start Server
**Windows:**
```bash
# Option 1: Use batch script
start_server.bat

# Option 2: Manual
python src\server\server.py
```

**Linux/Mac:**
```bash
# Option 1: Use shell script (make executable first)
chmod +x start_server.sh
./start_server.sh

# Option 2: Manual
python3 src/server/server.py
```

**Expected Output:**
```
[HH:MM:SS] Server started
[HH:MM:SS] TCP Control Port: 5000
[HH:MM:SS] UDP Video Port: 5001
[HH:MM:SS] Waiting for connections...
[HH:MM:SS] UDP video receiver started
```

#### Terminal 2 - Start First Client
**Windows:**
```bash
# Option 1: Use batch script
start_client.bat

# Option 2: Manual
python src\client\client.py
```

**Linux/Mac:**
```bash
# Option 1: Use shell script
chmod +x start_client.sh
./start_client.sh

# Option 2: Manual
python3 src/client/client.py
```

**In the Connection Dialog:**
- Server IP: `127.0.0.1`
- Username: `Alice`
- Click "Connect"

**Expected Result:**
- Client window appears with video grid
- Your webcam activates and you see yourself in one grid cell
- Status bar shows "Connected as: Alice (ID: 0)"

#### Terminal 3 - Start Second Client
Repeat the same process:
- Server IP: `127.0.0.1`
- Username: `Bob`

**Expected Result:**
- Bob's window shows both Alice and Bob's video feeds
- Alice's window updates to show Bob's video feed
- Both users can see each other in real-time

#### Verification Checklist
- [ ] Server shows connection messages for both clients
- [ ] Each client sees their own video (labeled "You")
- [ ] Each client sees other participants' videos
- [ ] Videos update in real-time (~30 FPS)
- [ ] When a client closes, others are notified
- [ ] User count updates correctly

---

### Test 2: LAN Testing (Multiple Computers)

This test uses separate computers on the same network.

#### Setup - Server Computer

1. **Find Server IP Address**

   **Windows:**
   ```bash
   ipconfig
   ```
   Look for "IPv4 Address" under your active network adapter (e.g., `192.168.1.100`)

   **Linux/Mac:**
   ```bash
   ifconfig
   # or
   ip addr show
   ```
   Look for `inet` address (e.g., `192.168.1.100`)

2. **Configure Firewall**

   Allow incoming connections on ports 5000 (TCP) and 5001 (UDP)

   **Windows Firewall:**
   ```bash
   # Run as Administrator
   netsh advfirewall firewall add rule name="LAN Comm TCP" dir=in action=allow protocol=TCP localport=5000
   netsh advfirewall firewall add rule name="LAN Comm UDP" dir=in action=allow protocol=UDP localport=5001
   ```

   **Linux (ufw):**
   ```bash
   sudo ufw allow 5000/tcp
   sudo ufw allow 5001/udp
   ```

3. **Start Server**
   ```bash
   # Windows
   start_server.bat

   # Linux/Mac
   ./start_server.sh
   ```

#### Setup - Client Computers

1. **Install Application** (same as server)

2. **Start Client**
   ```bash
   # Windows
   start_client.bat

   # Linux/Mac
   ./start_client.sh
   ```

3. **Connect to Server**
   - Server IP: `192.168.1.100` (use actual server IP)
   - Username: Unique name for each client
   - Click "Connect"

#### Verification Checklist
- [ ] Clients from different computers can connect
- [ ] All participants see each other's video
- [ ] Video quality is acceptable
- [ ] Latency is low (< 500ms)
- [ ] No excessive lag or freezing
- [ ] Disconnections are handled gracefully

---

### Test 3: Stress Testing

Test the system with maximum users.

1. **Start Server** (as above)

2. **Start Up to 10 Clients**
   - Can mix local and remote clients
   - Use different usernames for each

3. **Observe Performance**
   - CPU usage on server
   - Network bandwidth utilization
   - Video quality degradation (if any)
   - Frame rate stability

**Expected Results:**
- Server handles up to 10 concurrent connections
- Grid shows up to 9 video streams simultaneously
- Performance degrades gracefully under load

---

## Troubleshooting

### Problem: "Import cv2 could not be resolved"
**Solution:**
```bash
pip install opencv-python
# or
pip3 install opencv-python
```

### Problem: "Camera not found" or "Failed to open camera"
**Solutions:**
- Check if another application is using the camera
- Grant camera permissions to Python/Terminal
- Try changing camera index in code (line: `cv2.VideoCapture(0)` → try 1, 2, etc.)
- Run as administrator (Windows) or with sudo (Linux)

### Problem: "Connection refused"
**Solutions:**
- Verify server is running
- Check server IP address is correct
- Verify firewall allows connections on ports 5000 and 5001
- Ensure both computers are on same network
- Try `ping <server_ip>` to verify network connectivity

### Problem: "Poor video quality" or "Choppy playback"
**Solutions:**
- Reduce video quality in `src/common/config.py`:
  ```python
  VIDEO_QUALITY = 40  # Lower value = smaller file size
  ```
- Reduce resolution:
  ```python
  VIDEO_WIDTH = 320
  VIDEO_HEIGHT = 240
  ```
- Check network bandwidth with `iperf` or similar tool
- Reduce number of concurrent clients

### Problem: GUI doesn't appear (Linux)
**Solution:**
```bash
sudo apt-get install python3-tk
```

### Problem: "Address already in use"
**Solution:**
- Another instance of the server is running
- Wait a few seconds and try again
- Kill the existing process:
  ```bash
  # Windows
  netstat -ano | findstr :5000
  taskkill /PID <PID> /F

  # Linux/Mac
  lsof -i :5000
  kill -9 <PID>
  ```

---

## Performance Benchmarks

### Expected Performance (per client)
- **CPU Usage**: 5-15% (varies by computer)
- **RAM Usage**: 50-100 MB
- **Network Bandwidth**: 
  - Upload: ~400 KB/s per stream
  - Download: ~400 KB/s × (number of other clients)
- **Latency**: 50-200ms on LAN

### Recommended Hardware
- **CPU**: Dual-core 2.0 GHz or better
- **RAM**: 2 GB minimum
- **Network**: 100 Mbps LAN (10 Mbps for 2-3 users)

---

## Next Steps After Testing

Once Module 1 is working correctly:

1. **Document any issues** encountered during testing
2. **Optimize** based on your network and hardware
3. **Prepare for Module 2** (Audio Conferencing)
4. **Consider enhancements**:
   - Recording functionality
   - Better error messages
   - Connection retry logic
   - Bandwidth monitoring

---

## Getting Help

If you encounter issues:

1. Check the error message carefully
2. Review `MODULE1_SUMMARY.md` for technical details
3. Verify all prerequisites are met
4. Test with minimal setup (1 server, 1 client, same machine)
5. Check firewall and network settings

---

## Success Criteria

Module 1 is successfully implemented if:
- ✅ Server starts without errors
- ✅ Multiple clients can connect simultaneously
- ✅ All clients see each other's video feeds
- ✅ Video is smooth (~30 FPS)
- ✅ Disconnections are handled gracefully
- ✅ System works across LAN (not just localhost)

**If all criteria are met, Module 1 is COMPLETE!** 🎉

Ready to proceed to Module 2 when you are!
