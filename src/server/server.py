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
        
        # Audio buffers: {client_id: latest_audio_data}
        self.audio_buffers = {}
        self.audio_lock = threading.Lock()
        
        # Screen sharing state
        self.presenter_id = None  # ID of current presenter
        self.presenter_lock = threading.Lock()
        self.current_screen_frame = None  # Latest screen frame from presenter
        self.screen_frame_lock = threading.Lock()
        
        # Chat history: list of {'client_id': id, 'username': name, 'message': text, 'timestamp': time}
        self.chat_history = []
        self.chat_lock = threading.Lock()
        
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
            
            self.running = True
            
            print(f"[{self.get_timestamp()}] Server started")
            print(f"[{self.get_timestamp()}] TCP Control Port: {SERVER_TCP_PORT}")
            print(f"[{self.get_timestamp()}] UDP Video Port: {SERVER_UDP_PORT}")
            print(f"[{self.get_timestamp()}] UDP Audio Port: {SERVER_AUDIO_PORT}")
            print(f"[{self.get_timestamp()}] TCP Screen Sharing Control Port: {SERVER_SCREEN_PORT}")
            print(f"[{self.get_timestamp()}] UDP Screen Sharing Data Port: {SERVER_SCREEN_UDP_PORT}")
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
                            message_text = data.split(":", 1)[1]
                            self.broadcast_chat_message(client_id, username, message_text)
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
        
        while self.running:
            try:
                # Receive audio packet
                data, addr = self.audio_socket.recvfrom(MAX_PACKET_SIZE)
                
                if len(data) < 4:
                    continue
                
                # Extract client_id from packet (first 4 bytes)
                client_id = struct.unpack('I', data[:4])[0]
                audio_data = data[4:]
                
                # Update audio address for this client
                with self.clients_lock:
                    if client_id in self.clients:
                        self.clients[client_id]['audio_address'] = addr
                
                # Store the audio data
                with self.audio_lock:
                    self.audio_buffers[client_id] = audio_data
                
                # Mix and broadcast audio
                self.mix_and_broadcast_audio()
                
            except Exception as e:
                if self.running:
                    print(f"[{self.get_timestamp()}] Error receiving audio: {e}")
    
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
            message = f"USERS:{pickle.dumps(user_list).hex()}"
            
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
