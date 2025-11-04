"""
Server Application for LAN-Based Multi-User Communication
Handles video streaming, audio mixing, user session management, and broadcasting
"""

import socket
import threading
import time
import pickle
import struct
import numpy as np
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import *


class VideoConferenceServer:
    def __init__(self):
        # TCP socket for control messages
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # UDP socket for video streaming
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # UDP socket for audio streaming
        self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.audio_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # TCP socket for screen sharing control
        self.screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.screen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # UDP socket for screen frame data
        self.screen_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.screen_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Connected clients: {client_id: {'tcp_conn': conn, 'address': addr, 'udp_address': udp_addr, 'audio_address': audio_addr, 'username': name}}
        self.clients = {}
        self.client_id_counter = 0
        self.clients_lock = threading.Lock()
        
        # Video frames buffer: {client_id: latest_frame_data}
        self.video_frames = {}
        self.frames_lock = threading.Lock()
        
        # Audio buffers: {client_id: audio_data}
        self.audio_buffers = {}
        self.audio_timestamps = {}  # Track when audio was last received from each client
        self.audio_lock = threading.Lock()
        
        # Screen sharing state
        self.presenter_id = None  # ID of current presenter
        self.presenter_lock = threading.Lock()
        self.current_screen_frame = None  # Latest screen frame from presenter
        self.screen_frame_lock = threading.Lock()
        
        # Chat history: list of {'client_id': id, 'username': name, 'message': text, 'timestamp': time}
        self.chat_history = []
        self.chat_lock = threading.Lock()
        
        # File sharing: {file_id: {'filename': name, 'size': bytes, 'uploader_id': id, 'uploader_name': name, 'data': bytes, 'timestamp': time}}
        self.shared_files = {}
        self.file_id_counter = 0
        self.files_lock = threading.Lock()
        
        # TCP socket for file transfers
        self.file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.file_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.running = False
        
    def start(self):
        """Start the server"""
        try:
            # Bind TCP socket
            self.tcp_socket.bind((SERVER_HOST, SERVER_TCP_PORT))
            self.tcp_socket.listen(MAX_USERS)
            
            # Bind UDP socket for video
            self.udp_socket.bind((SERVER_HOST, SERVER_UDP_PORT))
            
            # Bind UDP socket for audio
            self.audio_socket.bind((SERVER_HOST, SERVER_AUDIO_PORT))
            
            # Bind TCP socket for screen sharing control
            print(f"[{self.get_timestamp()}] Binding screen sharing control socket to port {SERVER_SCREEN_PORT}...")
            self.screen_socket.bind((SERVER_HOST, SERVER_SCREEN_PORT))
            self.screen_socket.listen(MAX_USERS)
            print(f"[{self.get_timestamp()}] Screen sharing control socket bound successfully")
            
            # Bind UDP socket for screen frame data
            self.screen_udp_socket.bind((SERVER_HOST, SERVER_SCREEN_UDP_PORT))
            
            # Bind TCP socket for file transfers
            self.file_socket.bind((SERVER_HOST, SERVER_FILE_PORT))
            self.file_socket.listen(MAX_USERS)
            
            self.running = True
            
            print(f"[{self.get_timestamp()}] Server started")
            print(f"[{self.get_timestamp()}] TCP Control Port: {SERVER_TCP_PORT}")
            print(f"[{self.get_timestamp()}] UDP Video Port: {SERVER_UDP_PORT}")
            print(f"[{self.get_timestamp()}] UDP Audio Port: {SERVER_AUDIO_PORT}")
            print(f"[{self.get_timestamp()}] TCP Screen Sharing Control Port: {SERVER_SCREEN_PORT}")
            print(f"[{self.get_timestamp()}] UDP Screen Sharing Data Port: {SERVER_SCREEN_UDP_PORT}")
            print(f"[{self.get_timestamp()}] TCP File Transfer Port: {SERVER_FILE_PORT}")
            print(f"[{self.get_timestamp()}] Waiting for connections...")
            
            # Start UDP video receiver thread
            udp_thread = threading.Thread(target=self.receive_video_streams, daemon=True)
            udp_thread.start()
            
            # Start UDP audio receiver/mixer thread
            audio_thread = threading.Thread(target=self.receive_and_mix_audio, daemon=True)
            audio_thread.start()
            
            # Start screen sharing control thread
            screen_control_thread = threading.Thread(target=self.accept_screen_connections, daemon=True)
            screen_control_thread.start()
            print(f"[{self.get_timestamp()}] Screen control thread started: {screen_control_thread.is_alive()}")
            
            # Start file transfer thread
            file_thread = threading.Thread(target=self.accept_file_connections, daemon=True)
            file_thread.start()
            
            # Start screen sharing UDP receiver thread
            screen_udp_thread = threading.Thread(target=self.receive_screen_streams, daemon=True)
            screen_udp_thread.start()
            print(f"[{self.get_timestamp()}] Screen UDP thread started: {screen_udp_thread.is_alive()}")
            
            # Start TCP connection acceptor
            self.accept_connections()
            
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error starting server: {e}")
            self.shutdown()
    
    def get_timestamp(self):
        """Get formatted timestamp"""
        return datetime.now().strftime("%H:%M:%S")
    
    def accept_connections(self):
        """Accept incoming TCP connections from clients"""
        while self.running:
            try:
                conn, address = self.tcp_socket.accept()
                
                # Start a thread to handle this client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, address),
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    print(f"[{self.get_timestamp()}] Error accepting connection: {e}")
    
    def handle_client(self, conn, address):
        """Handle a client TCP connection"""
        client_id = None
        
        try:
            # Receive initial connection message with username
            data = conn.recv(1024).decode('utf-8')
            
            if data.startswith("CONNECT:"):
                username = data.split(":", 1)[1]
                
                with self.clients_lock:
                    client_id = self.client_id_counter
                    self.client_id_counter += 1
                    
                    self.clients[client_id] = {
                        'tcp_conn': conn,
                        'address': address,
                        'udp_address': None,
                        'screen_udp_address': None,
                        'username': username
                    }
                
                # Send client ID back
                conn.send(f"ID:{client_id}".encode('utf-8'))
                
                print(f"[{self.get_timestamp()}] Client '{username}' connected from {address} (ID: {client_id})")
                
                # Broadcast user list to all clients
                self.broadcast_user_list()
                
                # Keep connection alive and handle control messages
                while self.running:
                    try:
                        data = conn.recv(1024).decode('utf-8')
                        if not data:
                            break
                        
                        # Handle control messages (heartbeat, etc.)
                        if data == "PING":
                            conn.send("PONG".encode('utf-8'))
                        elif data.startswith("CHAT:"):
                            # Chat message from client
                            message_text = data.split(":", 1)[1].strip()  # Strip newline
                            self.broadcast_chat_message(client_id, username, message_text)
                        elif data.startswith("PRIVATE_CHAT:"):
                            # Private chat message: PRIVATE_CHAT:recipient_ids:message
                            try:
                                parts = data.split(":", 2)  # PRIVATE_CHAT:recipient_ids:message
                                if len(parts) >= 3:
                                    recipient_ids_str = parts[1]
                                    message_text = parts[2].strip()  # Strip newline
                                    recipient_ids = [int(rid) for rid in recipient_ids_str.split(",")]
                                    self.send_private_message(client_id, username, recipient_ids, message_text)
                            except Exception as e:
                                print(f"[{self.get_timestamp()}] Error handling private chat: {e}")
                        elif data == "REQUEST_PRESENTER":
                            # Client wants to become presenter
                            with self.presenter_lock:
                                if self.presenter_id is None or self.presenter_id == client_id:
                                    conn.send("PRESENTER_OK\n".encode('utf-8'))
                                else:
                                    conn.send("PRESENTER_DENIED\n".encode('utf-8'))
                        elif data == "STOP_PRESENTING":
                            # Client wants to stop presenting
                            with self.presenter_lock:
                                if self.presenter_id == client_id:
                                    self.presenter_id = None
                                    self.broadcast_presenter_status()
                            
                    except:
                        break
                        
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error handling client: {e}")
        
        finally:
            # Clean up client
            if client_id is not None:
                with self.clients_lock:
                    if client_id in self.clients:
                        username = self.clients[client_id]['username']
                        del self.clients[client_id]
                        print(f"[{self.get_timestamp()}] Client '{username}' disconnected (ID: {client_id})")
                
                with self.frames_lock:
                    if client_id in self.video_frames:
                        del self.video_frames[client_id]
                
                # Clear presenter status if this client was presenting
                with self.presenter_lock:
                    if self.presenter_id == client_id:
                        self.presenter_id = None
                        self.broadcast_presenter_status()
                
                # Broadcast updated user list
                self.broadcast_user_list()
            
            try:
                conn.close()
            except:
                pass
    
    def receive_video_streams(self):
        """Receive video frames via UDP and broadcast to other clients"""
        print(f"[{self.get_timestamp()}] UDP video receiver started")
        
        while self.running:
            try:
                # Receive video packet
                data, addr = self.udp_socket.recvfrom(MAX_PACKET_SIZE)
                
                if len(data) < 4:
                    continue
                
                # Extract client_id from packet (first 4 bytes)
                client_id = struct.unpack('I', data[:4])[0]
                frame_data = data[4:]
                
                # Update UDP address for this client
                with self.clients_lock:
                    if client_id in self.clients:
                        self.clients[client_id]['udp_address'] = addr
                
                # Store the frame
                with self.frames_lock:
                    self.video_frames[client_id] = frame_data
                
                # Broadcast to all other clients
                self.broadcast_video_frame(client_id, data)
                
            except Exception as e:
                if self.running:
                    print(f"[{self.get_timestamp()}] Error receiving video: {e}")
    
    def broadcast_video_frame(self, sender_id, frame_data):
        """Broadcast a video frame to all clients except the sender"""
        with self.clients_lock:
            for client_id, client_info in self.clients.items():
                if client_id != sender_id and client_info['udp_address'] is not None:
                    try:
                        self.udp_socket.sendto(frame_data, client_info['udp_address'])
                    except Exception as e:
                        pass  # Silently ignore send errors
    
    def receive_and_mix_audio(self):
        """Receive audio streams from clients, mix them, and broadcast"""
        print(f"[{self.get_timestamp()}] Audio receiver/mixer started")
        
        # Track last broadcast time to control mixing rate
        last_broadcast_time = time.time()
        broadcast_interval = AUDIO_CHUNK / AUDIO_RATE  # Match the audio chunk timing
        
        while self.running:
            try:
                # Receive audio packet with timeout to allow periodic mixing
                self.audio_socket.settimeout(broadcast_interval / 2)
                
                try:
                    data, addr = self.audio_socket.recvfrom(MAX_PACKET_SIZE)
                    
                    if len(data) >= 4:
                        # Extract client_id from packet (first 4 bytes)
                        client_id = struct.unpack('I', data[:4])[0]
                        audio_data = data[4:]
                        
                        # Update audio address for this client
                        with self.clients_lock:
                            if client_id in self.clients:
                                self.clients[client_id]['audio_address'] = addr
                        
                        # Store the audio data with timestamp
                        current_time = time.time()
                        with self.audio_lock:
                            self.audio_buffers[client_id] = audio_data
                            self.audio_timestamps[client_id] = current_time
                except socket.timeout:
                    # Timeout is normal - just continue to mixing
                    pass
                
                # Mix and broadcast at regular intervals (not on every packet)
                current_time = time.time()
                if current_time - last_broadcast_time >= broadcast_interval:
                    # Clean up old audio buffers before mixing
                    with self.audio_lock:
                        stale_clients = []
                        for cid, timestamp in list(self.audio_timestamps.items()):
                            if current_time - timestamp > 0.5:
                                stale_clients.append(cid)
                        
                        for cid in stale_clients:
                            if cid in self.audio_buffers:
                                del self.audio_buffers[cid]
                            if cid in self.audio_timestamps:
                                del self.audio_timestamps[cid]
                    
                    # Mix and broadcast
                    self.mix_and_broadcast_audio()
                    last_broadcast_time = current_time
                
            except Exception as e:
                if self.running:
                    print(f"[{self.get_timestamp()}] Error receiving audio: {e}")
                    time.sleep(0.01)
    
    def mix_and_broadcast_audio(self):
        """Mix all audio streams and broadcast to all clients"""
        with self.audio_lock:
            if len(self.audio_buffers) == 0:
                return
            
            try:
                # Convert all audio buffers to numpy arrays with client mapping
                audio_data_map = {}
                for client_id, audio_data in self.audio_buffers.items():
                    # Convert bytes to int16 array
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    audio_data_map[client_id] = audio_array.astype(np.float32)
                
                # Broadcast to each client (excluding their own audio to prevent loopback)
                if len(audio_data_map) > 0:
                    with self.clients_lock:
                        for target_client_id, client_info in self.clients.items():
                            if client_info.get('audio_address') is not None:
                                # Collect audio from all clients EXCEPT the target client
                                audio_arrays = []
                                for source_client_id, audio_array in audio_data_map.items():
                                    if source_client_id != target_client_id:
                                        audio_arrays.append(audio_array)
                                
                                # If there's audio to send to this client
                                if len(audio_arrays) > 0:
                                    # Ensure all arrays have the same length
                                    min_length = min(len(arr) for arr in audio_arrays)
                                    audio_arrays = [arr[:min_length] for arr in audio_arrays]
                                    
                                    # Average all audio streams
                                    mixed_audio = np.mean(audio_arrays, axis=0)
                                    
                                    # Convert back to int16
                                    mixed_audio = np.clip(mixed_audio, -32768, 32767).astype(np.int16)
                                    mixed_data = mixed_audio.tobytes()
                                    
                                    try:
                                        self.audio_socket.sendto(mixed_data, client_info['audio_address'])
                                    except:
                                        pass  # Silently ignore send errors
                
            except Exception as e:
                print(f"[{self.get_timestamp()}] Error mixing audio: {e}")
    
    def broadcast_user_list(self):
        """Send updated user list to all connected clients"""
        with self.clients_lock:
            user_list = []
            for client_id, client_info in self.clients.items():
                user_list.append({
                    'id': client_id,
                    'username': client_info['username']
                })
            
            # Serialize user list
            message = f"USERS:{pickle.dumps(user_list).hex()}\n"
            
            # Send to all clients
            for client_id, client_info in self.clients.items():
                try:
                    client_info['tcp_conn'].send(message.encode('utf-8'))
                except:
                    pass
    
    def broadcast_chat_message(self, sender_id, sender_username, message):
        """Broadcast chat message to all connected clients"""
        timestamp = self.get_timestamp()
        
        # Store in chat history
        with self.chat_lock:
            chat_entry = {
                'client_id': sender_id,
                'username': sender_username,
                'message': message,
                'timestamp': timestamp
            }
            self.chat_history.append(chat_entry)
        
        # Format message for broadcast
        chat_msg = f"CHAT:{sender_id}:{sender_username}:{timestamp}:{message}\n"
        
        # Send to all clients
        with self.clients_lock:
            for client_id, client_info in self.clients.items():
                try:
                    client_info['tcp_conn'].send(chat_msg.encode('utf-8'))
                except Exception as e:
                    print(f"[{self.get_timestamp()}] Error sending chat to client {client_id}: {e}")
        
        print(f"[{timestamp}] Chat from {sender_username}: {message}")
    
    def send_private_message(self, sender_id, sender_username, recipient_ids, message):
        """Send private message to specific recipients"""
        timestamp = self.get_timestamp()
        
        # Format message for private chat
        # PRIVATE_CHAT:sender_id|sender_username|timestamp|recipient_ids|message
        # Using | to separate fields since timestamp contains colons
        recipient_ids_str = ",".join(map(str, recipient_ids))
        private_msg = f"PRIVATE_CHAT:{sender_id}|{sender_username}|{timestamp}|{recipient_ids_str}|{message}\n"
        
        # Send to sender (so they see their own message)
        with self.clients_lock:
            if sender_id in self.clients:
                try:
                    self.clients[sender_id]['tcp_conn'].send(private_msg.encode('utf-8'))
                except Exception as e:
                    print(f"[{self.get_timestamp()}] Error sending private chat to sender {sender_id}: {e}")
            
            # Send to each recipient
            for recipient_id in recipient_ids:
                if recipient_id in self.clients:
                    try:
                        self.clients[recipient_id]['tcp_conn'].send(private_msg.encode('utf-8'))
                    except Exception as e:
                        print(f"[{self.get_timestamp()}] Error sending private chat to recipient {recipient_id}: {e}")
        
        recipient_names = [self.clients.get(rid, {}).get('username', f'User{rid}') for rid in recipient_ids]
        print(f"[{timestamp}] Private chat from {sender_username} to {', '.join(recipient_names)}: {message}")
    
    def accept_file_connections(self):
        """Accept file transfer connections"""
        print(f"[{self.get_timestamp()}] File transfer acceptor started on port {SERVER_FILE_PORT}")
        
        while self.running:
            try:
                self.file_socket.settimeout(2.0)
                try:
                    conn, addr = self.file_socket.accept()
                    print(f"[{self.get_timestamp()}] File transfer connection from {addr}")
                    
                    # Start thread to handle this file transfer
                    thread = threading.Thread(target=self.handle_file_transfer, args=(conn, addr), daemon=True)
                    thread.start()
                except socket.timeout:
                    continue
                    
            except Exception as e:
                if self.running:
                    print(f"[{self.get_timestamp()}] Error in file acceptor: {e}")
                break
    
    def handle_file_transfer(self, conn, address):
        """Handle file upload or download"""
        try:
            # Receive command: UPLOAD or DOWNLOAD:file_id
            # Read until we get a newline to separate command from file data
            command_bytes = b''
            while b'\n' not in command_bytes:
                chunk = conn.recv(1024)
                if not chunk:
                    return
                command_bytes += chunk
            
            # Split at first newline to separate command from any file data
            command, _, remaining = command_bytes.partition(b'\n')
            command = command.decode('utf-8').strip()
            
            if command.startswith("UPLOAD:"):
                # Format: UPLOAD:client_id:filename:filesize
                parts = command.split(":", 3)
                if len(parts) >= 4:
                    client_id = int(parts[1])
                    filename = parts[2]
                    filesize = int(parts[3])
                    
                    print(f"[{self.get_timestamp()}] Receiving file '{filename}' ({filesize} bytes) from client {client_id}")
                    
                    # Receive file data - start with any data already received
                    file_data = remaining  # Any extra data from the command recv
                    remaining = filesize - len(file_data)
                    
                    while remaining > 0:
                        chunk_size = min(FILE_CHUNK_SIZE, remaining)
                        chunk = conn.recv(chunk_size)
                        if not chunk:
                            break
                        file_data += chunk
                        remaining -= len(chunk)
                    
                    if len(file_data) == filesize:
                        # Store file
                        with self.files_lock:
                            file_id = self.file_id_counter
                            self.file_id_counter += 1
                            
                            uploader_name = self.clients.get(client_id, {}).get('username', f'User{client_id}')
                            
                            self.shared_files[file_id] = {
                                'filename': filename,
                                'size': filesize,
                                'uploader_id': client_id,
                                'uploader_name': uploader_name,
                                'data': file_data,
                                'timestamp': self.get_timestamp()
                            }
                        
                        # Send success response
                        conn.send(f"SUCCESS:{file_id}".encode('utf-8'))
                        
                        # Broadcast file availability to all clients
                        self.broadcast_file_offer(file_id, filename, filesize, uploader_name, client_id)
                        
                        print(f"[{self.get_timestamp()}] File '{filename}' stored with ID {file_id}")
                    else:
                        conn.send("ERROR:Incomplete file".encode('utf-8'))
                        print(f"[{self.get_timestamp()}] File upload failed: incomplete data")
                        
            elif command.startswith("DOWNLOAD:"):
                # Format: DOWNLOAD:file_id
                file_id = int(command.split(":", 1)[1])
                
                with self.files_lock:
                    if file_id in self.shared_files:
                        file_info = self.shared_files[file_id]
                        filename = file_info['filename']
                        filesize = file_info['size']
                        file_data = file_info['data']
                        
                        # Send file info
                        conn.send(f"FILE:{filename}:{filesize}\n".encode('utf-8'))
                        
                        # Send file data in chunks
                        offset = 0
                        while offset < filesize:
                            chunk_size = min(FILE_CHUNK_SIZE, filesize - offset)
                            chunk = file_data[offset:offset + chunk_size]
                            conn.sendall(chunk)
                            offset += chunk_size
                        
                        print(f"[{self.get_timestamp()}] Sent file '{filename}' (ID: {file_id})")
                    else:
                        conn.send("ERROR:File not found\n".encode('utf-8'))
            
            elif command.startswith("DELETE:"):
                # Format: DELETE:file_id:client_id
                parts = command.split(":", 2)
                if len(parts) >= 3:
                    file_id = int(parts[1])
                    client_id = int(parts[2])
                    
                    with self.files_lock:
                        if file_id in self.shared_files:
                            file_info = self.shared_files[file_id]
                            uploader_id = file_info['uploader_id']
                            
                            # Only allow uploader to delete
                            if uploader_id == client_id:
                                filename = file_info['filename']
                                del self.shared_files[file_id]
                                conn.send(f"DELETE_SUCCESS:{file_id}".encode('utf-8'))
                                
                                # Broadcast deletion to all clients
                                self.broadcast_file_deletion(file_id, filename)
                                print(f"[{self.get_timestamp()}] File '{filename}' (ID: {file_id}) deleted by client {client_id}")
                            else:
                                conn.send("ERROR:Not authorized to delete this file".encode('utf-8'))
                        else:
                            conn.send("ERROR:File not found".encode('utf-8'))
                        
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error in file transfer handler: {e}")
        finally:
            try:
                conn.close()
            except:
                pass
    
    def broadcast_file_offer(self, file_id, filename, filesize, uploader_name, uploader_id):
        """Broadcast file availability to all clients"""
        message = f"FILE_OFFER:{file_id}:{filename}:{filesize}:{uploader_name}:{uploader_id}\n"
        
        with self.clients_lock:
            for client_id, client_info in self.clients.items():
                try:
                    client_info['tcp_conn'].send(message.encode('utf-8'))
                except Exception as e:
                    print(f"[{self.get_timestamp()}] Error broadcasting file offer to client {client_id}: {e}")
        
        print(f"[{self.get_timestamp()}] Broadcasted file offer: {filename} from {uploader_name}")
    
    def broadcast_file_deletion(self, file_id, filename):
        """Broadcast file deletion to all clients"""
        message = f"FILE_DELETED:{file_id}\n"
        
        with self.clients_lock:
            for client_id, client_info in self.clients.items():
                try:
                    client_info['tcp_conn'].send(message.encode('utf-8'))
                except Exception as e:
                    print(f"[{self.get_timestamp()}] Error broadcasting file deletion to client {client_id}: {e}")
        
        print(f"[{self.get_timestamp()}] Broadcasted file deletion: {filename} (ID: {file_id})")
    
    def accept_screen_connections(self):
        """Accept screen sharing connections"""
        print(f"[{self.get_timestamp()}] Screen sharing acceptor started on port {SERVER_SCREEN_PORT}")
        print(f"[{self.get_timestamp()}] Socket listening: {self.screen_socket}")
        
        while self.running:
            try:
                print(f"[{self.get_timestamp()}] Waiting for screen sharing connection...")
                self.screen_socket.settimeout(2.0)  # Add timeout so we can see the loop is running
                try:
                    conn, addr = self.screen_socket.accept()
                    print(f"[{self.get_timestamp()}] *** SCREEN SHARING CONNECTION ACCEPTED from {addr} ***")
                    
                    # Start thread to handle this screen sharing connection
                    thread = threading.Thread(target=self.handle_screen_share, args=(conn, addr), daemon=True)
                    thread.start()
                    print(f"[{self.get_timestamp()}] Handler thread started for {addr}")
                except socket.timeout:
                    # Timeout is normal, just loop again
                    continue
                    
            except Exception as e:
                if self.running:
                    print(f"[{self.get_timestamp()}] Error accepting screen connection: {e}")
                    import traceback
                    traceback.print_exc()
    
    def handle_screen_share(self, conn, addr):
        """Handle screen sharing control from presenter"""
        client_id = None
        try:
            print(f"[{self.get_timestamp()}] handle_screen_share called for {addr}")
            
            # Receive client_id first
            client_id_data = conn.recv(4)
            print(f"[{self.get_timestamp()}] Received {len(client_id_data)} bytes for client_id")
            
            if len(client_id_data) < 4:
                print(f"[{self.get_timestamp()}] Insufficient data for client_id, closing")
                conn.close()
                return
            
            client_id = struct.unpack('I', client_id_data)[0]
            print(f"[{self.get_timestamp()}] Screen sharing request from client {client_id}")
            
            # Check if this client can be presenter
            print(f"[{self.get_timestamp()}] Acquiring presenter_lock...")
            with self.presenter_lock:
                print(f"[{self.get_timestamp()}] presenter_lock acquired. Current presenter_id: {self.presenter_id}")
                
                # Allow same client to reconnect (for restart), deny if different presenter exists
                if self.presenter_id is not None and self.presenter_id != client_id:
                    # Another user is already presenting
                    print(f"[{self.get_timestamp()}] Denying client {client_id} - presenter {self.presenter_id} exists")
                    conn.sendall(b"DENIED")
                    conn.close()
                    print(f"[{self.get_timestamp()}] DENIED sent and connection closed")
                    return
                
                # Clear old presenter status if reconnecting
                if self.presenter_id == client_id:
                    print(f"[{self.get_timestamp()}] Client {client_id} reconnecting as presenter")
                
                print(f"[{self.get_timestamp()}] Setting presenter_id to {client_id}")
                self.presenter_id = client_id
                print(f"[{self.get_timestamp()}] Sending GRANTED to client {client_id}")
                
                try:
                    conn.sendall(b"GRANTED")  # Use sendall to ensure it's sent
                    print(f"[{self.get_timestamp()}] GRANTED sent, client {client_id} is now the presenter")
                except Exception as send_err:
                    print(f"[{self.get_timestamp()}] ERROR sending GRANTED: {send_err}")
                    raise
            
            print(f"[{self.get_timestamp()}] Released presenter_lock")
            
            # Notify all clients about presenter change (do this AFTER releasing the lock)
            print(f"[{self.get_timestamp()}] Broadcasting presenter status...")
            self.broadcast_presenter_status()
            print(f"[{self.get_timestamp()}] Presenter status broadcast complete")
            
            # Keep connection alive - presenter will send frames via UDP
            # This connection is just for control and to detect disconnection
            while self.running:
                try:
                    conn.settimeout(0.5)  # Shorter timeout for faster response
                    data = conn.recv(1024)
                    if not data:
                        print(f"[{self.get_timestamp()}] Client {client_id} disconnected (no data)")
                        break
                    
                    # Handle STOP message - clear presenter IMMEDIATELY
                    if b"STOP" in data:
                        print(f"[{self.get_timestamp()}] Client {client_id} requested stop - clearing presenter immediately")
                        # Clear presenter_id quickly WITHOUT broadcasting inside the lock
                        with self.presenter_lock:
                            if self.presenter_id == client_id:
                                self.presenter_id = None
                        print(f"[{self.get_timestamp()}] Presenter cleared, now broadcasting...")
                        # Broadcast AFTER releasing the lock to avoid deadlock
                        self.broadcast_presenter_status()
                        print(f"[{self.get_timestamp()}] Client {client_id} STOP handled, breaking from loop")
                        break
                except socket.timeout:
                    # Timeout is normal, just loop again
                    continue
                except Exception as e:
                    print(f"[{self.get_timestamp()}] Error in screen share loop for client {client_id}: {e}")
                    break
            
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error in screen sharing control: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            print(f"[{self.get_timestamp()}] Entering finally block for client {client_id}")
            # Clean up presenter status (only if this client was the presenter and not already cleared)
            if client_id is not None:
                print(f"[{self.get_timestamp()}] Attempting to acquire presenter_lock in finally for cleanup...")
                with self.presenter_lock:
                    print(f"[{self.get_timestamp()}] presenter_lock acquired in finally")
                    if self.presenter_id == client_id:
                        self.presenter_id = None
                        print(f"[{self.get_timestamp()}] Client {client_id} stopped presenting - presenter_id cleared in finally")
                        self.broadcast_presenter_status()
                    else:
                        if self.presenter_id is None:
                            print(f"[{self.get_timestamp()}] Client {client_id} disconnected - presenter_id already cleared")
                        else:
                            print(f"[{self.get_timestamp()}] Client {client_id} disconnected but was not presenter (current: {self.presenter_id})")
            else:
                print(f"[{self.get_timestamp()}] Screen share connection closed before client_id received")
            
            try:
                conn.close()
                print(f"[{self.get_timestamp()}] Connection closed for client {client_id}")
            except:
                pass
            
            print(f"[{self.get_timestamp()}] handle_screen_share EXITING for client {client_id}")
    
    def receive_screen_streams(self):
        """Receive screen frames via UDP and broadcast to all clients"""
        print(f"[{self.get_timestamp()}] Screen UDP receiver started")
        
        while self.running:
            try:
                # Receive screen frame packet
                data, addr = self.screen_udp_socket.recvfrom(MAX_SCREEN_PACKET_SIZE)
                
                if len(data) < 4:
                    continue
                
                # Extract client_id (first 4 bytes)
                client_id = struct.unpack('I', data[:4])[0]
                frame_data = data[4:]
                
                # Learn client's screen UDP address
                with self.clients_lock:
                    if client_id in self.clients:
                        if self.clients[client_id]['screen_udp_address'] is None:
                            self.clients[client_id]['screen_udp_address'] = addr
                            print(f"[{self.get_timestamp()}] Learned screen UDP address for client {client_id}: {addr}")
                
                # Skip if this is just an initial packet with no frame data
                if len(frame_data) == 0:
                    continue
                
                # Verify this is the current presenter
                with self.presenter_lock:
                    if self.presenter_id != client_id:
                        continue  # Ignore frames from non-presenters
                
                # Broadcast to all clients
                self.broadcast_screen_frame(client_id, data)  # Send whole packet with client_id
                
            except Exception as e:
                if self.running:
                    print(f"[{self.get_timestamp()}] Error receiving screen frame: {e}")
    
    def recv_exact(self, conn, n):
        """Receive exactly n bytes from connection"""
        data = b''
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data
    
    def broadcast_screen_frame(self, presenter_id, frame_data):
        """Broadcast screen frame to all clients via UDP"""
        with self.clients_lock:
            for client_id, client_info in self.clients.items():
                # Send to all clients including presenter (for their own preview)
                if client_info['screen_udp_address'] is not None:
                    try:
                        self.screen_udp_socket.sendto(frame_data, client_info['screen_udp_address'])
                    except:
                        pass  # Client might have disconnected
    
    def broadcast_presenter_status(self):
        """Notify all clients about current presenter"""
        with self.presenter_lock:
            if self.presenter_id is not None:
                message = f"PRESENTER:{self.presenter_id}\n"
            else:
                message = "PRESENTER:None\n"
        
        with self.clients_lock:
            for client_id, client_info in self.clients.items():
                try:
                    client_info['tcp_conn'].send(message.encode('utf-8'))
                except:
                    pass
    
    def shutdown(self):
        """Shutdown the server gracefully"""
        print(f"\n[{self.get_timestamp()}] Shutting down server...")
        self.running = False
        
        # Close all client connections
        with self.clients_lock:
            for client_id, client_info in self.clients.items():
                try:
                    client_info['tcp_conn'].close()
                except:
                    pass
        
        # Close sockets
        try:
            self.tcp_socket.close()
        except:
            pass
        
        try:
            self.udp_socket.close()
        except:
            pass
        
        try:
            self.audio_socket.close()
        except:
            pass
        
        try:
            self.screen_socket.close()
        except:
            pass
        
        print(f"[{self.get_timestamp()}] Server stopped")


def main():
    server = VideoConferenceServer()
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[Server] Keyboard interrupt received")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
