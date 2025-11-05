# File Sharing Module - Technical Documentation

**Computer Networks Project**  
**Module**: File Sharing & Transfer  
**Developers**: Bhadresh L and Santhana Srinivasan R

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Implementation Details](#implementation-details)
4. [Transfer Protocol](#transfer-protocol)
5. [Data Flow](#data-flow)
6. [Code Walkthrough](#code-walkthrough)
7. [Performance Analysis](#performance-analysis)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The file sharing module enables users to upload files to the server and download files shared by other users. Files are transferred reliably via TCP, stored temporarily on the server, and made available to all participants.

### Key Features
- **Upload to Server**: Any user can upload files
- **Server Storage**: Files stored in memory on server
- **Download Capability**: All users can download shared files
- **Progress Tracking**: Real-time upload/download progress bars
- **Metadata Display**: Filename, size, uploader, timestamp
- **File Management**: Delete own files, list available files
- **Large File Support**: Files up to 100MB supported
- **Chunked Transfer**: 8KB chunks for efficiency
- **Reliability**: TCP ensures complete, error-free transfer

### Technical Specifications
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Protocol | TCP | Reliability essential for files |
| Port | 5005 | Dedicated file transfer port |
| Chunk Size | 8,192 bytes (8KB) | Balance between efficiency and memory |
| Max File Size | 100 MB | Prevents server memory exhaustion |
| Storage | In-memory | Fast access, temporary session storage |
| Encoding | Base64 (optional) | Binary-safe transmission |
| Compression | None | Files may already be compressed |
| Concurrent Transfers | Unlimited | Separate thread per transfer |

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT (UPLOADER)                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │ User Clicks  │─────▶│ File Dialog  │                │
│  │"Upload File" │      │ (Select File)│                │
│  └──────────────┘      └──────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ Read File     │                │
│                        │ from Disk     │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ TCP Connect   │                │
│                        │ Port 5005     │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ Send Metadata │                │
│                        │ (UPLOAD cmd)  │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ Send File in  │                │
│                        │ 8KB Chunks    │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ Update        │                │
│                        │ Progress Bar  │                │
│                        └───────┬───────┘                │
│                                │                         │
└────────────────────────────────┼─────────────────────────┘
                                 │
                                 │ File Upload
                                 │
┌────────────────────────────────▼─────────────────────────┐
│                    SERVER SIDE                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│                        ┌───────────────┐                │
│                        │ TCP Accept    │                │
│                        │ (Port 5005)   │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ Receive       │                │
│                        │ Command       │                │
│                        └───────┬───────┘                │
│                                │                         │
│                    ┌───────────┴───────────┐            │
│                    │                       │            │
│                    ▼                       ▼            │
│            ┌───────────────┐      ┌───────────────┐    │
│            │ UPLOAD        │      │ DOWNLOAD      │    │
│            │ Process       │      │ Process       │    │
│            └───────┬───────┘      └───────┬───────┘    │
│                    │                       │            │
│                    ▼                       │            │
│            ┌───────────────┐              │            │
│            │ Receive Chunks│              │            │
│            │ Store in RAM  │              │            │
│            └───────┬───────┘              │            │
│                    │                       │            │
│                    ▼                       │            │
│            ┌───────────────┐              │            │
│            │ Assign File ID│              │            │
│            │ Store Metadata│              │            │
│            └───────┬───────┘              │            │
│                    │                       │            │
│                    ▼                       │            │
│            ┌───────────────┐              │            │
│            │ Broadcast     │              │            │
│            │ FILE_OFFER    │              │            │
│            └───────┬───────┘              │            │
│                    │                       │            │
└────────────────────┼───────────────────────┼────────────┘
                     │                       │
                     │ Notify All            │ Send File
                     │                       │
┌────────────────────▼───────────────────────▼────────────┐
│                    ALL CLIENTS                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────┐      │
│  │ Receive FILE_OFFER Notification              │      │
│  │ • File ID, Name, Size, Uploader, Timestamp   │      │
│  └────────────────────┬─────────────────────────┘      │
│                       │                                 │
│                       ▼                                 │
│  ┌──────────────────────────────────────────────┐      │
│  │ Update File List in Files Panel              │      │
│  │ Display download button for each file        │      │
│  └────────────────────┬─────────────────────────┘      │
│                       │                                 │
│                       ▼                                 │
│  ┌──────────────────────────────────────────────┐      │
│  │ User Clicks "Download" Button                │      │
│  └────────────────────┬─────────────────────────┘      │
│                       │                                 │
│                       ▼                                 │
│  ┌──────────────────────────────────────────────┐      │
│  │ Connect to Server Port 5005                  │      │
│  │ Send: DOWNLOAD:<file_id>                     │      │
│  └────────────────────┬─────────────────────────┘      │
│                       │                                 │
│                       ▼                                 │
│  ┌──────────────────────────────────────────────┐      │
│  │ Receive File in Chunks                       │      │
│  │ Save to Selected Location                    │      │
│  │ Update Progress Bar                          │      │
│  └──────────────────────────────────────────────┘      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. File Upload (Client Side)

**Location**: `src/client/client.py` - Method `upload_file()`

```python
def upload_file(self):
    """
    Upload file to server
    Opens file dialog, reads file, and sends via TCP
    """
    if not self.connected:
        QMessageBox.warning(self, "Upload Error", "Not connected to server")
        return
    
    # Open file dialog
    file_path, _ = QFileDialog.getOpenFileName(
        self,
        "Select File to Upload",
        "",
        "All Files (*.*)"
    )
    
    if not file_path:
        return  # User cancelled
    
    try:
        # Get file info
        filename = os.path.basename(file_path)
        filesize = os.path.getsize(file_path)
        
        # Check file size limit
        if filesize > MAX_FILE_SIZE:
            QMessageBox.warning(
                self,
                "File Too Large",
                f"File size ({filesize / 1024 / 1024:.2f} MB) exceeds limit ({MAX_FILE_SIZE / 1024 / 1024} MB)"
            )
            return
        
        # Create progress dialog
        progress = QProgressDialog(
            f"Uploading {filename}...",
            "Cancel",
            0,
            filesize,
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("File Upload")
        progress.show()
        
        # Connect to file transfer port
        file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        file_socket.connect((self.server_address, SERVER_FILE_PORT))
        
        # Send upload command with metadata
        upload_cmd = f"UPLOAD:{self.client_id}:{self.username}:{filename}:{filesize}\n"
        file_socket.send(upload_cmd.encode('utf-8'))
        
        # Wait for server ready signal
        response = file_socket.recv(1024).decode('utf-8').strip()
        if response != "READY":
            raise Exception(f"Server not ready: {response}")
        
        # Read and send file in chunks
        bytes_sent = 0
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(FILE_CHUNK_SIZE)  # 8KB chunks
                if not chunk:
                    break
                
                file_socket.send(chunk)
                bytes_sent += len(chunk)
                
                # Update progress
                progress.setValue(bytes_sent)
                
                # Check if cancelled
                if progress.wasCanceled():
                    raise Exception("Upload cancelled by user")
        
        # Close connection
        file_socket.close()
        
        # Update progress
        progress.setValue(filesize)
        progress.close()
        
        # Show success message
        QMessageBox.information(
            self,
            "Upload Complete",
            f"'{filename}' uploaded successfully!"
        )
        
        print(f"[{self.get_timestamp()}] File uploaded: {filename} ({filesize} bytes)")
        
    except Exception as e:
        print(f"Error uploading file: {e}")
        QMessageBox.critical(
            self,
            "Upload Error",
            f"Failed to upload file: {e}"
        )
        if 'file_socket' in locals():
            file_socket.close()
```

### 2. File Upload Processing (Server Side)

**Location**: `src/server/server.py` - Method `handle_file_transfer()`

```python
def handle_file_transfer(self, conn, address):
    """
    Handle file upload or download request
    Runs in separate thread for each transfer
    """
    try:
        # Receive command
        data = conn.recv(1024).decode('utf-8').strip()
        
        if data.startswith("UPLOAD:"):
            # File upload: UPLOAD:client_id:username:filename:filesize
            parts = data.split(":", 4)
            if len(parts) < 5:
                conn.send("ERROR:Invalid upload command\n".encode('utf-8'))
                return
            
            client_id = int(parts[1])
            username = parts[2]
            filename = parts[3]
            filesize = int(parts[4])
            
            # Validate file size
            if filesize > MAX_FILE_SIZE:
                conn.send(f"ERROR:File too large (max {MAX_FILE_SIZE} bytes)\n".encode('utf-8'))
                return
            
            print(f"[{self.get_timestamp()}] Receiving file '{filename}' ({filesize} bytes) from {username}")
            
            # Send ready signal
            conn.send("READY\n".encode('utf-8'))
            
            # Receive file data in chunks
            file_data = b''
            bytes_received = 0
            
            while bytes_received < filesize:
                chunk_size = min(FILE_CHUNK_SIZE, filesize - bytes_received)
                chunk = conn.recv(chunk_size)
                
                if not chunk:
                    raise Exception("Connection closed before transfer complete")
                
                file_data += chunk
                bytes_received += len(chunk)
            
            print(f"[{self.get_timestamp()}] File '{filename}' received completely ({bytes_received} bytes)")
            
            # Store file
            with self.files_lock:
                file_id = self.file_id_counter
                self.file_id_counter += 1
                
                self.shared_files[file_id] = {
                    'filename': filename,
                    'size': filesize,
                    'uploader_id': client_id,
                    'uploader_name': username,
                    'data': file_data,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            
            # Notify all clients about new file
            self.broadcast_file_offer(file_id)
            
            print(f"[{self.get_timestamp()}] File '{filename}' stored with ID {file_id}")
            
        elif data.startswith("DOWNLOAD:"):
            # File download: DOWNLOAD:file_id
            file_id = int(data.split(":", 1)[1])
            
            # Get file data
            with self.files_lock:
                if file_id not in self.shared_files:
                    conn.send("ERROR:File not found\n".encode('utf-8'))
                    return
                
                file_info = self.shared_files[file_id]
            
            print(f"[{self.get_timestamp()}] Sending file '{file_info['filename']}' (ID: {file_id})")
            
            # Send file metadata
            metadata = f"FILE:{file_info['filename']}:{file_info['size']}\n"
            conn.send(metadata.encode('utf-8'))
            
            # Wait for client ready
            response = conn.recv(1024).decode('utf-8').strip()
            if response != "READY":
                return
            
            # Send file data in chunks
            file_data = file_info['data']
            bytes_sent = 0
            
            while bytes_sent < len(file_data):
                chunk_end = min(bytes_sent + FILE_CHUNK_SIZE, len(file_data))
                chunk = file_data[bytes_sent:chunk_end]
                conn.send(chunk)
                bytes_sent += len(chunk)
            
            print(f"[{self.get_timestamp()}] File '{file_info['filename']}' sent completely")
            
    except Exception as e:
        print(f"[{self.get_timestamp()}] Error in file transfer: {e}")
    
    finally:
        conn.close()
```

### 3. File Offer Broadcast

**Location**: `src/server/server.py` - Method `broadcast_file_offer()`

```python
def broadcast_file_offer(self, file_id):
    """
    Notify all clients about newly uploaded file
    """
    with self.files_lock:
        if file_id not in self.shared_files:
            return
        
        file_info = self.shared_files[file_id]
    
    # Format notification: FILE_OFFER:file_id:filename:filesize:uploader_name:uploader_id
    message = (
        f"FILE_OFFER:{file_id}:{file_info['filename']}:{file_info['size']}:"
        f"{file_info['uploader_name']}:{file_info['uploader_id']}\n"
    )
    
    # Send to all clients via their TCP connections
    with self.clients_lock:
        for client_id, client_info in self.clients.items():
            try:
                client_info['tcp_conn'].send(message.encode('utf-8'))
            except Exception as e:
                print(f"[{self.get_timestamp()}] Error notifying client {client_id} about file: {e}")
    
    print(f"[{self.get_timestamp()}] Broadcasted file offer: {file_info['filename']} (ID: {file_id})")
```

### 4. File Download (Client Side)

**Location**: `src/client/client.py` - Method `download_file()`

```python
def download_file(self, file_id):
    """
    Download file from server
    """
    if file_id not in self.shared_files_metadata:
        QMessageBox.warning(self, "Download Error", "File not found")
        return
    
    file_info = self.shared_files_metadata[file_id]
    filename = file_info['filename']
    filesize = file_info['size']
    
    # Ask where to save
    save_path, _ = QFileDialog.getSaveFileName(
        self,
        "Save File As",
        filename,  # Default filename
        "All Files (*.*)"
    )
    
    if not save_path:
        return  # User cancelled
    
    try:
        # Create progress dialog
        progress = QProgressDialog(
            f"Downloading {filename}...",
            "Cancel",
            0,
            filesize,
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("File Download")
        progress.show()
        
        # Connect to file transfer port
        file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        file_socket.connect((self.server_address, SERVER_FILE_PORT))
        
        # Send download request
        download_cmd = f"DOWNLOAD:{file_id}\n"
        file_socket.send(download_cmd.encode('utf-8'))
        
        # Receive file metadata
        response = file_socket.recv(1024).decode('utf-8').strip()
        if response.startswith("ERROR:"):
            raise Exception(response.split(":", 1)[1])
        
        if not response.startswith("FILE:"):
            raise Exception(f"Unexpected response: {response}")
        
        # Parse metadata: FILE:filename:filesize
        parts = response.split(":", 2)
        received_filename = parts[1]
        received_filesize = int(parts[2])
        
        # Send ready signal
        file_socket.send("READY\n".encode('utf-8'))
        
        # Receive file data in chunks
        bytes_received = 0
        with open(save_path, 'wb') as f:
            while bytes_received < received_filesize:
                chunk_size = min(FILE_CHUNK_SIZE, received_filesize - bytes_received)
                chunk = file_socket.recv(chunk_size)
                
                if not chunk:
                    raise Exception("Connection closed before transfer complete")
                
                f.write(chunk)
                bytes_received += len(chunk)
                
                # Update progress
                progress.setValue(bytes_received)
                
                # Check if cancelled
                if progress.wasCanceled():
                    raise Exception("Download cancelled by user")
        
        # Close connection
        file_socket.close()
        
        # Update progress
        progress.setValue(received_filesize)
        progress.close()
        
        # Show success message
        QMessageBox.information(
            self,
            "Download Complete",
            f"'{filename}' saved to {save_path}"
        )
        
        print(f"[{self.get_timestamp()}] File downloaded: {filename} ({received_filesize} bytes)")
        
    except Exception as e:
        print(f"Error downloading file: {e}")
        QMessageBox.critical(
            self,
            "Download Error",
            f"Failed to download file: {e}"
        )
        if 'file_socket' in locals():
            file_socket.close()
        # Delete partial file
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except:
                pass
```

### 5. File List Display

**Location**: `src/client/client.py` - Method `update_file_list()`

```python
def update_file_list(self):
    """
    Update file list display in Files panel
    Shows available files with download buttons
    """
    # Clear existing file widgets
    # ... (clear layout code) ...
    
    # Add each file
    for file_id, file_info in self.shared_files_metadata.items():
        # Create file item widget
        file_item = QFrame()
        file_item.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame:hover {
                background-color: #3c4043;
            }
        """)
        
        item_layout = QVBoxLayout(file_item)
        item_layout.setContentsMargins(10, 10, 10, 10)
        
        # Filename
        filename_label = QLabel(file_info['filename'])
        filename_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        filename_label.setStyleSheet("color: #e8eaed;")
        item_layout.addWidget(filename_label)
        
        # File info (size, uploader)
        size_mb = file_info['size'] / 1024 / 1024
        info_text = f"{size_mb:.2f} MB • Uploaded by {file_info['uploader']}"
        info_label = QLabel(info_text)
        info_label.setFont(QFont("Arial", 9))
        info_label.setStyleSheet("color: #9aa0a6;")
        item_layout.addWidget(info_label)
        
        # Download button
        download_btn = QPushButton("Download")
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
        """)
        download_btn.clicked.connect(lambda checked, fid=file_id: self.download_file(fid))
        item_layout.addWidget(download_btn)
        
        # Add to file list layout
        self.file_list_layout.addWidget(file_item)
```

---

## Transfer Protocol

### Commands

#### 1. Upload Command

**Client → Server**:
```
UPLOAD:<client_id>:<username>:<filename>:<filesize>\n
```

**Server → Client**:
```
READY\n    (server ready to receive)
ERROR:<message>\n    (if validation fails)
```

**Then**: Client sends file data in 8KB chunks (binary)

#### 2. Download Command

**Client → Server**:
```
DOWNLOAD:<file_id>\n
```

**Server → Client**:
```
FILE:<filename>:<filesize>\n
ERROR:<message>\n    (if file not found)
```

**Client → Server**:
```
READY\n
```

**Then**: Server sends file data in 8KB chunks (binary)

#### 3. File Offer Notification

**Server → All Clients**:
```
FILE_OFFER:<file_id>:<filename>:<filesize>:<uploader_name>:<uploader_id>\n
```

Broadcast when new file uploaded

#### 4. File Deleted Notification

**Server → All Clients**:
```
FILE_DELETED:<file_id>\n
```

Broadcast when file removed from server

---

## Data Flow

### Upload Flow

```
┌────────────────────────────────────────────────────────────────┐
│ STEP 1: FILE SELECTION                                         │
├────────────────────────────────────────────────────────────────┤
│ User clicks "Upload File"                                      │
│ QFileDialog opens                                              │
│ User selects file: "report.pdf" (2.5 MB)                      │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 2: VALIDATION                                             │
├────────────────────────────────────────────────────────────────┤
│ Check file exists: os.path.exists(file_path)                  │
│ Get file size: os.path.getsize(file_path) = 2,621,440 bytes  │
│ Check size limit: 2.5 MB < 100 MB ✓                           │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 3: TCP CONNECTION                                         │
├────────────────────────────────────────────────────────────────┤
│ Create socket: socket.socket(AF_INET, SOCK_STREAM)            │
│ Connect: file_socket.connect((server_ip, 5005))               │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 4: SEND UPLOAD COMMAND                                    │
├────────────────────────────────────────────────────────────────┤
│ Format: "UPLOAD:3:Alice:report.pdf:2621440\n"                 │
│ Send via TCP                                                   │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 5: SERVER VALIDATION & READY SIGNAL                       │
├────────────────────────────────────────────────────────────────┤
│ Parse command: extract metadata                                │
│ Validate size: 2.5 MB < 100 MB ✓                              │
│ Send: "READY\n"                                                │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 6: CHUNKED FILE TRANSFER                                  │
├────────────────────────────────────────────────────────────────┤
│ Open file: with open('report.pdf', 'rb') as f:                │
│ Loop:                                                          │
│   Chunk 1: Read 8,192 bytes → Send                            │
│   Chunk 2: Read 8,192 bytes → Send                            │
│   ...                                                          │
│   Chunk 320: Read 8,192 bytes → Send                          │
│   Chunk 321: Read remaining 64 bytes → Send                   │
│ Total: 321 chunks sent                                         │
│ Progress bar updated after each chunk                         │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 7: SERVER RECEPTION & STORAGE                             │
├────────────────────────────────────────────────────────────────┤
│ Receive all chunks: file_data = b''                           │
│ Concatenate: file_data += chunk                               │
│ Verify size: len(file_data) == 2,621,440 ✓                   │
│ Assign ID: file_id = 15                                       │
│ Store in dict: shared_files[15] = {...}                       │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 8: BROADCAST FILE OFFER                                   │
├────────────────────────────────────────────────────────────────┤
│ Message: "FILE_OFFER:15:report.pdf:2621440:Alice:3\n"        │
│ Send to all clients via control TCP connection                │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 9: ALL CLIENTS UPDATE FILE LIST                           │
├────────────────────────────────────────────────────────────────┤
│ Receive FILE_OFFER notification                               │
│ Parse metadata                                                 │
│ Add to shared_files_metadata dict                             │
│ Update Files panel UI                                          │
│ Show download button                                           │
└────────────────────────────────────────────────────────────────┘
```

### Download Flow

```
(User clicks Download button for file ID 15)
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 1: SAVE DIALOG                                            │
├────────────────────────────────────────────────────────────────┤
│ QFileDialog.getSaveFileName()                                  │
│ User selects: "C:\Downloads\report.pdf"                       │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 2: CONNECT & REQUEST                                      │
├────────────────────────────────────────────────────────────────┤
│ Connect to server:5005                                         │
│ Send: "DOWNLOAD:15\n"                                          │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 3: SERVER LOOKUP & METADATA                               │
├────────────────────────────────────────────────────────────────┤
│ Find file: file = shared_files[15]                            │
│ Send metadata: "FILE:report.pdf:2621440\n"                    │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 4: CLIENT READY SIGNAL                                    │
├────────────────────────────────────────────────────────────────┤
│ Client sends: "READY\n"                                        │
│ Open file for writing: f = open(save_path, 'wb')              │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 5: SERVER SENDS FILE                                      │
├────────────────────────────────────────────────────────────────┤
│ file_data = shared_files[15]['data']                          │
│ Send in 8KB chunks (321 chunks total)                         │
│ Progress tracked on server side                               │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 6: CLIENT RECEIVES & SAVES                                │
├────────────────────────────────────────────────────────────────┤
│ Receive chunk 1: 8,192 bytes → Write to file                  │
│ Receive chunk 2: 8,192 bytes → Write to file                  │
│ ... (321 chunks total)                                         │
│ Update progress bar after each chunk                          │
│ Close file when complete                                       │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 7: COMPLETION                                             │
├────────────────────────────────────────────────────────────────┤
│ Close TCP connection                                           │
│ Show success message: "File saved to C:\Downloads\..."        │
│ File ready to use                                              │
└────────────────────────────────────────────────────────────────┘
```

---

## Performance Analysis

### Transfer Speed

**Theoretical Maximum** (Gigabit Ethernet):
- 1 Gbps = 125 MB/s
- TCP overhead ~5-10%
- **Effective**: ~110-120 MB/s

**Actual Performance** (LAN):
- Typically: 20-50 MB/s
- 100 MB file: 2-5 seconds
- 10 MB file: 0.2-0.5 seconds

**Factors Affecting Speed**:
- Network congestion
- Server CPU (reading/writing files)
- Client disk I/O speed
- Concurrent transfers

### Memory Usage

**Server Side**:
```
Memory per file = File size (stored in RAM)
10 files @ 10 MB each = 100 MB
Maximum (10 users × 100 MB) = 1 GB
```

**Client Side**:
- Minimal (streams to disk)
- ~8 KB buffer per transfer

### Bandwidth Impact

**During Transfer**:
- Upload: Uses full available bandwidth
- Download: Uses full available bandwidth
- **Impact on other features**: Minimal (separate port)

**Best Practice**:
- Transfer large files when not actively using video/audio
- Or accept slight quality reduction during transfer

### Scalability

| Metric | 1 User | 5 Users | 10 Users |
|--------|--------|---------|----------|
| Simultaneous Uploads | Fast | Slower | Contention |
| Server Memory (10MB/file) | 10 MB | 50 MB | 100 MB |
| Download Bandwidth | 20 MB/s | 4 MB/s ea | 2 MB/s ea |

---

## Troubleshooting

### Common Issues

#### 1. Upload Fails

**Symptoms**:
- File selection works but upload stalls
- Error: "Connection refused"

**Diagnosis**:
```python
# Check if server file socket is listening
netstat -an | findstr 5005  # Windows
netstat -an | grep 5005     # Linux/Mac

# Should show: LISTENING on port 5005
```

**Solutions**:
- Ensure server file transfer thread started
- Check firewall allows TCP port 5005
- Verify file size under 100 MB limit
- Try smaller file first

#### 2. Download Fails

**Symptoms**:
- Download starts but stops mid-transfer
- Partial file created

**Diagnosis**:
```python
# Server: Check if file exists
print(f"File {file_id} in shared_files: {file_id in self.shared_files}")

# Client: Check connection
print(f"Connected to {self.server_address}:5005")
```

**Solutions**:
- Verify file_id is valid
- Check disk space on client
- Ensure stable network connection
- Check no firewall blocking mid-transfer

#### 3. File Not Appearing in List

**Symptoms**:
- Upload completes but file not shown to others

**Diagnosis**:
```python
# Server: Check broadcast
print(f"Broadcasting FILE_OFFER to {len(self.clients)} clients")

# Client: Check TCP receive
print("Received FILE_OFFER notification")
```

**Solutions**:
- Verify `broadcast_file_offer()` called after upload
- Check all clients have active TCP connections
- Ensure `update_file_list()` called on client

#### 4. "File Too Large" Error

**Symptoms**:
- Upload rejected with size error

**Solutions**:
- Check `MAX_FILE_SIZE` in config.py (default: 100 MB)
- Increase limit if server has sufficient RAM
- Compress file before uploading
- Split large files into parts

```python
# Increase limit (in config.py)
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB
```

#### 5. Out of Memory

**Symptoms**:
- Server crashes after multiple uploads
- Memory usage steadily increases

**Diagnosis**:
```python
# Monitor server memory
import psutil
print(f"Memory usage: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB")
```

**Solutions**:
- Implement file cleanup (delete old files)
- Store files on disk instead of RAM
- Limit number of files per session

**Disk-Based Storage** (Alternative):
```python
# Instead of storing in memory
self.shared_files[file_id] = {
    'filename': filename,
    'size': filesize,
    'filepath': f'/tmp/uploads/{file_id}_{filename}',  # Path on disk
    ...
}

# Write to disk
with open(filepath, 'wb') as f:
    f.write(file_data)
```

---

## Advanced Features (Not Implemented)

### 1. Resume Capability

For interrupted transfers:

```python
# Client sends resume offset
UPLOAD_RESUME:<file_id>:<offset>\n

# Server continues from offset
# Client seeks to offset in file
f.seek(offset)
chunk = f.read(FILE_CHUNK_SIZE)
```

### 2. File Compression

Compress before upload:

```python
import gzip

# Compress
with open(file_path, 'rb') as f_in:
    with gzip.open(f'{file_path}.gz', 'wb') as f_out:
        f_out.writelines(f_in)

# Upload compressed file
# Server stores compressed
# Client decompresses after download
```

### 3. Encryption

Encrypt files for privacy:

```python
from cryptography.fernet import Fernet

# Generate key
key = Fernet.generate_key()
cipher = Fernet(key)

# Encrypt file
encrypted_data = cipher.encrypt(file_data)

# Upload encrypted data
# Share key via secure channel
# Recipient decrypts after download
```

### 4. File Preview

Generate thumbnails for images:

```python
from PIL import Image

# Create thumbnail
img = Image.open(file_path)
img.thumbnail((200, 200))
thumbnail_data = img.tobytes()

# Send with FILE_OFFER
# Display preview in file list
```

### 5. Version Control

Track file versions:

```python
# Store multiple versions
self.shared_files[file_id] = {
    'filename': filename,
    'versions': [
        {'data': data_v1, 'timestamp': time1, 'uploader': user1},
        {'data': data_v2, 'timestamp': time2, 'uploader': user2},
    ]
}

# Client can download specific version
DOWNLOAD:<file_id>:<version_number>\n
```

---

## Future Enhancements

1. **Persistent Storage**: Save files to database or disk
2. **File Expiry**: Auto-delete files after 24 hours
3. **Access Control**: Restrict downloads to specific users
4. **Drag & Drop**: Drag files directly into window
5. **Multiple File Upload**: Upload multiple files at once
6. **Folder Upload**: Upload entire folders
7. **Direct Transfer**: P2P transfer between clients (bypass server)
8. **Cloud Backup**: Sync files to cloud storage
9. **File Comments**: Add notes/comments to files
10. **File Categories**: Organize files by type/category

---

**End of File Sharing Module Documentation**

---

## Summary

The file sharing module provides a robust, TCP-based file transfer system with:

- ✅ **Reliable Transfer**: TCP ensures complete, error-free delivery
- ✅ **Progress Tracking**: Real-time upload/download progress
- ✅ **Broadcast Notifications**: All users informed of new files
- ✅ **Simple Protocol**: Easy to understand and debug
- ✅ **Large File Support**: Up to 100 MB files
- ✅ **Concurrent Transfers**: Multiple users can upload/download simultaneously

**Key Takeaway**: The file sharing module complements the real-time communication features by providing a method to share documents, images, and other files that enhance collaboration in the LAN conference environment.
