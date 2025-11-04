"""
Client Application for LAN-Based Multi-User Communication
Handles video capture, audio capture, transmission, receiving, and GUI
"""

import socket
import threading
import time
import pickle
import struct
import cv2
import numpy as np
import pyaudio
from PIL import Image
from datetime import datetime
import mss
import os
import sys

# PyQt6 imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTextEdit, QLineEdit, QComboBox, QCheckBox,
    QGridLayout, QFrame, QDialog, QListWidget, QProgressBar, QMessageBox,
    QFileDialog, QScrollArea, QGroupBox, QListWidgetItem, QSizePolicy, QMenu
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QSize
from PyQt6.QtGui import QPixmap, QImage, QFont, QColor, QPalette, QIcon, QAction

# Try to import qtawesome for Material Design icons
try:
    import qtawesome as qta
    HAS_QTAWESOME = True
except ImportError:
    HAS_QTAWESOME = False
    print("QtAwesome not installed. Using emoji icons. Install with: pip install qtawesome")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import *


class VideoConferenceClient(QMainWindow):
    # Signals for thread-safe GUI updates
    chat_message_received = pyqtSignal(str, str, str)  # username, timestamp, message
    chat_debug_signal = pyqtSignal(str)  # debug message to display
    notification_signal = pyqtSignal(str, str)  # sender, message - for thread-safe notifications
    user_join_signal = pyqtSignal(str)  # username - for user join notifications
    
    def __init__(self):
        super().__init__()
        
        # Network
        self.tcp_socket = None
        self.udp_socket = None
        self.audio_udp_socket = None
        self.server_address = None
        self.client_id = None
        self.username = None
        self.connected = False
        
        # Video capture
        self.camera = None
        self.capturing = False
        
        # Audio
        self.audio = None
        self.audio_stream_input = None
        self.audio_stream_output = None
        self.audio_capturing = False
        self.audio_playing = False
        self.selected_input_device = None  # Will store device index
        self.selected_output_device = None  # Will store device index
        
        # Video streams: {client_id: frame_data}
        self.video_streams = {}
        self.video_stream_timestamps = {}  # Track when we last received a frame
        self.streams_lock = threading.Lock()
        
        # User list
        self.users = {}
        self.users_lock = threading.Lock()
        
        # Chat
        self.selected_recipients = []  # List of client IDs for private messages
        
        # Screen sharing
        self.screen_socket = None  # TCP control socket
        self.screen_udp_socket = None  # UDP data socket
        self.is_presenting = False
        self.screen_sharing_active = False
        self.current_presenter_id = None
        self.shared_screen_frame = None
        self.screen_lock = threading.Lock()
        
        # GUI
        self.video_labels = {}
        self.screen_label = None  # Label for displaying shared screen
        
        # UI Settings
        self.show_self_video = None  # Will be BooleanVar
        self.microphone_on = None  # Will be BooleanVar
        self.speaker_on = None  # Will be BooleanVar
        self.current_layout = "auto"  # auto, 1x1, 2x2, 3x3, 4x4
        
        # Google Meet-style panel visibility
        self.chat_panel_visible = False
        self.file_panel_visible = False
        self.people_panel_visible = False
        self.settings_panel_visible = False
        
        # Notification tracking
        self.active_notifications = []
        
    def show_chat_notification(self, sender, message, notification_type="Message"):
        """Show a notification popup for incoming chat messages"""
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
        
        main_layout = QHBoxLayout(notification)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(12)
        
        # Avatar (circular with first letter of sender name)
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
                border: none;
            }
        """)
        main_layout.addWidget(avatar)
        
        # Text container (sender name + message)
        text_container = QWidget()
        text_container.setStyleSheet("background: transparent; border: none;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        
        # Sender name
        sender_label = QLabel(sender)
        sender_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        sender_label.setStyleSheet("color: #ffffff; background: transparent; border: none;")
        text_layout.addWidget(sender_label)
        
        # Message preview (truncate if too long)
        preview = message[:35] + "..." if len(message) > 35 else message
        message_label = QLabel(preview)
        message_label.setFont(QFont("Arial", 9))
        message_label.setStyleSheet("color: #e0e0e0; background: transparent; border: none;")
        message_label.setWordWrap(False)
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
                font-size: 18px;
                font-weight: bold;
                border-radius: 14px;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #ea4335;
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(lambda: self.hide_notification(notification))
        main_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignTop)
        
        # Make notification clickable (except close button)
        notification.mousePressEvent = lambda event: self.notification_clicked(notification)
        
        # Position notification (stack them if multiple)
        y_offset = 80 + (len(self.active_notifications) * 100)
        notification.move(self.width() - 360, y_offset)
        notification.show()
        notification.raise_()  # Bring to front
        
        # Add to active notifications
        self.active_notifications.append(notification)
        
        # Auto-hide after 5 seconds
        QTimer.singleShot(5000, lambda: self.hide_notification(notification))
    
    def show_user_join_notification(self, username):
        """Show a notification when a user joins"""
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
        
        main_layout = QHBoxLayout(notification)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(12)
        
        # Avatar (circular with first letter of username)
        avatar = QLabel(username[0].upper() if username else "?")
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("""
            QLabel {
                background-color: #34a853;
                color: white;
                border-radius: 20px;
                font-size: 18px;
                font-weight: bold;
                border: none;
            }
        """)
        main_layout.addWidget(avatar)
        
        # Text container (username + "joined")
        text_container = QWidget()
        text_container.setStyleSheet("background: transparent; border: none;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        
        # Username
        user_label = QLabel(username)
        user_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        user_label.setStyleSheet("color: #ffffff; background: transparent; border: none;")
        text_layout.addWidget(user_label)
        
        # "joined the meeting"
        joined_label = QLabel("joined the meeting")
        joined_label.setFont(QFont("Arial", 9))
        joined_label.setStyleSheet("color: #e0e0e0; background: transparent; border: none;")
        text_layout.addWidget(joined_label)
        
        main_layout.addWidget(text_container, 1)
        
        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3e3e42;
                color: #ffffff;
                border: none;
                font-size: 18px;
                font-weight: bold;
                border-radius: 14px;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #ea4335;
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(lambda: self.hide_notification(notification))
        main_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignTop)
        
        # Position notification (stack them if multiple)
        y_offset = 80 + (len(self.active_notifications) * 100)
        notification.move(self.width() - 360, y_offset)
        notification.show()
        notification.raise_()  # Bring to front
        
        # Add to active notifications
        self.active_notifications.append(notification)
        
        # Auto-hide after 4 seconds
        QTimer.singleShot(4000, lambda: self.hide_notification(notification))
    
    def notification_clicked(self, notification):
        """Handle notification click - open chat panel"""
        self.hide_notification(notification)
        if not self.chat_panel_visible:
            self.toggle_chat_panel()
    
    def hide_notification(self, notification):
        """Hide and remove a notification"""
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)
            notification.deleteLater()
            
            # Reposition remaining notifications
            for idx, notif in enumerate(self.active_notifications):
                y_offset = 80 + (idx * 100)
                notif.move(self.width() - 360, y_offset)
        
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
                
                # Create UDP socket for audio
                self.audio_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
                # Create UDP socket for screen sharing
                self.screen_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
                # Send initial packet on screen UDP socket so server learns our address
                # This is a dummy packet with just our client_id, no frame data
                initial_packet = struct.pack('I', self.client_id)
                self.screen_udp_socket.sendto(initial_packet, (self.server_address, SERVER_SCREEN_UDP_PORT))
                print(f"[{self.get_timestamp()}] Sent initial screen UDP packet to establish address")
                
                # Initialize PyAudio
                self.audio = pyaudio.PyAudio()
                
                # Start receiver threads
                tcp_thread = threading.Thread(target=self.receive_control_messages, daemon=True)
                tcp_thread.start()
                
                udp_thread = threading.Thread(target=self.receive_video_streams, daemon=True)
                udp_thread.start()
                
                audio_thread = threading.Thread(target=self.receive_audio_stream, daemon=True)
                audio_thread.start()
                
                # Start screen sharing UDP receiver
                screen_udp_thread = threading.Thread(target=self.receive_screen_streams, daemon=True)
                screen_udp_thread.start()
                
                return True
            else:
                print(f"[{self.get_timestamp()}] Failed to connect to server")
                return False
                
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error connecting to server: {e}")
            return False
    
    def get_audio_devices(self):
        """Get list of available audio devices"""
        if self.audio is None:
            return {'input': [], 'output': []}
        
        input_devices = []
        output_devices = []
        
        try:
            info = self.audio.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            
            for i in range(num_devices):
                device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
                device_name = device_info.get('name')
                
                # Check if device supports input (microphone)
                if device_info.get('maxInputChannels') > 0:
                    input_devices.append({
                        'index': i,
                        'name': device_name,
                        'channels': device_info.get('maxInputChannels')
                    })
                
                # Check if device supports output (speakers)
                if device_info.get('maxOutputChannels') > 0:
                    output_devices.append({
                        'index': i,
                        'name': device_name,
                        'channels': device_info.get('maxOutputChannels')
                    })
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error getting audio devices: {e}")
        
        return {'input': input_devices, 'output': output_devices}
    
    def refresh_audio_devices(self):
        """Refresh audio device lists in GUI dropdowns"""
        devices = self.get_audio_devices()
        
        # Update input device dropdown
        input_names = [d['name'] for d in devices['input']]
        if hasattr(self, 'input_device_combo'):
            self.input_device_combo.clear()
            self.input_device_combo.addItems(input_names)
            if len(input_names) > 0 and self.selected_input_device is None:
                self.input_device_combo.setCurrentIndex(0)
                self.selected_input_device = devices['input'][0]['index']
        
        # Update output device dropdown
        output_names = [d['name'] for d in devices['output']]
        if hasattr(self, 'output_device_combo'):
            self.output_device_combo.clear()
            self.output_device_combo.addItems(output_names)
            if len(output_names) > 0 and self.selected_output_device is None:
                self.output_device_combo.setCurrentIndex(0)
                self.selected_output_device = devices['output'][0]['index']
    
    def on_input_device_changed(self, event=None):
        """Handle input device selection change"""
        if not hasattr(self, 'input_device_combo'):
            return
        
        devices = self.get_audio_devices()
        selected_name = self.input_device_combo.currentText()
        
        for device in devices['input']:
            if device['name'] == selected_name:
                old_device = self.selected_input_device
                self.selected_input_device = device['index']
                
                # Restart audio capture if it was running
                if self.audio_capturing and old_device != self.selected_input_device:
                    self.stop_audio_capture()
                    time.sleep(0.2)
                    self.start_audio_capture()
                    print(f"[{self.get_timestamp()}] Switched to input device: {device['name']}")
                break
    
    def on_output_device_changed(self, event=None):
        """Handle output device selection change"""
        if not hasattr(self, 'output_device_combo'):
            return
        
        devices = self.get_audio_devices()
        selected_name = self.output_device_combo.currentText()
        
        for device in devices['output']:
            if device['name'] == selected_name:
                old_device = self.selected_output_device
                self.selected_output_device = device['index']
                
                # Restart audio playback if it was running
                if self.audio_playing and old_device != self.selected_output_device:
                    self.stop_audio_playback()
                    time.sleep(0.2)
                    self.start_audio_playback()
                    print(f"[{self.get_timestamp()}] Switched to output device: {device['name']}")
                break
    
    def get_timestamp(self):
        """Get formatted timestamp"""
        return datetime.now().strftime("%H:%M:%S")
    
    def start_video_capture(self):
        """Start capturing video from webcam"""
        try:
            # Create new camera instance
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
    
    def stop_video_capture(self):
        """Stop capturing video from webcam and release camera"""
        self.capturing = False
        
        # Give the capture thread time to stop
        time.sleep(0.2)
        
        # Release the camera
        if self.camera is not None:
            self.camera.release()
            self.camera = None
            print(f"[{self.get_timestamp()}] Camera released")
        
        print(f"[{self.get_timestamp()}] Video capture stopped")
    
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
    
    def start_audio_capture(self):
        """Start capturing audio from microphone"""
        try:
            # Open audio input stream
            self.audio_stream_input = self.audio.open(
                format=AUDIO_FORMAT,
                channels=AUDIO_CHANNELS,
                rate=AUDIO_RATE,
                input=True,
                input_device_index=self.selected_input_device,
                frames_per_buffer=AUDIO_CHUNK
            )
            
            self.audio_capturing = True
            
            # Start audio capture thread
            audio_capture_thread = threading.Thread(target=self.capture_and_send_audio, daemon=True)
            audio_capture_thread.start()
            
            print(f"[{self.get_timestamp()}] Audio capture started")
            return True
            
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error starting audio capture: {e}")
            return False
    
    def stop_audio_capture(self):
        """Stop capturing audio"""
        self.audio_capturing = False
        
        # Give the capture thread time to stop
        time.sleep(0.15)
        
        # Close audio input stream
        if self.audio_stream_input is not None:
            try:
                self.audio_stream_input.stop_stream()
            except:
                pass
            
            try:
                self.audio_stream_input.close()
            except:
                pass
            
            self.audio_stream_input = None
            print(f"[{self.get_timestamp()}] Microphone closed")
        
        print(f"[{self.get_timestamp()}] Audio capture stopped")
    
    def capture_and_send_audio(self):
        """Capture audio and send to server"""
        while self.audio_capturing and self.connected:
            try:
                # Read audio data (non-blocking with overflow handling)
                audio_data = self.audio_stream_input.read(AUDIO_CHUNK, exception_on_overflow=False)
                
                # Prepend client_id to the audio data
                packet = struct.pack('I', self.client_id) + audio_data
                
                # Send via UDP
                self.audio_udp_socket.sendto(packet, (self.server_address, SERVER_AUDIO_PORT))
                
                # Small delay to prevent flooding (AUDIO_CHUNK/AUDIO_RATE = natural timing)
                # This helps sync with video and reduces network congestion
                time.sleep(AUDIO_CHUNK / AUDIO_RATE * 0.95)  # 95% to account for processing time
                
            except Exception as e:
                if self.audio_capturing:
                    print(f"[{self.get_timestamp()}] Error capturing/sending audio: {e}")
                time.sleep(0.01)
    
    def start_audio_playback(self):
        """Start audio playback"""
        try:
            # Open audio output stream
            self.audio_stream_output = self.audio.open(
                format=AUDIO_FORMAT,
                channels=AUDIO_CHANNELS,
                rate=AUDIO_RATE,
                output=True,
                output_device_index=self.selected_output_device,
                frames_per_buffer=AUDIO_CHUNK
            )
            
            self.audio_playing = True
            print(f"[{self.get_timestamp()}] Audio playback started")
            return True
            
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error starting audio playback: {e}")
            return False
    
    def stop_audio_playback(self):
        """Stop audio playback"""
        self.audio_playing = False
        
        # Give the playback thread time to stop writing
        time.sleep(0.15)
        
        # Close audio output stream
        if self.audio_stream_output is not None:
            try:
                self.audio_stream_output.stop_stream()
            except:
                pass
            
            try:
                self.audio_stream_output.close()
            except:
                pass
            
            self.audio_stream_output = None
            print(f"[{self.get_timestamp()}] Speaker closed")
        
        print(f"[{self.get_timestamp()}] Audio playback stopped")
    
    def receive_audio_stream(self):
        """Receive mixed audio stream from server and play it"""
        print(f"[{self.get_timestamp()}] Audio receiver started")
        
        while self.connected:
            try:
                # Receive audio packet
                data, addr = self.audio_udp_socket.recvfrom(MAX_PACKET_SIZE)
                
                # Play audio if playback is enabled
                if self.audio_playing and self.audio_stream_output is not None:
                    try:
                        self.audio_stream_output.write(data)
                    except Exception as write_error:
                        # Stream might be closing, skip this chunk
                        if self.audio_playing:
                            print(f"[{self.get_timestamp()}] Audio write error: {write_error}")
                        time.sleep(0.01)
                
            except Exception as e:
                if self.connected:
                    print(f"[{self.get_timestamp()}] Error receiving/playing audio: {e}")
                time.sleep(0.01)
    
    def start_screen_sharing(self):
        """Start sharing screen"""
        try:
            # Make sure we're not already sharing
            if self.screen_sharing_active:
                print(f"[{self.get_timestamp()}] Already sharing screen")
                return False
            
            # Clean up any leftover socket from previous session
            if self.screen_socket:
                try:
                    self.screen_socket.close()
                except:
                    pass
                self.screen_socket = None
                time.sleep(0.2)  # Brief wait after cleanup
                print(f"[{self.get_timestamp()}] Cleaned up previous screen socket")
            
            print(f"[{self.get_timestamp()}] Connecting to screen sharing server...")
            
            # Connect to screen sharing control port (TCP)
            self.screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.screen_socket.settimeout(5.0)  # 5 second timeout for connection
            
            try:
                self.screen_socket.connect((self.server_address, SERVER_SCREEN_PORT))
                print(f"[{self.get_timestamp()}] Connected to {self.server_address}:{SERVER_SCREEN_PORT}")
            except socket.timeout:
                print(f"[{self.get_timestamp()}] Connection timeout - server may not be running or port {SERVER_SCREEN_PORT} blocked")
                raise
            except ConnectionRefusedError:
                print(f"[{self.get_timestamp()}] Connection refused - server not listening on port {SERVER_SCREEN_PORT}")
                raise
            
            # Send client_id
            print(f"[{self.get_timestamp()}] Sending client_id: {self.client_id}")
            self.screen_socket.sendall(struct.pack('I', self.client_id))
            print(f"[{self.get_timestamp()}] Waiting for server response...")
            
            # Wait for response
            self.screen_socket.settimeout(5.0)  # Keep timeout for recv
            response = self.screen_socket.recv(10)
            print(f"[{self.get_timestamp()}] Received response: {response}")
            
            # Remove timeout for ongoing communication
            self.screen_socket.settimeout(None)
            
            if response == b"GRANTED":
                self.is_presenting = True
                self.screen_sharing_active = True
                self.current_presenter_id = self.client_id  # Mark self as presenter
                
                # Start screen capture thread (sends via UDP)
                screen_thread = threading.Thread(target=self.capture_and_send_screen, daemon=True)
                screen_thread.start()
                
                print(f"[{self.get_timestamp()}] Screen sharing started")
                return True
            else:
                print(f"[{self.get_timestamp()}] Screen sharing denied - another user is presenting")
                if self.screen_socket:
                    try:
                        self.screen_socket.close()
                    except:
                        pass
                    self.screen_socket = None
                return False
                
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error starting screen sharing: {e}")
            import traceback
            traceback.print_exc()
            # Clean up on error
            self.screen_sharing_active = False
            self.is_presenting = False
            if self.screen_socket:
                try:
                    self.screen_socket.close()
                except:
                    pass
                self.screen_socket = None
            return False
    
    def stop_screen_sharing(self):
        """Stop sharing screen"""
        if not self.screen_sharing_active:
            return
        
        print(f"[{self.get_timestamp()}] Stopping screen sharing...")
        
        # Stop the sharing flags first to terminate capture thread
        self.screen_sharing_active = False
        self.is_presenting = False
        
        # Clear presenter ID if it's us
        if self.current_presenter_id == self.client_id:
            self.current_presenter_id = None
        
        # Clear the shared screen frame
        with self.screen_lock:
            self.shared_screen_frame = None
        
        # Give capture thread time to exit cleanly
        time.sleep(0.7)
        
        # Signal stop to server via TCP control socket
        if self.screen_socket:
            try:
                self.screen_socket.send(b"STOP")
                time.sleep(0.1)  # Give server time to process
            except Exception as e:
                print(f"[{self.get_timestamp()}] Note: Error sending STOP: {e}")
            
            try:
                self.screen_socket.shutdown(socket.SHUT_RDWR)
            except Exception as e:
                print(f"[{self.get_timestamp()}] Note: Error in shutdown: {e}")
            
            try:
                self.screen_socket.close()
            except Exception as e:
                print(f"[{self.get_timestamp()}] Note: Error closing socket: {e}")
            finally:
                self.screen_socket = None
        
        # Extra wait to ensure server has processed the stop
        time.sleep(0.3)
        
        print(f"[{self.get_timestamp()}] Screen sharing stopped - ready for restart")
    
    def capture_and_send_screen(self):
        """Capture screen and send to server via UDP"""
        # Create mss instance in this thread
        sct = None
        try:
            sct = mss.mss()
            
            while self.screen_sharing_active and self.connected:
                try:
                    # Capture primary monitor
                    monitor = sct.monitors[1]  # Primary monitor
                    screenshot = sct.grab(monitor)
                    
                    # Convert to numpy array
                    img = np.array(screenshot)
                    
                    # Convert BGRA to BGR
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    
                    # Resize to screen sharing resolution
                    img = cv2.resize(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
                    
                    # Compress to JPEG
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), SCREEN_QUALITY]
                    result, encoded_frame = cv2.imencode('.jpg', img, encode_param)
                    
                    if result:
                        frame_data = encoded_frame.tobytes()
                        
                        # Check if packet will fit in UDP (with some safety margin)
                        packet = struct.pack('I', self.client_id) + frame_data
                        packet_size = len(packet)
                        
                        if packet_size > 60000:  # Too large for UDP
                            # Re-encode with lower quality
                            lower_quality = max(20, SCREEN_QUALITY - 20)
                            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), lower_quality]
                            result, encoded_frame = cv2.imencode('.jpg', img, encode_param)
                            if result:
                                frame_data = encoded_frame.tobytes()
                                packet = struct.pack('I', self.client_id) + frame_data
                                print(f"[{self.get_timestamp()}] Reduced quality to {lower_quality} (size: {len(packet)} bytes)")
                        
                        # Store frame locally so presenter can see their own screen
                        with self.screen_lock:
                            self.shared_screen_frame = frame_data
                        
                        # Send via UDP with client_id prefix
                        try:
                            self.screen_udp_socket.sendto(packet, (self.server_address, SERVER_SCREEN_UDP_PORT))
                        except OSError as e:
                            if self.screen_sharing_active and "10040" in str(e):
                                print(f"[{self.get_timestamp()}] Packet too large ({len(packet)} bytes) - skipping frame")
                            elif self.screen_sharing_active:
                                print(f"[{self.get_timestamp()}] Error sending screen frame: {e}")
                    
                    # Control frame rate
                    time.sleep(1.0 / SCREEN_FPS)
                    
                except Exception as e:
                    if self.screen_sharing_active:
                        print(f"[{self.get_timestamp()}] Error capturing screen: {e}")
                    break
        
        finally:
            # Clean up mss instance
            if sct:
                try:
                    sct.close()
                except:
                    pass
            
            print(f"[{self.get_timestamp()}] Screen capture thread ended")
    
    def receive_screen_streams(self):
        """Receive screen frames via UDP"""
        print(f"[{self.get_timestamp()}] Screen UDP receiver started")
        
        while self.connected:
            try:
                # Receive screen frame packet
                data, addr = self.screen_udp_socket.recvfrom(MAX_SCREEN_PACKET_SIZE)
                
                if len(data) < 4:
                    continue
                
                # Extract client_id (first 4 bytes)
                presenter_id = struct.unpack('I', data[:4])[0]
                frame_data = data[4:]
                
                # Store the frame (including our own for preview)
                with self.screen_lock:
                    self.shared_screen_frame = frame_data
                    self.current_presenter_id = presenter_id
                
            except Exception as e:
                if self.connected:
                    print(f"[{self.get_timestamp()}] Error receiving screen frame: {e}")
    
    def receive_control_messages(self):
        """Receive control messages from server via TCP"""
        buffer = ""
        
        while self.connected:
            try:
                data = self.tcp_socket.recv(4096).decode('utf-8')
                
                if not data:
                    break
                
                buffer += data
                
                # Process complete messages (line-based protocol - only process when we have full lines)
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    
                    if not message:  # Skip empty messages
                        continue
                    
                    if message.startswith("USERS:"):
                        # Update user list
                        user_data = message.split(":", 1)[1]
                        try:
                            users = pickle.loads(bytes.fromhex(user_data))
                            with self.users_lock:
                                old_user_count = len(self.users)
                                old_users = set(self.users.values())  # Store old usernames
                                self.users = {u['id']: u['username'] for u in users}
                                new_user_count = len(self.users)
                                new_users = set(self.users.values())  # Get new usernames
                                
                                # Detect who joined
                                joined_users = new_users - old_users
                                for username in joined_users:
                                    if username != self.username:  # Don't notify for yourself
                                        self.user_join_signal.emit(username)
                            
                            # Clean up video streams for disconnected users
                            with self.streams_lock:
                                current_user_ids = set(self.users.keys())
                                stream_client_ids = set(self.video_streams.keys())
                                
                                # Remove streams for users no longer in the session
                                for client_id in list(stream_client_ids):
                                    if client_id not in current_user_ids and client_id != self.client_id:
                                        del self.video_streams[client_id]
                                        if client_id in self.video_stream_timestamps:
                                            del self.video_stream_timestamps[client_id]
                                        print(f"[{self.get_timestamp()}] Removed video stream for disconnected user {client_id}")
                            
                            # Update recipient dropdown
                            self.update_recipient_list()
                            
                            # Re-evaluate layout when user count changes
                            if old_user_count != new_user_count:
                                if self.layout_mode == "auto":
                                    QTimer.singleShot(100, self.determine_and_apply_layout)
                        except:
                            pass
                    
                    elif message.startswith("CHAT:"):
                        # Received chat message from server
                        try:
                            # Format: CHAT:client_id:username:HH:MM:SS:message
                            # Split into at most 4 parts: CHAT, client_id, username, "HH:MM:SS:message"
                            parts = message.split(":", 3)
                            if len(parts) >= 4:
                                sender_id = int(parts[1])
                                sender_username = parts[2]
                                rest = parts[3]
                                
                                # rest is "HH:MM:SS:message", split once more to get timestamp and message
                                # Timestamp is first 8 characters (HH:MM:SS)
                                timestamp = rest[:8]
                                chat_message = rest[9:] if len(rest) > 9 else ""  # Skip "HH:MM:SS:"
                                
                                # Display in chat window (done in main thread via signal)
                                self.chat_message_received.emit(sender_username, timestamp, chat_message)
                        except Exception as e:
                            self.chat_debug_signal.emit(f"Error handling chat: {str(e)}")
                    
                    elif message.startswith("PRIVATE_CHAT:"):
                        # Received private chat message: PRIVATE_CHAT:sender_id|sender_username|timestamp|recipient_ids|message
                        try:
                            # Remove "PRIVATE_CHAT:" prefix and split by pipe
                            content = message[13:]  # Remove "PRIVATE_CHAT:"
                            parts = content.split("|", 4)  # Split into max 5 parts
                            if len(parts) >= 5:
                                sender_id = int(parts[0])
                                sender_username = parts[1]
                                timestamp = parts[2]
                                recipient_ids_str = parts[3]
                                chat_message = parts[4]
                                
                                # Get recipient names
                                recipient_ids = [int(rid) for rid in recipient_ids_str.split(",")]
                                recipient_names = []
                                with self.users_lock:
                                    for rid in recipient_ids:
                                        if rid in self.users:
                                            recipient_names.append(self.users[rid])
                                        elif rid == self.client_id:
                                            recipient_names.append("You")
                                
                                # Display in chat window - call directly since we're already in a QTimer callback
                                self.display_chat_message(sender_username, timestamp, chat_message, is_private=True, recipient_names=recipient_names)
                        except Exception as e:
                            print(f"[{self.get_timestamp()}] Error handling private chat message: {e}")
                    
                    elif message.startswith("FILE_OFFER:"):
                        # File available for download: FILE_OFFER:file_id:filename:filesize:uploader_name:uploader_id
                        try:
                            parts = message.split(":", 5)
                            if len(parts) >= 6:
                                file_id = int(parts[1])
                                filename = parts[2]
                                filesize = int(parts[3])
                                uploader_name = parts[4]
                                uploader_id = int(parts[5])
                                
                                # Store metadata
                                self.shared_files_metadata[file_id] = {
                                    'filename': filename,
                                    'size': filesize,
                                    'uploader': uploader_name,
                                    'uploader_id': uploader_id
                                }
                                
                                # Update file list (must be in main thread)
                                QTimer.singleShot(0, self.update_file_list)
                                
                                # Show notification in chat
                                size_mb = filesize / (1024 * 1024)
                                notification = f"📁 {uploader_name} shared a file: {filename} ({size_mb:.2f} MB)"
                                QTimer.singleShot(0, lambda: self.display_chat_message(
                                    "System", self.get_timestamp(), notification, is_system=True
                                ))
                        except Exception as e:
                            print(f"[{self.get_timestamp()}] Error handling file offer: {e}")
                    
                    elif message.startswith("FILE_DELETED:"):
                        # File deleted notification: FILE_DELETED:file_id
                        try:
                            file_id = int(message.split(":", 1)[1])
                            
                            # Remove from metadata
                            if file_id in self.shared_files_metadata:
                                filename = self.shared_files_metadata[file_id]['filename']
                                del self.shared_files_metadata[file_id]
                                
                                # Update file list
                                QTimer.singleShot(0, self.update_file_list)
                                
                                # Show notification
                                notification = f"🗑️ File deleted: {filename}"
                                QTimer.singleShot(0, lambda: self.display_chat_message(
                                    "System", self.get_timestamp(), notification, is_system=True
                                ))
                        except Exception as e:
                            print(f"[{self.get_timestamp()}] Error handling file deletion: {e}")
                    
                    elif message.startswith("PRESENTER:"):
                        # Update presenter status
                        presenter_data = message.split(":", 1)[1]
                        if presenter_data == "None":
                            self.current_presenter_id = None
                            with self.screen_lock:
                                self.shared_screen_frame = None
                            print(f"[{self.get_timestamp()}] No active presenter")
                        else:
                            try:
                                self.current_presenter_id = int(presenter_data)
                                with self.users_lock:
                                    username = self.users.get(self.current_presenter_id, "Unknown")
                                print(f"[{self.get_timestamp()}] {username} is now presenting")
                            except:
                                pass
                    
                    # Note: Screen frames now received via UDP in receive_screen_streams()
                    
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
                        self.video_stream_timestamps[client_id] = time.time()
                
            except Exception as e:
                if self.connected:
                    print(f"[{self.get_timestamp()}] Error receiving video stream: {e}")
    
    def get_icon(self, icon_name, color='#e8eaed', size=None):
        """Get Material Design icon using qtawesome or fallback to text"""
        if HAS_QTAWESOME:
            # Material Design icon names
            icon_map = {
                'mic': 'mdi.microphone',
                'mic_off': 'mdi.microphone-off',
                'videocam': 'mdi.video',
                'videocam_off': 'mdi.video-off',
                'screen_share': 'mdi.monitor',
                'call_end': 'mdi.phone-hangup',
                'chat': 'mdi.message-text',
                'people': 'mdi.account-group',
                'attach_file': 'mdi.folder',
                'settings': 'mdi.cog',
                'close': 'mdi.close',
                'send': 'mdi.send',
                'download': 'mdi.download',
                'delete': 'mdi.delete',
                'refresh': 'mdi.refresh',
                'layout': 'mdi.view-dashboard',
            }
            mdi_name = icon_map.get(icon_name, 'mdi.help-circle')
            try:
                return qta.icon(mdi_name, color=color)
            except:
                # Fallback if icon not found
                return None
        return None
    
    def create_gui(self):
        """Create the GUI"""
        # Set window properties
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1400, 800)  # Wider to accommodate screen sharing
        self.setMinimumSize(1200, 600)  # Prevent shrinking too small
        
        # Apply modern dark theme
        self.setStyleSheet("""
            /* Main Window */
            QMainWindow {
                background-color: #1e1e1e;
            }
            
            /* General Widget Styling */
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            /* Labels */
            QLabel {
                color: #e0e0e0;
                background-color: transparent;
            }
            
            /* Buttons */
            QPushButton {
                background-color: #2d2d30;
                color: #ffffff;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10pt;
            }
            
            QPushButton:hover {
                background-color: #3e3e42;
                border: 1px solid #007acc;
            }
            
            QPushButton:pressed {
                background-color: #007acc;
            }
            
            QPushButton:disabled {
                background-color: #2d2d30;
                color: #656565;
                border: 1px solid #3e3e42;
            }
            
            /* CheckBoxes */
            QCheckBox {
                color: #e0e0e0;
                spacing: 5px;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 2px solid #3e3e42;
                background-color: #2d2d30;
            }
            
            QCheckBox::indicator:checked {
                background-color: #007acc;
                border: 2px solid #007acc;
            }
            
            QCheckBox::indicator:hover {
                border: 2px solid #007acc;
            }
            
            /* ComboBox */
            QComboBox {
                background-color: #2d2d30;
                color: #e0e0e0;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 5px;
                min-width: 100px;
            }
            
            QComboBox:hover {
                border: 1px solid #007acc;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
                margin-right: 5px;
            }
            
            QComboBox QAbstractItemView {
                background-color: #2d2d30;
                color: #e0e0e0;
                selection-background-color: #007acc;
                selection-color: #ffffff;
                border: 1px solid #3e3e42;
            }
            
            /* LineEdit */
            QLineEdit {
                background-color: #2d2d30;
                color: #e0e0e0;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 5px;
            }
            
            QLineEdit:focus {
                border: 1px solid #007acc;
            }
            
            /* TextEdit (Chat) */
            QTextEdit {
                background-color: #252526;
                color: #e0e0e0;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 5px;
            }
            
            QTextEdit:focus {
                border: 1px solid #007acc;
            }
            
            /* ListWidget (Files) */
            QListWidget {
                background-color: #252526;
                color: #e0e0e0;
                border: 1px solid #3e3e42;
                border-radius: 4px;
            }
            
            QListWidget::item {
                padding: 5px;
            }
            
            QListWidget::item:selected {
                background-color: #007acc;
                color: #ffffff;
            }
            
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
            
            /* ScrollBar */
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 12px;
                border: none;
            }
            
            QScrollBar::handle:vertical {
                background-color: #3e3e42;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #007acc;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            QScrollBar:horizontal {
                background-color: #1e1e1e;
                height: 12px;
                border: none;
            }
            
            QScrollBar::handle:horizontal {
                background-color: #3e3e42;
                border-radius: 6px;
                min-width: 20px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background-color: #007acc;
            }
            
            /* GroupBox (File Sharing) */
            QGroupBox {
                color: #e0e0e0;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #007acc;
            }
            
            /* Frame (Video containers) */
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
            }
            
            /* Progress Bar */
            QProgressBar {
                background-color: #2d2d30;
                color: #e0e0e0;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                text-align: center;
            }
            
            QProgressBar::chunk {
                background-color: #007acc;
                border-radius: 3px;
            }
            
            /* Dialog */
            QDialog {
                background-color: #1e1e1e;
            }
            
            /* MessageBox */
            QMessageBox {
                background-color: #1e1e1e;
            }
            
            QMessageBox QLabel {
                color: #e0e0e0;
            }
        """)
        
        # Initialize UI variables (Python variables instead of tk.*Var)
        self.show_self_video = True
        self.microphone_on = True
        self.speaker_on = True
        self.layout_mode = "tiled"  # Start with tiled layout
        self.current_layout_mode = "tiled"  # Actual current mode after auto-decision
        self.recipient_var = "Everyone"
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Google Meet-style layout: Main content + side panels + bottom controls
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main video content area (always visible)
        self.main_content_widget = QWidget()
        main_content_layout = QVBoxLayout(self.main_content_widget)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(0)
        
        # Video display area (fills most of screen)
        self.video_display_container = QWidget()
        video_display_layout = QHBoxLayout(self.video_display_container)
        video_display_layout.setContentsMargins(10, 10, 10, 10)
        video_display_layout.setSpacing(10)
        
        # Main video/screen area
        self.main_video_container = QWidget()
        self.main_video_layout = QVBoxLayout(self.main_video_container)
        self.main_video_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tiled video grid (default view)
        self.video_frame = QFrame()
        self.video_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        self.video_frame.setLineWidth(2)
        self.video_frame.setStyleSheet("QFrame { background-color: #000000; }")
        self.main_video_layout.addWidget(self.video_frame)
        
        # Spotlight/Screen share container (hidden by default)
        self.spotlight_container = QWidget()
        self.spotlight_layout = QHBoxLayout(self.spotlight_container)
        self.spotlight_layout.setSpacing(10)
        self.spotlight_layout.setContentsMargins(0, 0, 0, 0)
        
        # Spotlight main area (screen share or main speaker)
        self.spotlight_main = QFrame()
        self.spotlight_main.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        self.spotlight_main.setLineWidth(2)
        self.spotlight_main.setStyleSheet("QFrame { background-color: #000000; }")
        spotlight_main_layout = QVBoxLayout(self.spotlight_main)
        spotlight_main_layout.setContentsMargins(0, 0, 0, 0)
        spotlight_main_layout.setSpacing(0)
        
        # Spotlight video label
        self.spotlight_label = QLabel("No Content")
        self.spotlight_label.setFont(QFont("Arial", 14))
        self.spotlight_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spotlight_label.setStyleSheet("background-color: black; color: white;")
        spotlight_main_layout.addWidget(self.spotlight_label, stretch=1)
        
        # Spotlight name label (shows who is sharing/speaking)
        self.spotlight_name_label = QLabel("")
        self.spotlight_name_label.setFont(QFont("Arial", 12))
        self.spotlight_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spotlight_name_label.setStyleSheet("background-color: rgba(0, 0, 0, 180); color: white; padding: 8px;")
        self.spotlight_name_label.setMaximumHeight(40)
        spotlight_main_layout.addWidget(self.spotlight_name_label)
        
        self.spotlight_layout.addWidget(self.spotlight_main, stretch=1)
        
        # Sidebar for participant thumbnails (when screen sharing)
        self.participants_sidebar = QFrame()
        self.participants_sidebar.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        self.participants_sidebar.setLineWidth(1)
        self.participants_sidebar.setMaximumWidth(200)
        self.participants_sidebar.setStyleSheet("QFrame { background-color: #1e1e1e; }")
        sidebar_layout = QVBoxLayout(self.participants_sidebar)
        sidebar_layout.setContentsMargins(5, 5, 5, 5)
        sidebar_layout.setSpacing(5)
        
        # Scrollable area for participant thumbnails
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar_scroll.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")
        
        self.sidebar_widget = QWidget()
        self.sidebar_widget_layout = QVBoxLayout(self.sidebar_widget)
        self.sidebar_widget_layout.setSpacing(8)
        self.sidebar_widget_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_widget_layout.addStretch()
        
        self.sidebar_scroll.setWidget(self.sidebar_widget)
        sidebar_layout.addWidget(self.sidebar_scroll)
        
        self.spotlight_layout.addWidget(self.participants_sidebar)
        self.participants_sidebar.hide()  # Hidden until screen share
        
        # Add spotlight container to main layout (hidden initially)
        self.main_video_layout.addWidget(self.spotlight_container)
        self.spotlight_container.hide()
        
        video_display_layout.addWidget(self.main_video_container, stretch=1)
        
        main_content_layout.addWidget(self.video_display_container, stretch=1)
        
        # Bottom control bar (Google Meet style)
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(70)
        bottom_bar.setStyleSheet("""
            QWidget {
                background-color: #202124;
                border-top: 1px solid #3c4043;
            }
        """)
        bottom_bar_layout = QHBoxLayout(bottom_bar)
        bottom_bar_layout.setContentsMargins(20, 0, 20, 0)  # Remove vertical padding for centering
        bottom_bar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center horizontally
        
        # Left side - Meeting info
        info_label = QLabel()
        info_label.setFont(QFont("Arial", 9))
        info_label.setStyleSheet("color: #e8eaed;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # Align vertically center
        self.meeting_info_label = info_label
        bottom_bar_layout.addWidget(info_label)
        
        bottom_bar_layout.addStretch()
        
        # Center - Main controls
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setSpacing(10)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the buttons
        
        # Microphone button
        self.mic_btn = QPushButton()
        self.mic_btn.setCheckable(True)
        self.mic_btn.setChecked(True)
        mic_icon = self.get_icon('mic', '#e8eaed')
        if mic_icon:
            self.mic_btn.setIcon(mic_icon)
            self.mic_btn.setIconSize(QSize(24, 24))
        else:
            self.mic_btn.setText("🎤")
            self.mic_btn.setFont(QFont("Arial", 20))
        self.mic_btn.setFixedSize(50, 50)
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background-color: #ea4335;
                border-radius: 25px;
                border: none;
            }
            QPushButton:hover {
                background-color: #c5341c;
            }
            QPushButton:checked {
                background-color: #3c4043;
            }
            QPushButton:checked:hover {
                background-color: #5f6368;
            }
        """)
        self.mic_btn.toggled.connect(self.toggle_microphone)
        controls_layout.addWidget(self.mic_btn)
        
        # Camera button
        self.camera_btn = QPushButton()
        self.camera_btn.setCheckable(True)
        self.camera_btn.setChecked(True)
        cam_icon = self.get_icon('videocam', '#e8eaed')
        if cam_icon:
            self.camera_btn.setIcon(cam_icon)
            self.camera_btn.setIconSize(QSize(24, 24))
        else:
            self.camera_btn.setText("📹")
            self.camera_btn.setFont(QFont("Arial", 20))
        self.camera_btn.setFixedSize(50, 50)
        self.camera_btn.setStyleSheet("""
            QPushButton {
                background-color: #ea4335;
                border-radius: 25px;
                border: none;
            }
            QPushButton:hover {
                background-color: #c5341c;
            }
            QPushButton:checked {
                background-color: #3c4043;
            }
            QPushButton:checked:hover {
                background-color: #5f6368;
            }
        """)
        self.camera_btn.toggled.connect(self.toggle_self_video)
        controls_layout.addWidget(self.camera_btn)
        
        # Screen share button - use monitor symbol
        self.share_screen_btn = QPushButton()
        self.share_screen_btn.setCheckable(True)
        screen_icon = self.get_icon('screen_share', '#e8eaed')
        if screen_icon:
            self.share_screen_btn.setIcon(screen_icon)
            self.share_screen_btn.setIconSize(QSize(24, 24))
        else:
            self.share_screen_btn.setText("🖥")
            self.share_screen_btn.setFont(QFont("Arial", 20))
        self.share_screen_btn.setFixedSize(50, 50)
        self.share_screen_btn.setStyleSheet("""
            QPushButton {
                background-color: #ea4335;
                border-radius: 25px;
                border: none;
            }
            QPushButton:hover {
                background-color: #c5341c;
            }
            QPushButton:checked {
                background-color: #3c4043;
            }
            QPushButton:checked:hover {
                background-color: #5f6368;
            }
        """)
        self.share_screen_btn.toggled.connect(self.toggle_screen_sharing)
        controls_layout.addWidget(self.share_screen_btn)
        
        # Leave call button
        leave_btn = QPushButton()
        leave_icon = self.get_icon('call_end', '#ffffff')
        if leave_icon:
            leave_btn.setIcon(leave_icon)
            leave_btn.setIconSize(QSize(24, 24))
        else:
            leave_btn.setText("📞")
            leave_btn.setFont(QFont("Arial", 20))
        leave_btn.setFixedSize(50, 50)
        leave_btn.setStyleSheet("""
            QPushButton {
                background-color: #ea4335;
                border-radius: 25px;
                border: none;
            }
            QPushButton:hover {
                background-color: #c5341c;
            }
        """)
        leave_btn.clicked.connect(self.close)
        controls_layout.addWidget(leave_btn)
        
        bottom_bar_layout.addWidget(controls_widget)
        
        bottom_bar_layout.addStretch()
        
        # Right side - Panel toggles and settings
        right_controls = QWidget()
        right_controls_layout = QHBoxLayout(right_controls)
        right_controls_layout.setSpacing(8)
        
        # People panel toggle
        people_btn = QPushButton()
        people_icon = self.get_icon('people', '#e8eaed')
        if people_icon:
            people_btn.setIcon(people_icon)
            people_btn.setIconSize(QSize(20, 20))
        else:
            people_btn.setText("👥")
            people_btn.setFont(QFont("Arial", 16))
        people_btn.setFixedSize(40, 40)
        people_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border-radius: 20px;
                border: none;
                color: #e8eaed;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
        """)
        people_btn.setToolTip("People")
        people_btn.clicked.connect(self.toggle_people_panel)
        right_controls_layout.addWidget(people_btn)
        
        # Chat panel toggle
        chat_btn = QPushButton()
        chat_icon = self.get_icon('chat', '#e8eaed')
        if chat_icon:
            chat_btn.setIcon(chat_icon)
            chat_btn.setIconSize(QSize(20, 20))
        else:
            chat_btn.setText("💬")
            chat_btn.setFont(QFont("Arial", 16))
        chat_btn.setFixedSize(40, 40)
        chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border-radius: 20px;
                border: none;
                color: #e8eaed;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
        """)
        chat_btn.setToolTip("Chat")
        chat_btn.clicked.connect(self.toggle_chat_panel)
        right_controls_layout.addWidget(chat_btn)
        
        # File panel toggle
        file_btn = QPushButton()
        file_icon = self.get_icon('attach_file', '#e8eaed')
        if file_icon:
            file_btn.setIcon(file_icon)
            file_btn.setIconSize(QSize(20, 20))
        else:
            file_btn.setText("📁")
            file_btn.setFont(QFont("Arial", 16))
        file_btn.setFixedSize(40, 40)
        file_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border-radius: 20px;
                border: none;
                color: #e8eaed;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
        """)
        file_btn.setToolTip("Files")
        file_btn.clicked.connect(self.toggle_file_panel)
        right_controls_layout.addWidget(file_btn)
        
        # Layout menu button
        layout_btn = QPushButton()
        layout_icon = self.get_icon('layout', '#e8eaed')
        if layout_icon:
            layout_btn.setIcon(layout_icon)
            layout_btn.setIconSize(QSize(20, 20))
        else:
            layout_btn.setText("⊞")
            layout_btn.setFont(QFont("Arial", 16))
        layout_btn.setFixedSize(40, 40)
        layout_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border-radius: 20px;
                border: none;
                color: #e8eaed;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
        """)
        layout_btn.setToolTip("Change Layout")
        layout_btn.clicked.connect(self.show_layout_menu)
        right_controls_layout.addWidget(layout_btn)
        
        # Settings button
        settings_btn = QPushButton()
        settings_icon = self.get_icon('settings', '#e8eaed')
        if settings_icon:
            settings_btn.setIcon(settings_icon)
            settings_btn.setIconSize(QSize(20, 20))
        else:
            settings_btn.setText("⚙️")
            settings_btn.setFont(QFont("Arial", 16))
        settings_btn.setFixedSize(40, 40)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border-radius: 20px;
                border: none;
                color: #e8eaed;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
        """)
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self.show_settings_panel)
        right_controls_layout.addWidget(settings_btn)
        
        bottom_bar_layout.addWidget(right_controls)
        
        main_content_layout.addWidget(bottom_bar)
        
        main_layout.addWidget(self.main_content_widget, stretch=1)
        
        # Chat Side Panel (hidden by default)
        self.chat_panel = QWidget()
        self.chat_panel.setFixedWidth(350)
        self.chat_panel.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-left: 1px solid #3c4043;
            }
        """)
        chat_panel_layout = QVBoxLayout(self.chat_panel)
        chat_panel_layout.setContentsMargins(0, 0, 0, 0)
        chat_panel_layout.setSpacing(0)
        
        # Chat header
        chat_header = QWidget()
        chat_header.setFixedHeight(60)
        chat_header.setStyleSheet("background-color: #2d2d30; border-bottom: 1px solid #3c4043;")
        chat_header_layout = QHBoxLayout(chat_header)
        chat_header_layout.setContentsMargins(20, 10, 20, 10)
        
        chat_title = QLabel("Messages")
        chat_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        chat_title.setStyleSheet("color: #e8eaed; border: none; background-color: transparent;")
        chat_header_layout.addWidget(chat_title)
        
        chat_header_layout.addStretch()
        
        close_chat_btn = QPushButton("✕")
        close_chat_btn.setFixedSize(30, 30)
        close_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #e8eaed;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #3c4043;
                border-radius: 15px;
            }
        """)
        close_chat_btn.clicked.connect(self.toggle_chat_panel)
        chat_header_layout.addWidget(close_chat_btn)
        
        chat_panel_layout.addWidget(chat_header)
        
        # Chat messages area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | 
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.chat_display.setFont(QFont("Arial", 11))
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e8eaed;
                border: none;
                padding: 15px;
            }
        """)
        chat_panel_layout.addWidget(self.chat_display, stretch=1)
        
        # Chat input area
        chat_input_container = QWidget()
        chat_input_container.setStyleSheet("background-color: #2d2d30; border-top: 1px solid #3c4043;")
        chat_input_layout = QVBoxLayout(chat_input_container)
        chat_input_layout.setContentsMargins(15, 15, 15, 15)
        
        # Recipient selector
        recipient_widget = QWidget()
        recipient_layout = QHBoxLayout(recipient_widget)
        recipient_layout.setContentsMargins(0, 0, 0, 5)
        
        to_label = QLabel("To:")
        to_label.setStyleSheet("color: #e8eaed;")
        recipient_layout.addWidget(to_label)
        
        self.recipient_combo = QComboBox()
        self.recipient_combo.addItem("Everyone")
        self.recipient_combo.setFont(QFont("Arial", 10))
        self.recipient_combo.setStyleSheet("""
            QComboBox {
                background-color: #3c4043;
                border: 1px solid #5f6368;
                border-radius: 4px;
                padding: 5px;
                color: #e8eaed;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #e8eaed;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d30;
                color: #e8eaed;
                selection-background-color: #007acc;
                border: 1px solid #5f6368;
            }
        """)
        recipient_layout.addWidget(self.recipient_combo, stretch=1)
        
        select_multiple_btn = QPushButton("...")
        select_multiple_btn.setFixedSize(30, 30)
        select_multiple_btn.clicked.connect(self.show_recipient_selector)
        select_multiple_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border: 1px solid #5f6368;
                border-radius: 4px;
                color: #e8eaed;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
        """)
        recipient_layout.addWidget(select_multiple_btn)
        
        chat_input_layout.addWidget(recipient_widget)
        
        # Message input
        message_input_widget = QWidget()
        message_input_layout = QHBoxLayout(message_input_widget)
        message_input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Send a message...")
        self.chat_input.setFont(QFont("Arial", 11))
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background-color: #3c4043;
                border: 1px solid #5f6368;
                border-radius: 20px;
                padding: 10px 15px;
                color: #e8eaed;
            }
            QLineEdit:focus {
                border: 2px solid #1a73e8;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_chat_message)
        message_input_layout.addWidget(self.chat_input, stretch=1)
        
        send_btn = QPushButton()
        send_icon = self.get_icon('send', '#ffffff')
        if send_icon:
            send_btn.setIcon(send_icon)
            send_btn.setIconSize(QSize(20, 20))
        else:
            send_btn.setText("➤")
            send_btn.setFont(QFont("Arial", 16))
        send_btn.setFixedSize(40, 40)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                border-radius: 20px;
                border: none;
                color: white;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
        """)
        send_btn.clicked.connect(self.send_chat_message)
        message_input_layout.addWidget(send_btn)
        
        chat_input_layout.addWidget(message_input_widget)
        
        chat_panel_layout.addWidget(chat_input_container)
        
        main_layout.addWidget(self.chat_panel)
        self.chat_panel.hide()  # Hidden by default
        
        # File Panel (hidden by default)
        self.file_panel = QWidget()
        self.file_panel.setFixedWidth(350)
        self.file_panel.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-left: 1px solid #3c4043;
            }
        """)
        file_panel_layout = QVBoxLayout(self.file_panel)
        file_panel_layout.setContentsMargins(0, 0, 0, 0)
        file_panel_layout.setSpacing(0)
        
        # File header
        file_header = QWidget()
        file_header.setFixedHeight(60)
        file_header.setStyleSheet("background-color: #2d2d30; border-bottom: 1px solid #3c4043;")
        file_header_layout = QHBoxLayout(file_header)
        file_header_layout.setContentsMargins(20, 10, 20, 10)
        
        file_title = QLabel("Shared Files")
        file_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        file_title.setStyleSheet("color: #e8eaed; border: none; background-color: transparent;")
        file_header_layout.addWidget(file_title)
        
        file_header_layout.addStretch()
        
        close_file_btn = QPushButton("✕")
        close_file_btn.setFixedSize(30, 30)
        close_file_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #e8eaed;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #3c4043;
                border-radius: 15px;
            }
        """)
        close_file_btn.clicked.connect(self.toggle_file_panel)
        file_header_layout.addWidget(close_file_btn)
        
        file_panel_layout.addWidget(file_header)
        
        # File content area
        file_content_scroll = QScrollArea()
        file_content_scroll.setWidgetResizable(True)
        file_content_scroll.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")
        
        file_content_widget = QWidget()
        file_content_layout = QVBoxLayout(file_content_widget)
        file_content_layout.setContentsMargins(20, 20, 20, 20)
        file_content_layout.setSpacing(15)
        
        # Upload button
        upload_btn = QPushButton("📤 Upload File")
        upload_btn.setFixedHeight(40)
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                border-radius: 4px;
                border: none;
                color: white;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
        """)
        upload_btn.clicked.connect(self.upload_file)
        file_content_layout.addWidget(upload_btn)
        
        # File list
        self.file_listbox = QListWidget()
        self.file_listbox.setFont(QFont("Arial", 10))
        self.file_listbox.setStyleSheet("""
            QListWidget {
                background-color: #2d2d30;
                border: 1px solid #3c4043;
                border-radius: 4px;
                color: #e8eaed;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3c4043;
            }
            QListWidget::item:hover {
                background-color: #3c4043;
            }
            QListWidget::item:selected {
                background-color: #007acc;
                color: #ffffff;
            }
        """)
        file_content_layout.addWidget(self.file_listbox, stretch=1)
        
        # File action buttons
        file_actions_widget = QWidget()
        file_actions_layout = QHBoxLayout(file_actions_widget)
        file_actions_layout.setSpacing(10)
        
        download_btn = QPushButton("📥 Download")
        download_btn.setFixedHeight(35)
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border: 1px solid #5f6368;
                border-radius: 4px;
                color: #e8eaed;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
        """)
        download_btn.clicked.connect(self.download_selected_files)
        file_actions_layout.addWidget(download_btn)
        
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setFixedHeight(35)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border: 1px solid #dadce0;
                border-radius: 4px;
                color: #ea4335;
                font-size: 12px;
                border: 1px solid #5f6368;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected_files)
        file_actions_layout.addWidget(delete_btn)
        
        file_content_layout.addWidget(file_actions_widget)
        
        file_content_scroll.setWidget(file_content_widget)
        file_panel_layout.addWidget(file_content_scroll)
        
        main_layout.addWidget(self.file_panel)
        self.file_panel.hide()  # Hidden by default
        
        # People Panel (hidden by default)
        self.people_panel = QWidget()
        self.people_panel.setFixedWidth(350)
        self.people_panel.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-left: 1px solid #3c4043;
            }
        """)
        people_panel_layout = QVBoxLayout(self.people_panel)
        people_panel_layout.setContentsMargins(0, 0, 0, 0)
        people_panel_layout.setSpacing(0)
        
        # People header
        people_header = QWidget()
        people_header.setFixedHeight(60)
        people_header.setStyleSheet("background-color: #2d2d30; border-bottom: 1px solid #3c4043;")
        people_header_layout = QHBoxLayout(people_header)
        people_header_layout.setContentsMargins(20, 10, 20, 10)
        
        people_title = QLabel("Participants")
        people_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        people_title.setStyleSheet("color: #e8eaed; border: none; background-color: transparent;")
        people_header_layout.addWidget(people_title)
        
        people_header_layout.addStretch()
        
        self.people_count_label = QLabel("0")
        self.people_count_label.setFont(QFont("Arial", 12))
        self.people_count_label.setStyleSheet("color: #e8eaed; border: none; background-color: transparent;")
        people_header_layout.addWidget(self.people_count_label)
        
        close_people_btn = QPushButton("✕")
        close_people_btn.setFixedSize(30, 30)
        close_people_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #e8eaed;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #3c4043;
                border-radius: 15px;
            }
        """)
        close_people_btn.clicked.connect(self.toggle_people_panel)
        people_header_layout.addWidget(close_people_btn)
        
        people_panel_layout.addWidget(people_header)
        
        # People list with audio device settings
        people_content_scroll = QScrollArea()
        people_content_scroll.setWidgetResizable(True)
        people_content_scroll.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")
        
        people_content_widget = QWidget()
        people_content_layout = QVBoxLayout(people_content_widget)
        people_content_layout.setContentsMargins(20, 20, 20, 20)
        people_content_layout.setSpacing(15)
        
        self.participants_list = QListWidget()
        self.participants_list.setFont(QFont("Arial", 11))
        self.participants_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d30;
                border: 1px solid #3c4043;
                border-radius: 4px;
                color: #e8eaed;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #3c4043;
            }
            QListWidget::item:selected {
                background-color: #007acc;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #3c4043;
            }
        """)
        people_content_layout.addWidget(self.participants_list, stretch=1)
        
        people_content_scroll.setWidget(people_content_widget)
        people_panel_layout.addWidget(people_content_scroll)
        
        main_layout.addWidget(self.people_panel)
        self.people_panel.hide()  # Hidden by default
        
        # Settings Panel (hidden by default)
        self.settings_panel = QWidget()
        self.settings_panel.setFixedWidth(350)
        self.settings_panel.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-left: 1px solid #3c4043;
            }
        """)
        settings_panel_layout = QVBoxLayout(self.settings_panel)
        settings_panel_layout.setContentsMargins(0, 0, 0, 0)
        settings_panel_layout.setSpacing(0)
        
        # Settings header
        settings_header = QWidget()
        settings_header.setFixedHeight(60)
        settings_header.setStyleSheet("background-color: #2d2d30; border-bottom: 1px solid #3c4043;")
        settings_header_layout = QHBoxLayout(settings_header)
        settings_header_layout.setContentsMargins(20, 10, 20, 10)
        
        settings_title = QLabel("Settings")
        settings_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        settings_title.setStyleSheet("color: #e8eaed; border: none; background-color: transparent;")
        settings_header_layout.addWidget(settings_title)
        
        settings_header_layout.addStretch()
        
        close_settings_btn = QPushButton("✕")
        close_settings_btn.setFixedSize(30, 30)
        close_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #e8eaed;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #3c4043;
                border-radius: 15px;
            }
        """)
        close_settings_btn.clicked.connect(self.toggle_settings_panel)
        settings_header_layout.addWidget(close_settings_btn)
        
        settings_panel_layout.addWidget(settings_header)
        
        # Settings content
        settings_content_scroll = QScrollArea()
        settings_content_scroll.setWidgetResizable(True)
        settings_content_scroll.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")
        
        settings_content_widget = QWidget()
        settings_content_layout = QVBoxLayout(settings_content_widget)
        settings_content_layout.setContentsMargins(20, 20, 20, 20)
        settings_content_layout.setSpacing(15)
        
        # Audio settings section
        audio_group = QGroupBox("Audio Settings")
        audio_group.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        audio_group.setStyleSheet("""
            QGroupBox {
                color: #e8eaed;
                border: 1px solid #3c4043;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        audio_layout = QVBoxLayout(audio_group)
        
        # Microphone selector
        mic_label = QLabel("Microphone:")
        mic_label.setFont(QFont("Arial", 10))
        mic_label.setStyleSheet("color: #e8eaed;")
        audio_layout.addWidget(mic_label)
        
        self.input_device_combo = QComboBox()
        self.input_device_combo.currentTextChanged.connect(self.on_input_device_changed)
        self.input_device_combo.setStyleSheet("""
            QComboBox {
                background-color: #3c4043;
                border: 1px solid #5f6368;
                border-radius: 4px;
                padding: 5px;
                color: #e8eaed;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #e8eaed;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d30;
                color: #e8eaed;
                selection-background-color: #007acc;
                border: 1px solid #5f6368;
            }
        """)
        audio_layout.addWidget(self.input_device_combo)
        
        # Speaker selector
        speaker_label = QLabel("Speaker:")
        speaker_label.setFont(QFont("Arial", 10))
        speaker_label.setStyleSheet("color: #e8eaed;")
        audio_layout.addWidget(speaker_label)
        
        self.output_device_combo = QComboBox()
        self.output_device_combo.currentTextChanged.connect(self.on_output_device_changed)
        self.output_device_combo.setStyleSheet("""
            QComboBox {
                background-color: #3c4043;
                border: 1px solid #5f6368;
                border-radius: 4px;
                padding: 5px;
                color: #e8eaed;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #e8eaed;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d30;
                color: #e8eaed;
                selection-background-color: #007acc;
                border: 1px solid #5f6368;
            }
        """)
        audio_layout.addWidget(self.output_device_combo)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Devices")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border: 1px solid #5f6368;
                border-radius: 4px;
                padding: 5px;
                color: #e8eaed;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_audio_devices)
        audio_layout.addWidget(refresh_btn)
        
        settings_content_layout.addWidget(audio_group)
        settings_content_layout.addStretch()
        
        settings_content_scroll.setWidget(settings_content_widget)
        settings_panel_layout.addWidget(settings_content_scroll)
        
        main_layout.addWidget(self.settings_panel)
        self.settings_panel.hide()  # Hidden by default
        
        # Store file metadata: {file_id: {'filename': name, 'size': size, 'uploader': name}}
        self.shared_files_metadata = {}
        
        # Create initial video grid (will be dynamic)
        self.create_video_grid()
        
        # Initialize audio device lists
        self.refresh_audio_devices()
        
        # Connect signals for thread-safe GUI updates
        self.chat_message_received.connect(self.display_chat_message)
        self.chat_debug_signal.connect(lambda msg: self.chat_display.append(msg))
        self.notification_signal.connect(self.show_chat_notification)
        self.user_join_signal.connect(self.show_user_join_notification)
        
        # Start GUI update loop
        self.update_gui()
    
    def toggle_chat_panel(self):
        """Toggle chat panel visibility"""
        self.chat_panel_visible = not self.chat_panel_visible
        if self.chat_panel_visible:
            self.chat_panel.show()
            # Hide other panels
            self.file_panel.hide()
            self.file_panel_visible = False
            self.people_panel.hide()
            self.people_panel_visible = False
            self.settings_panel.hide()
            self.settings_panel_visible = False
        else:
            self.chat_panel.hide()
    
    def toggle_file_panel(self):
        """Toggle file panel visibility"""
        self.file_panel_visible = not self.file_panel_visible
        if self.file_panel_visible:
            self.file_panel.show()
            # Hide other panels
            self.chat_panel.hide()
            self.chat_panel_visible = False
            self.people_panel.hide()
            self.people_panel_visible = False
            self.settings_panel.hide()
            self.settings_panel_visible = False
        else:
            self.file_panel.hide()
    
    def toggle_people_panel(self):
        """Toggle people panel visibility"""
        self.people_panel_visible = not self.people_panel_visible
        if self.people_panel_visible:
            self.people_panel.show()
            # Hide other panels
            self.chat_panel.hide()
            self.chat_panel_visible = False
            self.file_panel.hide()
            self.file_panel_visible = False
            self.settings_panel.hide()
            self.settings_panel_visible = False
            # Update participant list
            self.update_participants_list()
        else:
            self.people_panel.hide()
    
    def toggle_settings_panel(self):
        """Toggle settings panel visibility"""
        self.settings_panel_visible = not self.settings_panel_visible
        if self.settings_panel_visible:
            self.settings_panel.show()
            # Hide other panels
            self.chat_panel.hide()
            self.chat_panel_visible = False
            self.file_panel.hide()
            self.file_panel_visible = False
            self.people_panel.hide()
            self.people_panel_visible = False
        else:
            self.settings_panel.hide()
    
    def update_participants_list(self):
        """Update the participants list in people panel"""
        self.participants_list.clear()
        with self.users_lock:
            count = len(self.users)
            self.people_count_label.setText(str(count))
            for user_id, username in self.users.items():
                self.participants_list.addItem(f"👤 {username}")
    
    def show_settings_panel(self):
        """Show settings panel"""
        self.toggle_settings_panel()
    
    def toggle_self_video(self):
        """Toggle video capture on/off"""
        self.show_self_video = self.camera_btn.isChecked()
        
        if self.show_self_video:
            # Turn video ON - start capturing and transmitting
            self.start_video_capture()
        else:
            # Turn video OFF - stop capturing and transmitting
            self.stop_video_capture()
        
        # Refresh sidebar if in spotlight mode
        if self.current_layout_mode == "spotlight":
            self.update_spotlight_layout()
    
    def toggle_microphone(self):
        """Toggle microphone on/off"""
        self.microphone_on = self.mic_btn.isChecked()
        if self.microphone_on:
            # Turn microphone ON
            self.start_audio_capture()
        else:
            # Turn microphone OFF
            self.stop_audio_capture()
    
    def toggle_speaker(self):
        """Toggle speaker on/off"""
        # Speaker is always on in new design - audio playback handled automatically
        if hasattr(self, 'speaker_on'):
            if self.speaker_on:
                self.start_audio_playback()
            else:
                self.stop_audio_playback()
    
    def send_chat_message(self):
        """Send a chat message to the server"""
        if not self.connected:
            QMessageBox.warning(self, "Not Connected", "Please connect to the server first.")
            return
        
        message = self.chat_input.text().strip()
        if not message:
            return
        
        try:
            recipient = self.recipient_combo.currentText()
            
            if recipient == "Everyone":
                # Public message
                chat_data = f"CHAT:{message}\n"
                self.tcp_socket.send(chat_data.encode('utf-8'))
            elif recipient.startswith("Multiple ("):
                # Multiple recipients selected
                if self.selected_recipients:
                    recipient_ids = ",".join(map(str, self.selected_recipients))
                    chat_data = f"PRIVATE_CHAT:{recipient_ids}:{message}\n"
                    self.tcp_socket.send(chat_data.encode('utf-8'))
                else:
                    QMessageBox.warning(self, "No Recipients", "Please select recipients first.")
                    return
            else:
                # Single recipient
                # Find the user ID from username
                recipient_id = None
                with self.users_lock:
                    for uid, uname in self.users.items():
                        if uname == recipient:
                            recipient_id = uid
                            break
                
                if recipient_id is not None:
                    chat_data = f"PRIVATE_CHAT:{recipient_id}:{message}\n"
                    self.tcp_socket.send(chat_data.encode('utf-8'))
                else:
                    QMessageBox.critical(self, "Error", "Recipient not found.")
                    return
            
            # Clear input field
            self.chat_input.clear()
            
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error sending chat message: {e}")
            QMessageBox.critical(self, "Chat Error", f"Failed to send message: {e}")
    
    def display_chat_message(self, username, timestamp, message, is_system=False, is_private=False, recipient_names=None):
        """Display a chat message in the chat window"""
        if is_system:
            # System message (e.g., user joined/left)
            text = f"[SYSTEM] {message}"
        elif is_private:
            # Private message
            recipient_text = f" to {', '.join(recipient_names)}" if recipient_names else ""
            text = f"[{timestamp}] [PRIVATE] {username}{recipient_text}: {message}"
        else:
            # Regular chat message
            text = f"[{timestamp}] {username}: {message}"
        
        self.chat_display.append(text)
        
        # Auto-scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Show notification if chat panel is not visible and message is not from self
        if not self.chat_panel_visible and username != self.username:
            notification_type = "Private" if is_private else "Message"
            self.notification_signal.emit(username, message)
    
    def show_recipient_selector(self):
        """Show dialog to select multiple recipients"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Recipients")
        dialog.setFixedSize(300, 400)
        dialog.setModal(True)
        
        # Main layout
        layout = QVBoxLayout(dialog)
        
        # Title
        title_label = QLabel("Select recipients for private message:")
        title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # Scroll area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Checkboxes for each user
        check_boxes = {}
        with self.users_lock:
            for user_id, username in self.users.items():
                if user_id != self.client_id:  # Don't include self
                    checkbox = QCheckBox(username)
                    checkbox.setChecked(user_id in self.selected_recipients)
                    scroll_layout.addWidget(checkbox)
                    check_boxes[user_id] = checkbox
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        def apply_selection():
            self.selected_recipients = [uid for uid, cb in check_boxes.items() if cb.isChecked()]
            
            if self.selected_recipients:
                # Update dropdown to show "Multiple (X users)"
                count = len(self.selected_recipients)
                self.recipient_combo.setCurrentText(f"Multiple ({count} user{'s' if count > 1 else ''})")
            else:
                self.recipient_combo.setCurrentText("Everyone")
            
            dialog.accept()
        
        # Buttons
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(apply_selection)
        btn_layout.addWidget(apply_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addWidget(btn_widget)
        
        dialog.exec()
    
    def update_recipient_list(self):
        """Update the recipient dropdown with current users and participants list"""
        try:
            # Safety check - ensure GUI is initialized
            if not hasattr(self, 'recipient_combo'):
                return
                
            current_selection = self.recipient_combo.currentText()
            is_multiple_selection = current_selection.startswith("Multiple (")
            
            # Build list of recipients
            recipients = ["Everyone"]
            
            with self.users_lock:
                for user_id, username in self.users.items():
                    if user_id != self.client_id:  # Don't include self
                        recipients.append(username)
            
            # Update combobox
            self.recipient_combo.clear()
            self.recipient_combo.addItems(recipients)
            
            # If there was a multiple selection, re-add it and restore
            if is_multiple_selection and self.selected_recipients:
                # Validate that selected recipients still exist
                valid_recipients = []
                with self.users_lock:
                    for rid in self.selected_recipients:
                        if rid in self.users:
                            valid_recipients.append(rid)
                
                if valid_recipients:
                    self.selected_recipients = valid_recipients
                    count = len(valid_recipients)
                    multiple_text = f"Multiple ({count} user{'s' if count > 1 else ''})"
                    self.recipient_combo.addItem(multiple_text)
                    self.recipient_combo.setCurrentText(multiple_text)
                else:
                    # All selected recipients left, reset
                    self.selected_recipients = []
                    self.recipient_combo.setCurrentText("Everyone")
            elif current_selection in recipients:
                # Restore previous single selection
                self.recipient_combo.setCurrentText(current_selection)
            else:
                # Reset to "Everyone"
                self.recipient_combo.setCurrentText("Everyone")
            
            # Update participants list in people panel
            self.update_participants_list()
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error updating recipient list: {e}")
    
    def upload_file(self):
        """Upload a file to share with other users"""
        if not self.connected:
            QMessageBox.warning(self, "Not Connected", "Please connect to the server first.")
            return
        
        # Open file dialog
        filepath, _ = QFileDialog.getOpenFileName(self, "Select File to Share")
        
        if not filepath:
            return
        
        try:
            import os
            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)
            
            # Check file size
            if filesize > MAX_FILE_SIZE:
                QMessageBox.critical(self, "File Too Large", 
                                   f"File size ({filesize / (1024*1024):.2f} MB) exceeds maximum allowed size ({MAX_FILE_SIZE / (1024*1024):.0f} MB).")
                return
            
            # Create progress dialog
            progress_dialog = QDialog(self)
            progress_dialog.setWindowTitle("Uploading File")
            progress_dialog.setFixedSize(400, 150)
            progress_dialog.setModal(True)
            
            dialog_layout = QVBoxLayout(progress_dialog)
            
            title_label = QLabel(f"Uploading: {filename}")
            title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            dialog_layout.addWidget(title_label)
            
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            dialog_layout.addWidget(progress_bar)
            
            status_label = QLabel("0%")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dialog_layout.addWidget(status_label)
            
            progress_dialog.show()
            
            # Upload in background thread
            def do_upload():
                try:
                    # Connect to file transfer port
                    file_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    file_sock.connect((self.server_address, SERVER_FILE_PORT))
                    
                    # Send upload command with newline delimiter
                    command = f"UPLOAD:{self.client_id}:{filename}:{filesize}\n"
                    file_sock.send(command.encode('utf-8'))
                    
                    # Send file data
                    with open(filepath, 'rb') as f:
                        sent = 0
                        while sent < filesize:
                            chunk = f.read(FILE_CHUNK_SIZE)
                            if not chunk:
                                break
                            file_sock.sendall(chunk)
                            sent += len(chunk)
                            
                            # Update progress using QTimer.singleShot for thread safety
                            percent = (sent / filesize) * 100
                            QTimer.singleShot(0, lambda p=percent: progress_bar.setValue(int(p)))
                            QTimer.singleShot(0, lambda p=percent: status_label.setText(f"{p:.1f}%"))
                    
                    # Wait for response
                    response = file_sock.recv(1024).decode('utf-8')
                    file_sock.close()
                    
                    if response.startswith("SUCCESS"):
                        QTimer.singleShot(0, progress_dialog.close)
                        QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"File '{filename}' uploaded successfully!"))
                    else:
                        QTimer.singleShot(0, progress_dialog.close)
                        QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Upload Failed", "File upload failed on server."))
                    
                except Exception as e:
                    print(f"[{self.get_timestamp()}] Error uploading file: {e}")
                    QTimer.singleShot(0, progress_dialog.close)
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Upload Error", f"Failed to upload file: {e}"))
            
            threading.Thread(target=do_upload, daemon=True).start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to upload file: {e}")
    
    def download_selected_files(self):
        """Download all checked files"""
        if not self.connected:
            QMessageBox.warning(self, "Not Connected", "Please connect to the server first.")
            return
        
        # Get all checked items
        checked_items = []
        for i in range(self.file_listbox.count()):
            item = self.file_listbox.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                file_id = item.data(Qt.ItemDataRole.UserRole)
                checked_items.append((file_id, item))
        
        if not checked_items:
            QMessageBox.warning(self, "No Selection", "Please check files to download.")
            return
        
        # Download each file
        for file_id, item in checked_items:
            if file_id in self.shared_files_metadata:
                self._download_single_file(file_id)
    
    def delete_selected_files(self):
        """Delete all checked files (only your uploads)"""
        if not self.connected:
            QMessageBox.warning(self, "Not Connected", "Please connect to the server first.")
            return
        
        # Get all checked items that belong to this user
        checked_own_files = []
        checked_other_files = []
        
        for i in range(self.file_listbox.count()):
            item = self.file_listbox.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                file_id = item.data(Qt.ItemDataRole.UserRole)
                uploader_id = item.data(Qt.ItemDataRole.UserRole + 1)
                
                if uploader_id == self.client_id:
                    checked_own_files.append(file_id)
                else:
                    checked_other_files.append(file_id)
        
        if not checked_own_files and not checked_other_files:
            QMessageBox.warning(self, "No Selection", "Please check files to delete.")
            return
        
        if checked_other_files:
            QMessageBox.warning(self, "Not Authorized", 
                              f"You can only delete your own uploads. {len(checked_other_files)} file(s) skipped.")
        
        if not checked_own_files:
            return
        
        # Confirm deletion
        reply = QMessageBox.question(self, "Confirm Delete", 
                                    f"Delete {len(checked_own_files)} file(s)?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            for file_id in checked_own_files:
                self._delete_single_file(file_id)
    
    def _delete_single_file(self, file_id):
        """Delete a single file on the server"""
        def do_delete():
            try:
                # Connect to file transfer port
                file_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                file_sock.connect((self.server_address, SERVER_FILE_PORT))
                
                # Send delete request
                command = f"DELETE:{file_id}:{self.client_id}\n"
                file_sock.send(command.encode('utf-8'))
                
                # Wait for response
                response = file_sock.recv(1024).decode('utf-8')
                file_sock.close()
                
                if response.startswith("DELETE_SUCCESS"):
                    print(f"[{self.get_timestamp()}] File {file_id} deleted successfully")
                elif response.startswith("ERROR"):
                    error_msg = response.split(":", 1)[1] if ":" in response else "Unknown error"
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Delete Failed", error_msg))
                    
            except Exception as e:
                print(f"[{self.get_timestamp()}] Error deleting file: {e}")
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Delete Error", 
                                                                 f"Failed to delete file: {e}"))
        
        threading.Thread(target=do_delete, daemon=True).start()
    
    def _download_single_file(self, file_id):
        """Download a single file - helper method"""
        if file_id not in self.shared_files_metadata:
            return
            
        file_info = self.shared_files_metadata[file_id]
        filename = file_info['filename']
        filesize = file_info['size']
        
        # Ask where to save
        save_path, _ = QFileDialog.getSaveFileName(self, "Save File", filename)
        if not save_path:
            return
        
        # Create progress dialog
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle(f"Downloading {filename}")
        progress_dialog.setModal(True)
        progress_dialog.setFixedSize(400, 100)
        
        dialog_layout = QVBoxLayout(progress_dialog)
        
        progress_bar = QProgressBar()
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        dialog_layout.addWidget(progress_bar)
        
        status_label = QLabel("0%")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dialog_layout.addWidget(status_label)
        
        progress_dialog.show()
        
        # Download in background thread
        def do_download():
            try:
                # Connect to file transfer port
                file_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                file_sock.connect((self.server_address, SERVER_FILE_PORT))
                
                # Send download request with newline delimiter
                command = f"DOWNLOAD:{file_id}\n"
                file_sock.send(command.encode('utf-8'))
                
                # Receive file info
                response = file_sock.recv(1024).decode('utf-8')
                if response.startswith("FILE:"):
                    # Receive file data
                    with open(save_path, 'wb') as f:
                        received = 0
                        while received < filesize:
                            chunk_size = min(FILE_CHUNK_SIZE, filesize - received)
                            chunk = file_sock.recv(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            received += len(chunk)
                            
                            # Update progress using QTimer.singleShot for thread safety
                            percent = (received / filesize) * 100
                            QTimer.singleShot(0, lambda p=percent: progress_bar.setValue(int(p)))
                            QTimer.singleShot(0, lambda p=percent: status_label.setText(f"{p:.1f}%"))
                    
                    file_sock.close()
                    
                    if received == filesize:
                        QTimer.singleShot(0, progress_dialog.close)
                        QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", 
                                                                             f"File '{filename}' downloaded successfully!"))
                    else:
                        QTimer.singleShot(0, progress_dialog.close)
                        QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Download Failed", 
                                                                         "File download incomplete."))
                else:
                    file_sock.close()
                    QTimer.singleShot(0, progress_dialog.close)
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Download Failed", 
                                                                     "File not found on server."))
                    
            except Exception as e:
                print(f"[{self.get_timestamp()}] Error downloading file: {e}")
                QTimer.singleShot(0, progress_dialog.close)
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Download Error", 
                                                                 f"Failed to download file: {e}"))
        
        threading.Thread(target=do_download, daemon=True).start()
    
    def download_file(self):
        """Download the selected file"""
        if not self.connected:
            QMessageBox.warning(self, "Not Connected", "Please connect to the server first.")
            return
        
        # Get selected file
        current_item = self.file_listbox.currentRow()
        if current_item < 0:
            QMessageBox.warning(self, "No Selection", "Please select a file to download.")
            return
        
        file_text = self.file_listbox.item(current_item).text()
        
        # Extract file_id from the text (format: "filename (size) - uploader [ID: file_id]")
        try:
            file_id = int(file_text.split("[ID: ")[1].rstrip("]"))
            file_info = self.shared_files_metadata[file_id]
            filename = file_info['filename']
            filesize = file_info['size']
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get file info: {e}")
            return
        
        # Choose save location
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            filename,
            f"All Files (*.*)"
        )
        
        if not save_path:
            return
        
        # Create progress dialog
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Downloading File")
        progress_dialog.setFixedSize(400, 150)
        progress_dialog.setModal(True)
        
        dialog_layout = QVBoxLayout(progress_dialog)
        
        title_label = QLabel(f"Downloading: {filename}")
        title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        dialog_layout.addWidget(title_label)
        
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        dialog_layout.addWidget(progress_bar)
        
        status_label = QLabel("0%")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dialog_layout.addWidget(status_label)
        
        progress_dialog.show()
        
        # Download in background thread
        def do_download():
            try:
                # Connect to file transfer port
                file_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                file_sock.connect((self.server_address, SERVER_FILE_PORT))
                
                # Send download request with newline delimiter
                command = f"DOWNLOAD:{file_id}\n"
                file_sock.send(command.encode('utf-8'))
                
                # Receive file info
                response = file_sock.recv(1024).decode('utf-8')
                if response.startswith("FILE:"):
                    # Receive file data
                    with open(save_path, 'wb') as f:
                        received = 0
                        while received < filesize:
                            chunk_size = min(FILE_CHUNK_SIZE, filesize - received)
                            chunk = file_sock.recv(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            received += len(chunk)
                            
                            # Update progress using QTimer.singleShot for thread safety
                            percent = (received / filesize) * 100
                            QTimer.singleShot(0, lambda p=percent: progress_bar.setValue(int(p)))
                            QTimer.singleShot(0, lambda p=percent: status_label.setText(f"{p:.1f}%"))
                    
                    file_sock.close()
                    
                    if received == filesize:
                        QTimer.singleShot(0, progress_dialog.close)
                        QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"File '{filename}' downloaded successfully!"))
                    else:
                        QTimer.singleShot(0, progress_dialog.close)
                        QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Download Failed", "File download incomplete."))
                else:
                    file_sock.close()
                    QTimer.singleShot(0, progress_dialog.close)
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Download Failed", "File not found on server."))
                    
            except Exception as e:
                print(f"[{self.get_timestamp()}] Error downloading file: {e}")
                QTimer.singleShot(0, progress_dialog.close)
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Download Error", f"Failed to download file: {e}"))
        
        threading.Thread(target=do_download, daemon=True).start()
    
    def update_file_list(self):
        """Update the file listbox with available files"""
        self.file_listbox.clear()
        
        for file_id, info in self.shared_files_metadata.items():
            filename = info['filename']
            size_mb = info['size'] / (1024 * 1024)
            uploader = info['uploader']
            uploader_id = info['uploader_id']
            
            # Format display text
            is_own_file = (uploader_id == self.client_id)
            display_text = f"{filename} ({size_mb:.2f} MB) - {uploader}"
            if is_own_file:
                display_text += " (Your upload)"
            
            # Create list item with checkbox
            item = QListWidgetItem(display_text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, file_id)  # Store file_id in item
            item.setData(Qt.ItemDataRole.UserRole + 1, uploader_id)  # Store uploader_id
            
            self.file_listbox.addItem(item)
    
    def toggle_screen_sharing(self):
        """Toggle screen sharing on/off"""
        if not self.is_presenting:
            # Start screen sharing in background thread to avoid blocking GUI
            def start_in_background():
                try:
                    if not self.start_screen_sharing():
                        # Revert on failure
                        QTimer.singleShot(0, lambda: QMessageBox.warning(self, "Screen Sharing", 
                                                                          "Could not start screen sharing. Another user may be presenting."))
                except Exception as e:
                    print(f"[{self.get_timestamp()}] Error in start_in_background: {e}")
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", f"Failed to start screen sharing: {e}"))
            
            threading.Thread(target=start_in_background, daemon=True).start()
            self.is_presenting = True  # Optimistically set
        else:
            # Stop screen sharing (also in background to avoid blocking)
            def stop_in_background():
                try:
                    self.stop_screen_sharing()
                except Exception as e:
                    print(f"[{self.get_timestamp()}] Error in stop_in_background: {e}")
            
            threading.Thread(target=stop_in_background, daemon=True).start()
            self.is_presenting = False
    
    def show_layout_menu(self):
        """Show popup menu with layout options"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 5px;
            }
            QMenu::item {
                color: #e0e0e0;
                padding: 8px 30px 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #007acc;
            }
            QMenu::icon {
                padding-left: 10px;
            }
        """)
        
        # Tiled layout action
        tiled_action = QAction("⊞  Tiled View", self)
        tiled_action.triggered.connect(self.switch_to_tiled_layout)
        if self.current_layout_mode == "tiled":
            tiled_action.setCheckable(True)
            tiled_action.setChecked(True)
        menu.addAction(tiled_action)
        
        # Spotlight layout action
        spotlight_action = QAction("◉  Spotlight View", self)
        spotlight_action.triggered.connect(self.switch_to_spotlight_layout)
        if self.current_layout_mode == "spotlight":
            spotlight_action.setCheckable(True)
            spotlight_action.setChecked(True)
        menu.addAction(spotlight_action)
        
        # Show menu at button position
        sender = self.sender()
        menu.exec(sender.mapToGlobal(sender.rect().bottomLeft()))
    
    def switch_to_tiled_layout(self):
        """Switch to tiled layout view"""
        self.layout_mode = "tiled"
        self.current_layout_mode = "tiled"
        self.apply_layout()
    
    def switch_to_spotlight_layout(self):
        """Switch to spotlight layout view"""
        self.layout_mode = "spotlight"
        self.current_layout_mode = "spotlight"
        self.apply_layout()
    
    def change_layout(self, event=None):
        """Change video layout mode (Google Meet style)"""
        self.layout_mode = self.layout_combo.currentText().lower()
        self.determine_and_apply_layout()
    
    def determine_and_apply_layout(self):
        """Determine the actual layout based on mode and current state"""
        # Manual mode selection - don't auto-switch
        self.current_layout_mode = self.layout_mode
        
        # Apply the layout
        self.apply_layout()
    
    def apply_layout(self):
        """Apply the current layout mode"""
        if self.current_layout_mode == "tiled":
            # Show tiled grid, hide spotlight
            self.video_frame.show()
            self.spotlight_container.hide()
            self.create_video_grid()
        elif self.current_layout_mode == "spotlight":
            # Show spotlight, hide tiled grid
            self.video_frame.hide()
            self.spotlight_container.show()
            self.update_spotlight_layout()
    
    def calculate_grid_size(self, num_videos):
        """Calculate optimal grid size based on number of videos"""
        # Automatic layout based on number of videos
        if num_videos <= 1:
            return 1, 1
        elif num_videos <= 4:
            return 2, 2
        elif num_videos <= 9:
            return 3, 3
        else:
            return 4, 4
    
    def create_video_grid(self):
        """Create a dynamic grid of video display labels (Tiled mode - Google Meet style)"""
        # Clear existing grid
        if self.video_frame.layout() is not None:
            QWidget().setLayout(self.video_frame.layout())  # Clear the layout
        
        grid_layout = QGridLayout(self.video_frame)
        grid_layout.setSpacing(5)
        
        self.video_labels = {}
        
        # Calculate how many tiles we need (participants + screen share if active)
        num_participants = len(self.video_streams) + 1  # +1 for self
        has_screen_share = self.current_presenter_id is not None
        total_tiles = num_participants + (1 if has_screen_share else 0)
        
        # Get grid size
        rows, cols = self.calculate_grid_size(total_tiles)
        max_tiles = rows * cols
        
        # Create grid positions
        idx = 0
        for row in range(rows):
            for col in range(cols):
                if idx >= max_tiles:
                    break
                    
                # Container frame for each video
                container = QFrame()
                container.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
                container.setLineWidth(1)
                container_layout = QVBoxLayout(container)
                container_layout.setContentsMargins(2, 2, 2, 2)
                
                # Username label
                username_label = QLabel("")
                username_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                username_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                container_layout.addWidget(username_label)
                
                # Video label - centered with black background
                video_label = QLabel("No Video")
                video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                video_label.setStyleSheet("background-color: black; color: white;")
                video_label.setMinimumSize(160, 120)  # Minimum size in pixels
                video_label.setScaledContents(True)  # Scale pixmap to fit label
                container_layout.addWidget(video_label, stretch=1)
                
                grid_layout.addWidget(container, row, col)
                
                self.video_labels[idx] = {
                    'container': container,
                    'username': username_label,
                    'video': video_label,
                    'client_id': None,
                    'is_screen': False  # Track if this tile shows screen share
                }
                idx += 1
    
    def update_spotlight_layout(self):
        """Update spotlight mode layout - main content + sidebar thumbnails"""
        # Clear existing sidebar widgets
        for i in reversed(range(self.sidebar_widget_layout.count())):
            widget = self.sidebar_widget_layout.itemAt(i).widget()
            if widget is not None and widget != self.sidebar_widget_layout.itemAt(self.sidebar_widget_layout.count() - 1).widget():
                widget.deleteLater()
        
        # Determine spotlight content (screen share takes priority, then active speaker)
        spotlight_client_id = None
        spotlight_is_screen = False
        
        if self.current_presenter_id is not None:
            # Screen sharing is active - show in spotlight
            spotlight_client_id = self.current_presenter_id
            spotlight_is_screen = True
        else:
            # No screen share - show first participant (or implement speaker detection later)
            with self.streams_lock:
                if len(self.video_streams) > 0:
                    spotlight_client_id = list(self.video_streams.keys())[0]
        
        # Store for update_gui to use
        self.spotlight_client_id = spotlight_client_id
        self.spotlight_is_screen = spotlight_is_screen
        
        # Create sidebar thumbnails for ALL participants (always show sidebar in spotlight mode)
        participants_to_show = []
        
        # Add self if showing self video (camera is ON)
        if self.show_self_video and self.camera_btn.isChecked():
            participants_to_show.append(('self', self.client_id, self.username))
        
        # Add other participants (excluding spotlight participant if it's a video)
        with self.streams_lock:
            with self.users_lock:
                for client_id in self.video_streams.keys():
                    if not spotlight_is_screen and client_id == spotlight_client_id:
                        continue  # Skip the spotlight participant
                    username = self.users.get(client_id, f"User {client_id}")
                    participants_to_show.append(('other', client_id, username))
        
        # Create thumbnail widgets
        for participant_type, client_id, username in participants_to_show:
            thumbnail = self.create_sidebar_thumbnail(participant_type, client_id, username)
            self.sidebar_widget_layout.insertWidget(self.sidebar_widget_layout.count() - 1, thumbnail)
        
        # Always show sidebar in spotlight mode if there are participants
        if len(participants_to_show) > 0:
            self.participants_sidebar.show()
        else:
            self.participants_sidebar.hide()
    
    def create_sidebar_thumbnail(self, participant_type, client_id, username):
        """Create a thumbnail widget for the sidebar"""
        container = QFrame()
        container.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        container.setLineWidth(1)
        container.setMaximumHeight(100)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # Username label
        name_label = QLabel(username)
        name_label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)
        
        # Video thumbnail
        video_label = QLabel("No Video")
        video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_label.setStyleSheet("background-color: black; color: white;")
        video_label.setMinimumSize(80, 60)
        video_label.setMaximumSize(200, 150)
        video_label.setScaledContents(True)  # Scale pixmap to fit label
        layout.addWidget(video_label, stretch=1)
        
        # Store reference for updates
        container.video_label = video_label
        container.client_id = client_id
        container.participant_type = participant_type
        
        return container
    
    def update_gui(self):
        """Update GUI with current video frames (Google Meet style - supports Tiled and Spotlight modes)"""
        try:
            # Update meeting info in bottom bar
            if self.connected:
                with self.users_lock:
                    user_count = len(self.users)
                    timestamp = self.get_timestamp()
                    self.meeting_info_label.setText(f"⏱️ {timestamp} • {user_count} participant{'s' if user_count != 1 else ''}")
            else:
                self.meeting_info_label.setText("Not connected")
            
            # Clean up stale video streams
            with self.streams_lock:
                current_time = time.time()
                stale_clients = []
                for client_id, last_update in self.video_stream_timestamps.items():
                    if current_time - last_update > 2.0:  # 2 second timeout
                        stale_clients.append(client_id)
                
                for client_id in stale_clients:
                    if client_id in self.video_streams:
                        del self.video_streams[client_id]
                    del self.video_stream_timestamps[client_id]
                    print(f"[{self.get_timestamp()}] Removed stale video stream for user {client_id}")
            
            # Re-evaluate layout if screen sharing state changed
            old_presenter = getattr(self, '_last_presenter_id', None)
            if old_presenter != self.current_presenter_id:
                self._last_presenter_id = self.current_presenter_id
                if self.layout_mode == "auto":
                    self.determine_and_apply_layout()
            
            # Update based on current layout mode
            if self.current_layout_mode == "tiled":
                self._update_tiled_layout()
            elif self.current_layout_mode == "spotlight":
                self._update_spotlight_layout_content()
            
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error updating GUI: {e}")
        
        # Schedule next update using QTimer
        QTimer.singleShot(33, self.update_gui)  # ~30 FPS
    
    def _update_tiled_layout(self):
        """Update tiled grid layout with all videos + screen share"""
        # Build display streams
        display_streams = {}
        
        # Other clients' video
        with self.streams_lock:
            for client_id, frame in self.video_streams.items():
                display_streams[client_id] = ('video', frame, client_id)
        
        # Self video (from camera) - only if capturing
        if self.capturing and self.camera is not None:
            ret, frame = self.camera.read()
            if ret:
                display_streams[self.client_id] = ('video', frame, self.client_id)
        
        # Screen share as a tile (if active)
        with self.screen_lock:
            screen_frame_copy = self.shared_screen_frame
        
        # Show screen if we have a frame and a presenter
        if screen_frame_copy is not None:
            presenter_id = self.current_presenter_id if self.current_presenter_id is not None else self.client_id
            display_streams['screen'] = ('screen', screen_frame_copy, presenter_id)
        
        # Check if we need to recreate the grid (number of tiles changed)
        num_tiles_needed = len(display_streams)
        num_tiles_available = len(self.video_labels)
        
        if num_tiles_needed != num_tiles_available:
            # Recreate grid with correct number of tiles
            self.create_video_grid()
        
        # Calculate video size
        container_width = self.video_frame.width()
        container_height = self.video_frame.height()
        
        num_tiles = len(display_streams)
        rows, cols = self.calculate_grid_size(num_tiles)
        
        if container_width > 1 and container_height > 1:
            cell_width = (container_width // cols) - 20
            cell_height = (container_height // rows) - 50
            
            aspect_ratio = 4.0 / 3.0
            video_width = max(160, cell_width)
            video_height = int(video_width / aspect_ratio)
            
            if video_height > cell_height:
                video_height = max(120, cell_height)
                video_width = int(video_height * aspect_ratio)
        else:
            video_width = 320
            video_height = 240
        
        # Update grid tiles
        display_index = 0
        for idx, label_info in self.video_labels.items():
            if display_index < len(display_streams):
                tile_key = list(display_streams.keys())[display_index]
                tile_type, frame_data, source_client_id = display_streams[tile_key]
                
                # Get username/label
                if tile_type == 'screen':
                    with self.users_lock:
                        presenter_name = self.users.get(source_client_id, "Unknown")
                    username = f"📺 {presenter_name}'s Screen"
                else:
                    with self.users_lock:
                        username = self.users.get(source_client_id, f"User {source_client_id}")
                    if source_client_id == self.client_id:
                        username = f"{username} (You)"
                
                label_info['username'].setText(username)
                
                # Process and display frame
                try:
                    if tile_type == 'screen':
                        # Screen frame is compressed
                        nparr = np.frombuffer(frame_data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    else:
                        frame = frame_data
                    
                    if frame is not None:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frame_resized = cv2.resize(frame_rgb, (video_width, video_height))
                        
                        height, width, channel = frame_resized.shape
                        bytes_per_line = 3 * width
                        q_image = QImage(frame_resized.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                        pixmap = QPixmap.fromImage(q_image)
                        
                        label_info['video'].setPixmap(pixmap)
                        label_info['video'].setText("")
                except Exception as e:
                    print(f"[{self.get_timestamp()}] Error displaying tile: {e}")
                
                label_info['client_id'] = source_client_id
                label_info['is_screen'] = (tile_type == 'screen')
                label_info['container'].show()
                display_index += 1
            else:
                # Hide unused slots
                label_info['container'].hide()
                label_info['client_id'] = None
                label_info['is_screen'] = False
    
    def _update_spotlight_layout_content(self):
        """Update spotlight layout content - main spotlight + sidebar thumbnails"""
        # Update main spotlight
        spotlight_frame = None
        spotlight_name = ""
        
        with self.screen_lock:
            screen_frame_copy = self.shared_screen_frame
        
        if screen_frame_copy is not None and self.current_presenter_id is not None:
            # Screen sharing is active - show in spotlight
            try:
                nparr = np.frombuffer(screen_frame_copy, np.uint8)
                spotlight_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                with self.users_lock:
                    presenter_name = self.users.get(self.current_presenter_id, "Unknown")
                spotlight_name = f"📺 {presenter_name}'s Screen"
            except Exception as e:
                print(f"[{self.get_timestamp()}] Error decoding screen: {e}")
        else:
            # No screen share - show first participant or self
            with self.streams_lock:
                if len(self.video_streams) > 0:
                    first_client_id = list(self.video_streams.keys())[0]
                    spotlight_frame = self.video_streams[first_client_id]
                    
                    with self.users_lock:
                        spotlight_name = self.users.get(first_client_id, f"User {first_client_id}")
                elif self.capturing and self.camera is not None:
                    ret, spotlight_frame = self.camera.read()
                    if ret:
                        spotlight_name = f"{self.username} (You)"
        
        # Display spotlight content
        if spotlight_frame is not None:
            try:
                # Resize to fit spotlight area
                spotlight_width = self.spotlight_main.width() - 40
                if spotlight_width < 100:
                    spotlight_width = 600
                
                aspect = spotlight_frame.shape[1] / spotlight_frame.shape[0]
                spotlight_height = int(spotlight_width / aspect)
                
                frame_rgb = cv2.cvtColor(spotlight_frame, cv2.COLOR_BGR2RGB)
                frame_resized = cv2.resize(frame_rgb, (spotlight_width, spotlight_height))
                
                height, width, channel = frame_resized.shape
                bytes_per_line = 3 * width
                q_image = QImage(frame_resized.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)
                
                self.spotlight_label.setPixmap(pixmap)
                self.spotlight_label.setText("")
                self.spotlight_name_label.setText(spotlight_name)
            except Exception as e:
                print(f"[{self.get_timestamp()}] Error displaying spotlight: {e}")
        else:
            self.spotlight_label.clear()
            self.spotlight_label.setText("No Content")
            self.spotlight_name_label.setText("")
        
        # Update sidebar thumbnails
        for i in range(self.sidebar_widget_layout.count()):
            item = self.sidebar_widget_layout.itemAt(i)
            if item and item.widget():
                thumbnail = item.widget()
                if hasattr(thumbnail, 'client_id') and hasattr(thumbnail, 'video_label'):
                    client_id = thumbnail.client_id
                    participant_type = thumbnail.participant_type
                    
                    # Get frame for this participant
                    frame = None
                    if participant_type == 'self' and self.capturing and self.camera is not None:
                        ret, frame = self.camera.read()
                        if not ret:
                            frame = None
                    elif participant_type == 'other':
                        with self.streams_lock:
                            frame = self.video_streams.get(client_id)
                    
                    # Update thumbnail
                    if frame is not None:
                        try:
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            frame_resized = cv2.resize(frame_rgb, (100, 75))
                            
                            height, width, channel = frame_resized.shape
                            bytes_per_line = 3 * width
                            q_image = QImage(frame_resized.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                            pixmap = QPixmap.fromImage(q_image)
                            
                            thumbnail.video_label.setPixmap(pixmap)
                            thumbnail.video_label.setText("")
                        except Exception as e:
                            print(f"[{self.get_timestamp()}] Error updating thumbnail: {e}")
    
    def closeEvent(self, event):
        """Handle window close event (QMainWindow override)"""
        self.on_closing()
        event.accept()
    
    def on_closing(self):
        """Handle window closing"""
        self.disconnect()
        # Don't call self.close() here as it creates a loop with closeEvent
    
    def disconnect(self):
        """Disconnect from server"""
        print(f"[{self.get_timestamp()}] Disconnecting...")
        
        self.connected = False
        self.capturing = False
        self.audio_capturing = False
        self.audio_playing = False
        
        # Release camera
        if self.camera is not None:
            self.camera.release()
        
        # Close audio streams
        try:
            if self.audio_stream_input:
                self.audio_stream_input.stop_stream()
                self.audio_stream_input.close()
        except:
            pass
        
        try:
            if self.audio_stream_output:
                self.audio_stream_output.stop_stream()
                self.audio_stream_output.close()
        except:
            pass
        
        # Terminate PyAudio
        try:
            if self.pyaudio_instance:
                self.pyaudio_instance.terminate()
        except:
            pass
        
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
        
        try:
            if self.audio_udp_socket:
                self.audio_udp_socket.close()
        except:
            pass
        
        print(f"[{self.get_timestamp()}] Disconnected")


class ConnectionDialog(QDialog):
    """Dialog for getting server IP and username"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None
        
        self.setWindowTitle("Connect to Server")
        self.setFixedSize(350, 200)
        self.setModal(True)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Form layout for inputs
        form_widget = QWidget()
        form_layout = QGridLayout(form_widget)
        
        # Server IP
        form_layout.addWidget(QLabel("Server IP Address:"), 0, 0)
        self.ip_entry = QLineEdit()
        self.ip_entry.setText("127.0.0.1")  # Default to localhost
        form_layout.addWidget(self.ip_entry, 0, 1)
        
        # Username
        form_layout.addWidget(QLabel("Username:"), 1, 0)
        self.username_entry = QLineEdit()
        self.username_entry.setText("User")
        form_layout.addWidget(self.username_entry, 1, 1)
        
        layout.addWidget(form_widget)
        
        # Buttons
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(self.on_connect)
        button_layout.addWidget(connect_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.on_cancel)
        button_layout.addWidget(cancel_btn)
        
        layout.addWidget(button_widget)
        
        # Focus on IP entry
        self.ip_entry.setFocus()
    
    def on_connect(self):
        """Handle connect button"""
        server_ip = self.ip_entry.text().strip()
        username = self.username_entry.text().strip()
        
        if not server_ip:
            QMessageBox.critical(self, "Error", "Please enter server IP address")
            return
        
        if not username:
            QMessageBox.critical(self, "Error", "Please enter a username")
            return
        
        self.result = (server_ip, username)
        self.accept()
    
    def on_cancel(self):
        """Handle cancel button"""
        self.result = None
        self.reject()
    
    def get_result(self):
        """Get the result after dialog is closed"""
        return self.result


def main():
    """Main entry point"""
    # Create QApplication
    app = QApplication(sys.argv)
    
    # Create client
    client = VideoConferenceClient()
    
    # Create GUI
    client.create_gui()
    
    # Show connection dialog
    dialog = ConnectionDialog(client)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        result = dialog.get_result()
        
        if result:
            server_ip, username = result
            
            # Connect to server
            if client.connect_to_server(server_ip, username):
                # Start video capture
                client.start_video_capture()
                
                # Start audio capture and playback
                client.start_audio_capture()
                client.start_audio_playback()
                
                # Show main window
                client.show()
                
                # Run event loop
                sys.exit(app.exec())
            else:
                QMessageBox.critical(None, "Connection Error", "Failed to connect to server")
                sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
