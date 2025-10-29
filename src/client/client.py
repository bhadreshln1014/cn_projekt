"""
Client Application for LAN-Based Multi-User Communication
Handles video capture, transmission, receiving, and GUI
"""

import socket
import threading
import time
import pickle
import struct
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import *


class VideoConferenceClient:
    def __init__(self):
        # Network
        self.tcp_socket = None
        self.udp_socket = None
        self.server_address = None
        self.client_id = None
        self.username = None
        self.connected = False
        
        # Video capture
        self.camera = None
        self.capturing = False
        
        # Video streams: {client_id: frame_data}
        self.video_streams = {}
        self.streams_lock = threading.Lock()
        
        # User list
        self.users = {}
        self.users_lock = threading.Lock()
        
        # GUI
        self.root = None
        self.video_labels = {}
        
    def connect_to_server(self, server_ip, username):
        """Connect to the server"""
        try:
            self.username = username
            self.server_address = server_ip
            
            # Create TCP socket for control
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((server_ip, SERVER_TCP_PORT))
            
            # Send connection request
            self.tcp_socket.send(f"CONNECT:{username}".encode('utf-8'))
            
            # Receive client ID
            response = self.tcp_socket.recv(1024).decode('utf-8')
            if response.startswith("ID:"):
                self.client_id = int(response.split(":", 1)[1])
                self.connected = True
                
                print(f"[{self.get_timestamp()}] Connected to server with ID: {self.client_id}")
                
                # Create UDP socket for video
                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
                # Start receiver threads
                tcp_thread = threading.Thread(target=self.receive_control_messages, daemon=True)
                tcp_thread.start()
                
                udp_thread = threading.Thread(target=self.receive_video_streams, daemon=True)
                udp_thread.start()
                
                return True
            else:
                print(f"[{self.get_timestamp()}] Failed to connect to server")
                return False
                
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error connecting to server: {e}")
            return False
    
    def get_timestamp(self):
        """Get formatted timestamp"""
        return datetime.now().strftime("%H:%M:%S")
    
    def start_video_capture(self):
        """Start capturing video from webcam"""
        try:
            self.camera = cv2.VideoCapture(0)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
            self.camera.set(cv2.CAP_PROP_FPS, VIDEO_FPS)
            
            if not self.camera.isOpened():
                print(f"[{self.get_timestamp()}] Failed to open camera")
                return False
            
            self.capturing = True
            
            # Start capture thread
            capture_thread = threading.Thread(target=self.capture_and_send, daemon=True)
            capture_thread.start()
            
            print(f"[{self.get_timestamp()}] Video capture started")
            return True
            
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error starting video capture: {e}")
            return False
    
    def capture_and_send(self):
        """Capture frames and send to server"""
        while self.capturing and self.connected:
            try:
                ret, frame = self.camera.read()
                
                if not ret:
                    continue
                
                # Resize frame
                frame = cv2.resize(frame, (VIDEO_WIDTH, VIDEO_HEIGHT))
                
                # Compress frame to JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), VIDEO_QUALITY]
                result, encoded_frame = cv2.imencode('.jpg', frame, encode_param)
                
                if result:
                    # Prepend client_id to the frame data
                    frame_data = struct.pack('I', self.client_id) + encoded_frame.tobytes()
                    
                    # Send via UDP
                    self.udp_socket.sendto(frame_data, (self.server_address, SERVER_UDP_PORT))
                
                # Control frame rate
                time.sleep(1.0 / VIDEO_FPS)
                
            except Exception as e:
                print(f"[{self.get_timestamp()}] Error capturing/sending video: {e}")
                time.sleep(0.1)
    
    def receive_control_messages(self):
        """Receive control messages from server via TCP"""
        buffer = ""
        
        while self.connected:
            try:
                data = self.tcp_socket.recv(4096).decode('utf-8')
                
                if not data:
                    break
                
                buffer += data
                
                # Process messages (simple line-based protocol)
                while '\n' in buffer or len(buffer) > 0:
                    if '\n' in buffer:
                        message, buffer = buffer.split('\n', 1)
                    else:
                        message = buffer
                        buffer = ""
                    
                    if message.startswith("USERS:"):
                        # Update user list
                        user_data = message.split(":", 1)[1]
                        try:
                            users = pickle.loads(bytes.fromhex(user_data))
                            with self.users_lock:
                                self.users = {u['id']: u['username'] for u in users}
                        except:
                            pass
                    
                    if not '\n' in (buffer + data):
                        break
                        
            except Exception as e:
                if self.connected:
                    print(f"[{self.get_timestamp()}] Error receiving control messages: {e}")
                break
    
    def receive_video_streams(self):
        """Receive video streams from server via UDP"""
        print(f"[{self.get_timestamp()}] UDP video receiver started")
        
        while self.connected:
            try:
                data, addr = self.udp_socket.recvfrom(MAX_PACKET_SIZE)
                
                if len(data) < 4:
                    continue
                
                # Extract client_id
                client_id = struct.unpack('I', data[:4])[0]
                frame_data = data[4:]
                
                # Decode frame
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    with self.streams_lock:
                        self.video_streams[client_id] = frame
                
            except Exception as e:
                if self.connected:
                    print(f"[{self.get_timestamp()}] Error receiving video stream: {e}")
    
    def create_gui(self):
        """Create the GUI"""
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Top bar with connection info
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_label = ttk.Label(top_frame, text="Not Connected", font=("Arial", 10))
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.user_count_label = ttk.Label(top_frame, text="Users: 0", font=("Arial", 10))
        self.user_count_label.pack(side=tk.RIGHT, padx=5)
        
        # Video grid frame
        self.video_frame = ttk.Frame(main_frame, relief=tk.SUNKEN, borderwidth=2)
        self.video_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure video grid
        for i in range(3):
            self.video_frame.columnconfigure(i, weight=1)
            self.video_frame.rowconfigure(i, weight=1)
        
        # Create placeholder video labels
        self.create_video_grid()
        
        # Start GUI update loop
        self.update_gui()
        
        return self.root
    
    def create_video_grid(self):
        """Create a grid of video display labels"""
        positions = [
            (0, 0), (0, 1), (0, 2),
            (1, 0), (1, 1), (1, 2),
            (2, 0), (2, 1), (2, 2)
        ]
        
        for idx, (row, col) in enumerate(positions):
            # Container frame for each video
            container = ttk.Frame(self.video_frame, relief=tk.RAISED, borderwidth=1)
            container.grid(row=row, column=col, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Username label
            username_label = ttk.Label(container, text="", font=("Arial", 9, "bold"))
            username_label.pack(side=tk.TOP, pady=2)
            
            # Video label
            video_label = tk.Label(container, bg="black", text="No Video")
            video_label.pack(side=tk.TOP, expand=True, fill=tk.BOTH, padx=2, pady=2)
            
            self.video_labels[idx] = {
                'container': container,
                'username': username_label,
                'video': video_label,
                'client_id': None
            }
    
    def update_gui(self):
        """Update GUI with current video frames"""
        if not self.root:
            return
        
        try:
            # Update status
            if self.connected:
                self.status_label.config(text=f"Connected as: {self.username} (ID: {self.client_id})")
                
                with self.users_lock:
                    self.user_count_label.config(text=f"Users: {len(self.users)}")
            
            # Update video streams
            with self.streams_lock:
                client_ids = list(self.video_streams.keys())
            
            # Add self camera if capturing
            display_streams = {}
            
            # Self video (from camera)
            if self.capturing and self.camera is not None:
                ret, frame = self.camera.read()
                if ret:
                    display_streams[self.client_id] = frame
            
            # Other clients' video
            with self.streams_lock:
                for client_id, frame in self.video_streams.items():
                    display_streams[client_id] = frame
            
            # Update video grid
            for idx, label_info in self.video_labels.items():
                if idx < len(display_streams):
                    client_id = list(display_streams.keys())[idx]
                    frame = display_streams[client_id]
                    
                    # Get username
                    with self.users_lock:
                        username = self.users.get(client_id, f"User {client_id}")
                    
                    if client_id == self.client_id:
                        username = f"{username} (You)"
                    
                    # Update username label
                    label_info['username'].config(text=username)
                    
                    # Convert and display frame
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_resized = cv2.resize(frame_rgb, (320, 240))
                    
                    img = Image.fromarray(frame_resized)
                    imgtk = ImageTk.PhotoImage(image=img)
                    
                    label_info['video'].config(image=imgtk, text="")
                    label_info['video'].image = imgtk
                    label_info['client_id'] = client_id
                else:
                    # Clear unused slots
                    label_info['username'].config(text="")
                    label_info['video'].config(image="", text="No Video", bg="black")
                    label_info['video'].image = None
                    label_info['client_id'] = None
            
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error updating GUI: {e}")
        
        # Schedule next update
        if self.root:
            self.root.after(33, self.update_gui)  # ~30 FPS
    
    def on_closing(self):
        """Handle window closing"""
        self.disconnect()
        if self.root:
            self.root.destroy()
    
    def disconnect(self):
        """Disconnect from server"""
        print(f"[{self.get_timestamp()}] Disconnecting...")
        
        self.connected = False
        self.capturing = False
        
        # Release camera
        if self.camera is not None:
            self.camera.release()
        
        # Close sockets
        try:
            if self.tcp_socket:
                self.tcp_socket.close()
        except:
            pass
        
        try:
            if self.udp_socket:
                self.udp_socket.close()
        except:
            pass
        
        print(f"[{self.get_timestamp()}] Disconnected")


class ConnectionDialog:
    """Dialog for getting server IP and username"""
    def __init__(self, parent):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Connect to Server")
        self.dialog.geometry("350x200")
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Server IP
        ttk.Label(main_frame, text="Server IP Address:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.ip_entry = ttk.Entry(main_frame, width=30)
        self.ip_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
        self.ip_entry.insert(0, "127.0.0.1")  # Default to localhost
        
        # Username
        ttk.Label(main_frame, text="Username:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(main_frame, width=30)
        self.username_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
        self.username_entry.insert(0, "User")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Connect", command=self.on_connect).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key
        self.dialog.bind('<Return>', lambda e: self.on_connect())
        
        # Focus on IP entry
        self.ip_entry.focus()
    
    def on_connect(self):
        """Handle connect button"""
        server_ip = self.ip_entry.get().strip()
        username = self.username_entry.get().strip()
        
        if not server_ip:
            messagebox.showerror("Error", "Please enter server IP address")
            return
        
        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return
        
        self.result = (server_ip, username)
        self.dialog.destroy()
    
    def on_cancel(self):
        """Handle cancel button"""
        self.result = None
        self.dialog.destroy()
    
    def show(self):
        """Show dialog and return result"""
        self.dialog.wait_window()
        return self.result


def main():
    """Main entry point"""
    client = VideoConferenceClient()
    
    # Create GUI
    root = client.create_gui()
    
    # Show connection dialog
    dialog = ConnectionDialog(root)
    result = dialog.show()
    
    if result:
        server_ip, username = result
        
        # Connect to server
        if client.connect_to_server(server_ip, username):
            # Start video capture
            client.start_video_capture()
            
            # Run GUI
            root.mainloop()
        else:
            messagebox.showerror("Connection Error", "Failed to connect to server")
            root.destroy()
    else:
        root.destroy()


if __name__ == "__main__":
    main()
