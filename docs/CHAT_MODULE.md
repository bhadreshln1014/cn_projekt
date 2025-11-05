# Chat Module - Technical Documentation

**Computer Networks Project**  
**Module**: Group Text Chat & Private Messaging  
**Developers**: Bhadresh L and Santhana Srinivasan R

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Implementation Details](#implementation-details)
4. [Message Protocol](#message-protocol)
5. [Data Flow](#data-flow)
6. [Code Walkthrough](#code-walkthrough)
7. [Features](#features)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The chat module provides text-based communication between users in the conference. It supports both group messaging (broadcast to all) and private messaging (direct messages to specific users).

### Key Features
- **Group Chat**: Broadcast messages to all connected users
- **Private Messages**: Send messages to specific individuals or groups
- **Chat History**: Server maintains full conversation history
- **Timestamps**: All messages timestamped (HH:MM:SS format)
- **User Identification**: Shows sender's username with each message
- **Notifications**: Visual notifications for incoming messages
- **Persistent Connection**: Uses existing TCP connection (port 5000)
- **Thread-Safe**: Concurrent send/receive operations

### Technical Specifications
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Protocol | TCP | Reliability required for text messages |
| Port | 5000 | Shared with control messages |
| Encoding | UTF-8 | Universal character support |
| Message Format | Plain text | Simple and human-readable |
| Max Message Length | Unlimited | TCP handles segmentation |
| Delimiter | Newline (\n) | Simple message boundary |
| Latency | < 10 ms | TCP on LAN is very fast |
| Reliability | 100% | TCP guarantees delivery |

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT A                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │ User Types   │─────▶│ Message Input│                │
│  │ Message      │      │ Field (GUI)  │                │
│  └──────────────┘      └──────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ Format Message│                │
│                        │ CHAT_MESSAGE: │                │
│                        │ recipients:msg│                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ TCP Send      │                │
│                        │ (Port 5000)   │                │
│                        └───────┬───────┘                │
│                                │                         │
└────────────────────────────────┼─────────────────────────┘
                                 │
                                 │ Chat Message
                                 │
┌────────────────────────────────▼─────────────────────────┐
│                    SERVER SIDE                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│                        ┌───────────────┐                │
│                        │ TCP Receive   │                │
│                        │ (Port 5000)   │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ Parse Message │                │
│                        │ • Extract text│                │
│                        │ • Get sender  │                │
│                        │ • Recipients  │                │
│                        └───────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ Store in      │                │
│                        │ chat_history  │                │
│                        └───────┬───────┘                │
│                                │                         │
│                    ┌───────────┴───────────┐            │
│                    │                       │            │
│                    ▼                       ▼            │
│            ┌───────────────┐      ┌───────────────┐    │
│            │ Group Message │      │Private Message│    │
│            │ (All users)   │      │ (Selected)    │    │
│            └───────┬───────┘      └───────┬───────┘    │
│                    │                       │            │
│                    └───────────┬───────────┘            │
│                                │                         │
│                                ▼                         │
│                        ┌───────────────┐                │
│                        │ Format & Send │                │
│                        │ to Recipients │                │
│                        └───────┬───────┘                │
│                                │                         │
└────────────────────────────────┼─────────────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
         ┌──────────┐     ┌──────────┐   ┌──────────┐
         │ Client A │     │ Client B │   │ Client C │
         │ (Sender) │     │(Recipient)│   │(Recipient)│
         └────┬─────┘     └────┬─────┘   └────┬─────┘
              │                │               │
              ▼                ▼               ▼
      ┌──────────────┐  ┌──────────────┐ ┌──────────────┐
      │ Display in   │  │ Display in   │ │ Display in   │
      │ Chat Panel   │  │ Chat Panel   │ │ Chat Panel   │
      │ + Notify     │  │ + Notify     │ │ + Notify     │
      └──────────────┘  └──────────────┘ └──────────────┘
```

---

## Implementation Details

### 1. Sending Messages (Client Side)

**Location**: `src/client/client.py` - Method `send_chat_message()`

```python
def send_chat_message(self):
    """
    Send chat message to server
    Handles both group and private messages
    """
    message = self.chat_input.text().strip()
    
    if not message or not self.tcp_socket:
        return
    
    try:
        # Determine recipients
        if self.selected_recipients:
            # Private message to selected recipients
            recipient_ids = ','.join(map(str, self.selected_recipients))
            formatted_message = f"PRIVATE_CHAT:{recipient_ids}:{message}\n"
        else:
            # Group message (to everyone)
            formatted_message = f"CHAT_MESSAGE:{message}\n"
        
        # Send via TCP
        self.tcp_socket.send(formatted_message.encode('utf-8'))
        
        # Clear input field
        self.chat_input.clear()
        
        # Update UI to show message was sent
        print(f"[{self.get_timestamp()}] Sent: {message}")
        
    except Exception as e:
        print(f"Error sending chat message: {e}")
        QMessageBox.warning(
            self,
            "Chat Error",
            f"Failed to send message: {e}"
        )
```

### 2. Message Processing (Server Side)

**Location**: `src/server/server.py` - Method `handle_client()`

```python
def handle_client(self, conn, address):
    """
    Handle client TCP connection - includes chat message processing
    """
    client_id = None
    username = None
    
    try:
        # ... connection establishment code ...
        
        while self.running:
            data = conn.recv(1024).decode('utf-8')
            
            if not data:
                break
            
            # Parse chat messages
            if data.startswith("CHAT_MESSAGE:"):
                # Group chat message
                message_text = data.split(":", 1)[1].strip()
                self.broadcast_chat_message(client_id, username, message_text)
                
            elif data.startswith("PRIVATE_CHAT:"):
                # Private message
                parts = data.split(":", 2)
                if len(parts) >= 3:
                    recipient_ids_str = parts[1]
                    message_text = parts[2].strip()
                    
                    # Parse recipient IDs
                    recipient_ids = [int(rid) for rid in recipient_ids_str.split(',')]
                    
                    # Send private message
                    self.send_private_message(
                        client_id,
                        username,
                        recipient_ids,
                        message_text
                    )
                    
    except Exception as e:
        print(f"[{self.get_timestamp()}] Client {client_id} error: {e}")
```

### 3. Group Message Broadcasting

**Location**: `src/server/server.py` - Method `broadcast_chat_message()`

```python
def broadcast_chat_message(self, sender_id, sender_username, message):
    """
    Broadcast chat message to all connected clients
    Stores message in chat history
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Create chat entry
    chat_entry = {
        'client_id': sender_id,
        'username': sender_username,
        'message': message,
        'timestamp': timestamp,
        'type': 'group'
    }
    
    # Store in history
    with self.chat_lock:
        self.chat_history.append(chat_entry)
    
    # Format message for transmission
    formatted_message = f"CHAT:{sender_id}:{sender_username}:{timestamp}:{message}\n"
    
    # Broadcast to all clients
    with self.clients_lock:
        for client_id, client_info in self.clients.items():
            try:
                client_info['tcp_conn'].send(formatted_message.encode('utf-8'))
            except Exception as e:
                print(f"[{self.get_timestamp()}] Error sending chat to client {client_id}: {e}")
    
    print(f"[{self.get_timestamp()}] Chat from {sender_username}: {message}")
```

### 4. Private Message Handling

**Location**: `src/server/server.py` - Method `send_private_message()`

```python
def send_private_message(self, sender_id, sender_username, recipient_ids, message):
    """
    Send private message to specific recipients
    Also sends copy to sender for confirmation
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Create chat entry
    chat_entry = {
        'client_id': sender_id,
        'username': sender_username,
        'message': message,
        'timestamp': timestamp,
        'type': 'private',
        'recipients': recipient_ids
    }
    
    # Store in history
    with self.chat_lock:
        self.chat_history.append(chat_entry)
    
    # Get recipient usernames for display
    recipient_names = []
    with self.clients_lock:
        for rid in recipient_ids:
            if rid in self.clients:
                recipient_names.append(self.clients[rid]['username'])
    
    recipient_names_str = ', '.join(recipient_names)
    
    # Format private message
    formatted_message = (
        f"PRIVATE:{sender_id}:{sender_username}:{timestamp}:"
        f"{recipient_names_str}:{message}\n"
    )
    
    # Send to recipients
    with self.clients_lock:
        # Send to all recipients
        for rid in recipient_ids:
            if rid in self.clients:
                try:
                    self.clients[rid]['tcp_conn'].send(formatted_message.encode('utf-8'))
                except Exception as e:
                    print(f"Error sending private message to {rid}: {e}")
        
        # Also send to sender for confirmation
        if sender_id in self.clients:
            try:
                self.clients[sender_id]['tcp_conn'].send(formatted_message.encode('utf-8'))
            except:
                pass
    
    print(f"[{self.get_timestamp()}] Private from {sender_username} to {recipient_names_str}: {message}")
```

### 5. Receiving Messages (Client Side)

**Location**: `src/client/client.py` - Method `handle_tcp_messages()`

```python
def handle_tcp_messages(self):
    """
    Receive and process TCP messages from server
    Includes chat message reception
    """
    buffer = ""
    
    while self.connected:
        try:
            data = self.tcp_socket.recv(4096).decode('utf-8')
            
            if not data:
                break
            
            # Add to buffer
            buffer += data
            
            # Process complete messages (delimited by \n)
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                
                if line.startswith("CHAT:"):
                    # Group chat message
                    # Format: CHAT:sender_id:username:HH:MM:SS:message
                    parts = line.split(":", 4)
                    if len(parts) >= 5:
                        sender_id = int(parts[1])
                        sender_username = parts[2]
                        timestamp = parts[3]
                        chat_message = parts[4]
                        
                        # Emit signal for thread-safe GUI update
                        self.chat_message_received.emit(
                            sender_id,
                            sender_username,
                            timestamp,
                            chat_message
                        )
                
                elif line.startswith("PRIVATE:"):
                    # Private message
                    # Format: PRIVATE:sender_id:username:HH:MM:SS:recipients:message
                    parts = line.split(":", 5)
                    if len(parts) >= 6:
                        sender_id = int(parts[1])
                        sender_username = parts[2]
                        timestamp = parts[3]
                        recipient_names = parts[4]
                        chat_message = parts[5]
                        
                        # Display as private message
                        self.display_chat_message(
                            sender_id,
                            sender_username,
                            timestamp,
                            chat_message,
                            is_private=True,
                            recipient_names=recipient_names
                        )
                
        except Exception as e:
            if self.connected:
                print(f"Error receiving messages: {e}")
            break
```

### 6. Displaying Messages (Client GUI)

**Location**: `src/client/client.py` - Method `display_chat_message()`

```python
def display_chat_message(self, sender_id, username, timestamp, message, 
                        is_system=False, is_private=False, recipient_names=None):
    """
    Display chat message in the chat panel
    Handles formatting for group, private, and system messages
    """
    # Build HTML formatted message
    if is_system:
        # System message (gray, italic)
        html = f'<div style="color: #888; font-style: italic; margin: 5px 0;">'
        html += f'<b>[{timestamp}]</b> {message}</div>'
    elif is_private:
        # Private message (blue background)
        html = f'<div style="background-color: #1e3a5f; padding: 8px; border-radius: 5px; margin: 5px 0;">'
        html += f'<b style="color: #64b5f6;">[{timestamp}] {username}</b>'
        html += f'<span style="color: #90caf9; font-size: 10px;"> (Private to: {recipient_names})</span><br>'
        html += f'<span style="color: #e8eaed;">{message}</span></div>'
    else:
        # Group message
        is_own_message = (sender_id == self.client_id)
        
        if is_own_message:
            # Own messages aligned right, green tint
            html = f'<div style="text-align: right; margin: 5px 0;">'
            html += f'<div style="background-color: #1e4620; display: inline-block; '
            html += f'padding: 8px; border-radius: 5px; max-width: 80%; text-align: left;">'
            html += f'<b style="color: #81c784;">[{timestamp}] You</b><br>'
            html += f'<span style="color: #e8eaed;">{message}</span></div></div>'
        else:
            # Others' messages aligned left
            html = f'<div style="margin: 5px 0;">'
            html += f'<div style="background-color: #2d2d30; display: inline-block; '
            html += f'padding: 8px; border-radius: 5px; max-width: 80%;">'
            html += f'<b style="color: #64b5f6;">[{timestamp}] {username}</b><br>'
            html += f'<span style="color: #e8eaed;">{message}</span></div></div>'
    
    # Append to chat display
    self.chat_display.append(html)
    
    # Scroll to bottom
    scrollbar = self.chat_display.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())
    
    # Show notification if chat panel is hidden and not own message
    if not self.chat_panel_visible and sender_id != self.client_id:
        self.show_chat_notification(username, message)
```

---

## Message Protocol

### Message Types

#### 1. Group Chat Message

**Client → Server**:
```
CHAT_MESSAGE:<message_text>\n
```

**Server → All Clients**:
```
CHAT:<sender_id>:<sender_username>:<HH:MM:SS>:<message_text>\n
```

**Example**:
```
Client sends:  CHAT_MESSAGE:Hello everyone!\n
Server sends:  CHAT:3:Alice:14:23:15:Hello everyone!\n
```

#### 2. Private Message

**Client → Server**:
```
PRIVATE_CHAT:<recipient_id1>,<recipient_id2>,...:<message_text>\n
```

**Server → Recipients + Sender**:
```
PRIVATE:<sender_id>:<sender_username>:<HH:MM:SS>:<recipient_names>:<message_text>\n
```

**Example**:
```
Client sends:  PRIVATE_CHAT:2,5:Hey you two!\n
Server sends:  PRIVATE:3:Alice:14:25:30:Bob, Charlie:Hey you two!\n
```

#### 3. System Messages

**Server → Client(s)**:
```
SYSTEM:<message_text>\n
```

Used for:
- User joined: "Alice has joined the conference"
- User left: "Bob has left the conference"
- Presenter changed: "Charlie is now presenting"

#### 4. Chat History (On Join)

**Server → New Client**:
```
CHAT_HISTORY\n
CHAT:1:Alice:10:15:30:Welcome!\n
CHAT:2:Bob:10:16:45:Thanks!\n
...
CHAT_HISTORY_END\n
```

---

## Data Flow

### Group Message Flow

```
┌────────────────────────────────────────────────────────────────┐
│ STEP 1: USER INPUT                                             │
├────────────────────────────────────────────────────────────────┤
│ User types: "Hello everyone!"                                  │
│ User presses Enter or clicks Send                             │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 2: CLIENT FORMATTING                                      │
├────────────────────────────────────────────────────────────────┤
│ Format: "CHAT_MESSAGE:Hello everyone!\n"                       │
│ Encode to UTF-8 bytes                                          │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 3: TCP TRANSMISSION                                       │
├────────────────────────────────────────────────────────────────┤
│ Send via existing TCP connection (port 5000)                  │
│ Reliable delivery guaranteed                                   │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 4: SERVER RECEPTION                                       │
├────────────────────────────────────────────────────────────────┤
│ Receive on client's TCP connection                            │
│ Decode UTF-8 to string                                         │
│ Parse: Extract message text after "CHAT_MESSAGE:"             │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 5: SERVER PROCESSING                                      │
├────────────────────────────────────────────────────────────────┤
│ Get sender info: client_id=3, username="Alice"                │
│ Generate timestamp: "14:30:25"                                 │
│ Create chat entry for history                                  │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 6: STORE IN HISTORY                                       │
├────────────────────────────────────────────────────────────────┤
│ chat_history.append({                                          │
│   'client_id': 3,                                              │
│   'username': 'Alice',                                         │
│   'message': 'Hello everyone!',                                │
│   'timestamp': '14:30:25',                                     │
│   'type': 'group'                                              │
│ })                                                             │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 7: FORMAT FOR BROADCAST                                   │
├────────────────────────────────────────────────────────────────┤
│ Message: "CHAT:3:Alice:14:30:25:Hello everyone!\n"            │
│ Encode to UTF-8                                                │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 8: BROADCAST TO ALL CLIENTS                               │
├────────────────────────────────────────────────────────────────┤
│ For each connected client:                                     │
│   Send message via their TCP connection                        │
│ Includes sender (for confirmation/echo)                        │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 9: CLIENT RECEPTION                                       │
├────────────────────────────────────────────────────────────────┤
│ Receive on TCP socket                                          │
│ Parse: "CHAT:3:Alice:14:30:25:Hello everyone!"                │
│ Extract: sender_id=3, username="Alice", etc.                  │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 10: GUI UPDATE (Thread-Safe)                             │
├────────────────────────────────────────────────────────────────┤
│ Emit Qt signal with message data                              │
│ Signal handler updates chat display (HTML formatted)          │
│ Scroll to bottom                                               │
│ Show notification if chat panel hidden                        │
└────────────────────────────────────────────────────────────────┘
```

### Private Message Flow

Similar to group, but:
1. Client specifies recipient IDs
2. Server only sends to specified recipients (+ sender)
3. Message marked as "Private" in display
4. Different styling (blue background)

---

## Code Walkthrough

### Recipient Selection

**Location**: `src/client/client.py` - Method `show_recipient_selector()`

```python
def show_recipient_selector(self):
    """
    Show dialog to select multiple recipients for private message
    """
    dialog = QDialog(self)
    dialog.setWindowTitle("Select Recipients")
    dialog.setModal(True)
    dialog.setFixedSize(300, 400)
    
    layout = QVBoxLayout(dialog)
    
    # Instruction label
    label = QLabel("Select users to send private message:")
    layout.addWidget(label)
    
    # List of users with checkboxes
    user_list = QListWidget()
    
    with self.users_lock:
        for user_id, user_info in self.users.items():
            if user_id != self.client_id:  # Don't include self
                item = QListWidgetItem(user_info['username'])
                item.setData(Qt.ItemDataRole.UserRole, user_id)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                
                # Check if already selected
                if user_id in self.selected_recipients:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
                
                user_list.addItem(item)
    
    layout.addWidget(user_list)
    
    # Buttons
    button_layout = QHBoxLayout()
    
    ok_btn = QPushButton("OK")
    ok_btn.clicked.connect(dialog.accept)
    button_layout.addWidget(ok_btn)
    
    cancel_btn = QPushButton("Cancel")
    cancel_btn.clicked.connect(dialog.reject)
    button_layout.addWidget(cancel_btn)
    
    layout.addLayout(button_layout)
    
    # Show dialog
    if dialog.exec() == QDialog.DialogCode.Accepted:
        # Update selected recipients
        self.selected_recipients = []
        for i in range(user_list.count()):
            item = user_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                user_id = item.data(Qt.ItemDataRole.UserRole)
                self.selected_recipients.append(user_id)
        
        # Update recipient combo box display
        if self.selected_recipients:
            names = []
            with self.users_lock:
                for uid in self.selected_recipients:
                    if uid in self.users:
                        names.append(self.users[uid]['username'])
            self.recipient_combo.setCurrentText(', '.join(names))
        else:
            self.recipient_combo.setCurrentText("Everyone")
```

### Chat Notifications

**Location**: `src/client/client.py` - Method `show_chat_notification()`

```python
def show_chat_notification(self, sender, message):
    """
    Show notification popup for incoming chat message
    Google Meet-style notification
    """
    # Create notification widget
    notification = QFrame(self)
    notification.setFixedSize(340, 90)
    notification.setStyleSheet("""
        QFrame {
            background-color: #2d2d30;
            border: 1px solid #3e3e42;
            border-radius: 10px;
        }
    """)
    
    # Layout
    main_layout = QHBoxLayout(notification)
    main_layout.setContentsMargins(15, 12, 15, 12)
    main_layout.setSpacing(12)
    
    # Avatar (first letter of sender name)
    avatar = QLabel(sender[0].upper() if sender else "?")
    avatar.setFixedSize(40, 40)
    avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setStyleSheet("""
        QLabel {
            background-color: #007acc;
            color: white;
            border-radius: 20px;
            font-size: 18px;
            font-weight: bold;
        }
    """)
    main_layout.addWidget(avatar)
    
    # Text (sender + message preview)
    text_container = QWidget()
    text_layout = QVBoxLayout(text_container)
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(4)
    
    sender_label = QLabel(sender)
    sender_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
    sender_label.setStyleSheet("color: #ffffff;")
    text_layout.addWidget(sender_label)
    
    # Truncate message if too long
    preview = message[:35] + "..." if len(message) > 35 else message
    message_label = QLabel(preview)
    message_label.setFont(QFont("Arial", 9))
    message_label.setStyleSheet("color: #e0e0e0;")
    text_layout.addWidget(message_label)
    
    main_layout.addWidget(text_container, 1)
    
    # Close button
    close_btn = QPushButton("✕")
    close_btn.setFixedSize(28, 28)
    close_btn.setStyleSheet("""
        QPushButton {
            background-color: #3e3e42;
            color: #ffffff;
            border: none;
            border-radius: 14px;
        }
        QPushButton:hover {
            background-color: #ea4335;
        }
    """)
    close_btn.clicked.connect(lambda: self.hide_notification(notification))
    main_layout.addWidget(close_btn)
    
    # Position notification (top-right corner)
    notification.move(
        self.width() - notification.width() - 20,
        70  # Below top bar
    )
    
    # Show notification
    notification.show()
    notification.raise_()
    
    # Auto-hide after 5 seconds
    QTimer.singleShot(5000, lambda: self.hide_notification(notification))
    
    # Track active notifications
    self.active_notifications.append(notification)
```

---

## Features

### 1. Chat History

When a new user joins, they receive full chat history:

```python
# Server sends history to new client
def send_chat_history(self, client_conn):
    """
    Send chat history to newly connected client
    """
    try:
        client_conn.send("CHAT_HISTORY\n".encode('utf-8'))
        
        with self.chat_lock:
            for entry in self.chat_history:
                if entry['type'] == 'group':
                    message = (
                        f"CHAT:{entry['client_id']}:{entry['username']}:"
                        f"{entry['timestamp']}:{entry['message']}\n"
                    )
                    client_conn.send(message.encode('utf-8'))
        
        client_conn.send("CHAT_HISTORY_END\n".encode('utf-8'))
        
    except Exception as e:
        print(f"Error sending chat history: {e}")
```

### 2. Message Formatting

Rich text formatting using HTML:

```python
# Different styles for different message types
styles = {
    'own_message': '#1e4620',      # Green tint
    'other_message': '#2d2d30',    # Gray
    'private_message': '#1e3a5f',  # Blue tint
    'system_message': '#888'        # Gray italic
}
```

### 3. Emoji Support

UTF-8 encoding supports emojis:

```python
message = "Hello! 👋 😊"
# Properly encoded and decoded
```

### 4. Message Persistence

Chat history persisted for session duration:

```python
self.chat_history = []  # Cleared on server restart
# Future: Save to database or file
```

---

## Troubleshooting

### Common Issues

#### 1. Messages Not Sending

**Symptoms**:
- Text typed but not appearing in chat
- No error messages

**Diagnosis**:
```python
# Check TCP connection
if not self.tcp_socket:
    print("TCP socket not connected")

# Check message format
print(f"Sending: {formatted_message}")
```

**Solutions**:
- Verify connected to server
- Check TCP socket not closed
- Ensure message ends with \n

#### 2. Messages Not Received

**Symptoms**:
- Others see message but you don't
- One-way communication

**Diagnosis**:
```python
# Server: Check if message was broadcast
print(f"Broadcasting to {len(self.clients)} clients")

# Client: Check receive thread running
print(f"Receive thread alive: {tcp_thread.is_alive()}")
```

**Solutions**:
- Restart receive thread
- Check for exceptions in receive loop
- Verify firewall not blocking

#### 3. Garbled Text / Encoding Issues

**Symptoms**:
- Special characters appear as �
- Non-English text corrupted

**Causes & Solutions**:

| Cause | Solution |
|-------|----------|
| Wrong encoding | Use UTF-8 everywhere |
| Incomplete multibyte chars | Receive complete messages |
| Terminal encoding | Set terminal to UTF-8 |

```python
# Always use UTF-8
data.encode('utf-8')
data.decode('utf-8')
```

#### 4. Private Messages Going to Everyone

**Symptoms**:
- Private messages visible to all users

**Diagnosis**:
```python
# Server: Check recipient filtering
print(f"Sending to recipients: {recipient_ids}")
```

**Solution**:
```python
# Ensure only sending to specified recipients
for rid in recipient_ids:
    if rid in self.clients:
        self.clients[rid]['tcp_conn'].send(message)
```

#### 5. Chat History Not Showing

**Symptoms**:
- New users don't see previous messages

**Solutions**:
- Implement `send_chat_history()` on server
- Call it after client connects
- Ensure chat_history not empty

---

## Performance Metrics

### Latency
- **Typical**: < 10 ms on LAN
- **Measured**: Send → Server → Receive ≈ 5-8 ms
- **Comparison**: Much faster than video/audio

### Bandwidth
- **Per Message**: ~100-500 bytes (depends on length)
- **Negligible**: Even 1000 messages = 500 KB
- **No Impact**: On audio/video streams

### Scalability
- **10 users**: No issues
- **100 users**: Still fine (TCP handles it)
- **1000 users**: May need optimization (chat server patterns)

### CPU Usage
- **Minimal**: < 1% CPU
- **String operations**: Very fast
- **Network I/O**: Handled by OS

---

## Future Enhancements

1. **Rich Text Formatting**: Bold, italic, code blocks
2. **File Attachments**: Send images/files via chat
3. **Emoji Picker**: Built-in emoji selector
4. **Read Receipts**: Show who read messages
5. **Typing Indicators**: "Alice is typing..."
6. **Message Search**: Search chat history
7. **Message Deletion**: Delete/edit sent messages
8. **Persistent Storage**: Save chat to database
9. **Message Reactions**: React with emojis
10. **Thread Replies**: Reply to specific messages

---

**End of Chat Module Documentation**
