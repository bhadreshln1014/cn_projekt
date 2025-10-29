"""
Server Application for LAN-Based Multi-User Communication
Handles video streaming, user session management, and broadcasting
"""

import socket
import threading
import time
import pickle
import struct
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
        
        # Connected clients: {client_id: {'tcp_conn': conn, 'address': addr, 'udp_address': udp_addr, 'username': name}}
        self.clients = {}
        self.client_id_counter = 0
        self.clients_lock = threading.Lock()
        
        # Video frames buffer: {client_id: latest_frame_data}
        self.video_frames = {}
        self.frames_lock = threading.Lock()
        
        self.running = False
        
    def start(self):
        """Start the server"""
        try:
            # Bind TCP socket
            self.tcp_socket.bind((SERVER_HOST, SERVER_TCP_PORT))
            self.tcp_socket.listen(MAX_USERS)
            
            # Bind UDP socket
            self.udp_socket.bind((SERVER_HOST, SERVER_UDP_PORT))
            
            self.running = True
            
            print(f"[{self.get_timestamp()}] Server started")
            print(f"[{self.get_timestamp()}] TCP Control Port: {SERVER_TCP_PORT}")
            print(f"[{self.get_timestamp()}] UDP Video Port: {SERVER_UDP_PORT}")
            print(f"[{self.get_timestamp()}] Waiting for connections...")
            
            # Start UDP video receiver thread
            udp_thread = threading.Thread(target=self.receive_video_streams, daemon=True)
            udp_thread.start()
            
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
