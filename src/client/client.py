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
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import mss

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import *


class VideoConferenceClient:
    def __init__(self):
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
        
        # Screen sharing
        self.screen_socket = None  # TCP control socket
        self.screen_udp_socket = None  # UDP data socket
        self.is_presenting = False
        self.screen_sharing_active = False
        self.current_presenter_id = None
        self.shared_screen_frame = None
        self.screen_lock = threading.Lock()
        
        # GUI
        self.root = None
        self.video_labels = {}
        self.screen_label = None  # Label for displaying shared screen
        
        # UI Settings (will be initialized after root window is created)
        self.show_self_video = None  # Will be BooleanVar
        self.microphone_on = None  # Will be BooleanVar
        self.speaker_on = None  # Will be BooleanVar
        self.current_layout = "auto"  # auto, 1x1, 2x2, 3x3, 4x4
        
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
            self.input_device_combo['values'] = input_names
            if len(input_names) > 0 and self.selected_input_device is None:
                self.input_device_combo.current(0)
                self.selected_input_device = devices['input'][0]['index']
        
        # Update output device dropdown
        output_names = [d['name'] for d in devices['output']]
        if hasattr(self, 'output_device_combo'):
            self.output_device_combo['values'] = output_names
            if len(output_names) > 0 and self.selected_output_device is None:
                self.output_device_combo.current(0)
                self.selected_output_device = devices['output'][0]['index']
    
    def on_input_device_changed(self, event=None):
        """Handle input device selection change"""
        if not hasattr(self, 'input_device_combo'):
            return
        
        devices = self.get_audio_devices()
        selected_name = self.input_device_combo.get()
        
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
        selected_name = self.output_device_combo.get()
        
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
                        except:
                            pass
                    
                    elif message.startswith("CHAT:"):
                        # Received chat message from server
                        try:
                            parts = message.split(":", 4)  # CHAT:client_id:username:timestamp:message
                            if len(parts) >= 5:
                                sender_id = int(parts[1])
                                sender_username = parts[2]
                                timestamp = parts[3]
                                chat_message = parts[4]
                                
                                # Display in chat window (must be done in main thread)
                                self.root.after(0, lambda: self.display_chat_message(
                                    sender_username, timestamp, chat_message
                                ))
                        except Exception as e:
                            print(f"[{self.get_timestamp()}] Error handling chat message: {e}")
                    
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
    
    def create_gui(self):
        """Create the GUI"""
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry("1400x800")  # Wider to accommodate screen sharing
        self.root.minsize(1200, 600)  # Prevent shrinking too small
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Initialize UI variables now that root exists
        self.show_self_video = tk.BooleanVar(value=True)
        self.microphone_on = tk.BooleanVar(value=True)
        self.speaker_on = tk.BooleanVar(value=True)
        self.layout_var = tk.StringVar(value="auto")
        
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
        
        # Controls frame (center)
        controls_frame = ttk.Frame(top_frame)
        controls_frame.pack(side=tk.LEFT, padx=20, expand=True)
        
        # Self video toggle
        self_video_check = ttk.Checkbutton(
            controls_frame, 
            text="📹 Camera",
            variable=self.show_self_video,
            command=self.toggle_self_video
        )
        self_video_check.pack(side=tk.LEFT, padx=5)
        
        # Microphone toggle
        mic_check = ttk.Checkbutton(
            controls_frame,
            text="🎤 Microphone",
            variable=self.microphone_on,
            command=self.toggle_microphone
        )
        mic_check.pack(side=tk.LEFT, padx=5)
        
        # Speaker toggle
        speaker_check = ttk.Checkbutton(
            controls_frame,
            text="🔊 Speaker",
            variable=self.speaker_on,
            command=self.toggle_speaker
        )
        speaker_check.pack(side=tk.LEFT, padx=5)
        
        # Screen sharing button
        self.share_screen_btn = ttk.Button(
            controls_frame,
            text="🖥️ Share Screen",
            command=self.toggle_screen_sharing
        )
        self.share_screen_btn.pack(side=tk.LEFT, padx=5)
        
        # Layout selector
        ttk.Label(controls_frame, text="Layout:").pack(side=tk.LEFT, padx=(15, 5))
        layout_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.layout_var,
            values=["auto", "1x1", "2x2", "3x3", "4x4"],
            state="readonly",
            width=8
        )
        layout_combo.pack(side=tk.LEFT, padx=5)
        layout_combo.bind("<<ComboboxSelected>>", self.change_layout)
        
        # Audio device selectors
        ttk.Label(controls_frame, text="Mic:").pack(side=tk.LEFT, padx=(15, 5))
        self.input_device_combo = ttk.Combobox(
            controls_frame,
            state="readonly",
            width=20
        )
        self.input_device_combo.pack(side=tk.LEFT, padx=5)
        self.input_device_combo.bind("<<ComboboxSelected>>", self.on_input_device_changed)
        
        ttk.Label(controls_frame, text="Speaker:").pack(side=tk.LEFT, padx=(10, 5))
        self.output_device_combo = ttk.Combobox(
            controls_frame,
            state="readonly",
            width=20
        )
        self.output_device_combo.pack(side=tk.LEFT, padx=5)
        self.output_device_combo.bind("<<ComboboxSelected>>", self.on_output_device_changed)
        
        # Refresh button for audio devices
        refresh_btn = ttk.Button(
            controls_frame,
            text="🔄",
            width=3,
            command=self.refresh_audio_devices
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        self.user_count_label = ttk.Label(top_frame, text="Users: 0", font=("Arial", 10))
        self.user_count_label.pack(side=tk.RIGHT, padx=5)
        
        # Main content area - split between video grid, screen share, and chat
        self.content_frame = ttk.Frame(main_frame)
        self.content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.content_frame.columnconfigure(0, weight=3)  # Video gets more space
        self.content_frame.columnconfigure(1, weight=2)  # Screen share gets space (always allocated)
        self.content_frame.columnconfigure(2, weight=1)  # Chat panel
        self.content_frame.rowconfigure(0, weight=1)
        
        # Video grid frame (left side)
        self.video_frame = ttk.Frame(self.content_frame, relief=tk.SUNKEN, borderwidth=2)
        self.video_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Screen share frame (right side - always visible to prevent resize)
        self.screen_frame = ttk.Frame(self.content_frame, relief=tk.SUNKEN, borderwidth=2)
        self.screen_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Screen share name label
        self.screen_name_label = ttk.Label(self.screen_frame, text="", 
                                           font=("Arial", 12, "bold"), anchor="center")
        self.screen_name_label.pack(side=tk.TOP, pady=5)
        
        # Screen share display label
        self.screen_label = ttk.Label(self.screen_frame, text="No screen being shared", 
                                     font=("Arial", 14), anchor="center")
        self.screen_label.pack(expand=True, fill=tk.BOTH)
        
        # Chat panel (right side)
        chat_container = ttk.Frame(self.content_frame, relief=tk.SUNKEN, borderwidth=2)
        chat_container.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        # Chat header
        chat_header = ttk.Label(chat_container, text="💬 Chat", 
                               font=("Arial", 12, "bold"), anchor="center")
        chat_header.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        # Chat display area with scrollbar
        chat_display_frame = ttk.Frame(chat_container)
        chat_display_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        chat_scrollbar = ttk.Scrollbar(chat_display_frame)
        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.chat_display = tk.Text(
            chat_display_frame,
            wrap=tk.WORD,
            yscrollcommand=chat_scrollbar.set,
            state=tk.DISABLED,
            font=("Arial", 10),
            bg="#f5f5f5"
        )
        self.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chat_scrollbar.config(command=self.chat_display.yview)
        
        # Configure chat text tags for styling
        self.chat_display.tag_config("timestamp", foreground="#888888", font=("Arial", 8))
        self.chat_display.tag_config("username", foreground="#0066cc", font=("Arial", 10, "bold"))
        self.chat_display.tag_config("message", foreground="#000000", font=("Arial", 10))
        self.chat_display.tag_config("system", foreground="#666666", font=("Arial", 9, "italic"))
        
        # Chat input area
        chat_input_frame = ttk.Frame(chat_container)
        chat_input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        self.chat_input = ttk.Entry(chat_input_frame, font=("Arial", 10))
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_input.bind('<Return>', lambda e: self.send_chat_message())
        
        send_btn = ttk.Button(chat_input_frame, text="Send", command=self.send_chat_message, width=8)
        send_btn.pack(side=tk.RIGHT)
        
        # Create initial video grid (will be dynamic)
        self.create_video_grid()
        
        # Initialize audio device lists
        self.refresh_audio_devices()
        
        # Start GUI update loop
        self.update_gui()
        
        return self.root
    
    def toggle_self_video(self):
        """Toggle video capture on/off"""
        if self.show_self_video.get():
            # Turn video ON - start capturing and transmitting
            self.start_video_capture()
        else:
            # Turn video OFF - stop capturing and transmitting
            self.stop_video_capture()
    
    def toggle_microphone(self):
        """Toggle microphone on/off"""
        if self.microphone_on.get():
            # Turn microphone ON
            self.start_audio_capture()
        else:
            # Turn microphone OFF
            self.stop_audio_capture()
    
    def toggle_speaker(self):
        """Toggle speaker on/off"""
        if self.speaker_on.get():
            # Turn speaker ON
            self.start_audio_playback()
        else:
            # Turn speaker OFF
            self.stop_audio_playback()
    
    def send_chat_message(self):
        """Send a chat message to the server"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to the server first.")
            return
        
        message = self.chat_input.get().strip()
        if not message:
            return
        
        try:
            # Send to server
            chat_data = f"CHAT:{message}"
            self.tcp_socket.send(chat_data.encode('utf-8'))
            
            # Clear input field
            self.chat_input.delete(0, tk.END)
            
        except Exception as e:
            print(f"[{self.get_timestamp()}] Error sending chat message: {e}")
            messagebox.showerror("Chat Error", f"Failed to send message: {e}")
    
    def display_chat_message(self, username, timestamp, message, is_system=False):
        """Display a chat message in the chat window"""
        self.chat_display.config(state=tk.NORMAL)
        
        if is_system:
            # System message (e.g., user joined/left)
            self.chat_display.insert(tk.END, f"{message}\n", "system")
        else:
            # Regular chat message
            self.chat_display.insert(tk.END, f"{timestamp} ", "timestamp")
            self.chat_display.insert(tk.END, f"{username}: ", "username")
            self.chat_display.insert(tk.END, f"{message}\n", "message")
        
        # Auto-scroll to bottom
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def toggle_screen_sharing(self):
        """Toggle screen sharing on/off"""
        if not self.is_presenting:
            # Start screen sharing in background thread to avoid blocking GUI
            def start_in_background():
                try:
                    if self.start_screen_sharing():
                        # Update button on success (must be done in main thread)
                        self.root.after(0, lambda: self.share_screen_btn.config(text="🛑 Stop Sharing"))
                    else:
                        # Revert on failure
                        self.root.after(0, lambda: messagebox.showwarning("Screen Sharing", 
                                                                          "Could not start screen sharing. Another user may be presenting."))
                except Exception as e:
                    print(f"[{self.get_timestamp()}] Error in start_in_background: {e}")
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to start screen sharing: {e}"))
            
            threading.Thread(target=start_in_background, daemon=True).start()
            self.is_presenting = True  # Optimistically set
        else:
            # Stop screen sharing (also in background to avoid blocking)
            def stop_in_background():
                try:
                    self.stop_screen_sharing()
                    self.root.after(0, lambda: self.share_screen_btn.config(text="🖥️ Share Screen"))
                except Exception as e:
                    print(f"[{self.get_timestamp()}] Error in stop_in_background: {e}")
            
            threading.Thread(target=stop_in_background, daemon=True).start()
            self.is_presenting = False
            self.share_screen_btn.config(text="🖥️ Share Screen")  # Update immediately
    
    def change_layout(self, event=None):
        """Change video grid layout"""
        layout = self.layout_var.get()
        self.current_layout = layout
        self.create_video_grid()
    
    def calculate_grid_size(self, num_videos):
        """Calculate optimal grid size based on number of videos and layout setting"""
        if self.current_layout == "auto":
            # Automatic layout based on number of videos
            if num_videos <= 1:
                return 1, 1
            elif num_videos <= 4:
                return 2, 2
            elif num_videos <= 9:
                return 3, 3
            else:
                return 4, 4
        else:
            # Fixed layout
            size = int(self.current_layout[0])  # Extract number from "1x1", "2x2", etc.
            return size, size
    
    def create_video_grid(self):
        """Create a dynamic grid of video display labels"""
        # Clear existing grid
        for widget in self.video_frame.winfo_children():
            widget.destroy()
        
        self.video_labels = {}
        
        # Get maximum grid size based on current layout
        if self.current_layout == "auto":
            max_size = 4  # Default max for auto
        else:
            max_size = int(self.current_layout[0])
        
        # Configure grid weights
        for i in range(max_size):
            self.video_frame.columnconfigure(i, weight=1)
            self.video_frame.rowconfigure(i, weight=1)
        
        # Create grid positions
        idx = 0
        for row in range(max_size):
            for col in range(max_size):
                # Container frame for each video
                container = ttk.Frame(self.video_frame, relief=tk.RAISED, borderwidth=1)
                container.grid(row=row, column=col, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
                
                # Configure container to expand uniformly
                container.columnconfigure(0, weight=1)
                container.rowconfigure(1, weight=1)
                
                # Username label
                username_label = ttk.Label(container, text="", font=("Arial", 9, "bold"), anchor="center")
                username_label.grid(row=0, column=0, pady=2, sticky=(tk.W, tk.E))
                
                # Video label - centered and uniform with fixed minimum size
                video_label = tk.Label(container, bg="black", text="No Video", anchor="center")
                video_label.grid(row=1, column=0, padx=2, pady=2, sticky=(tk.W, tk.E, tk.N, tk.S))
                
                # Set minimum size for the video label to ensure uniformity
                video_label.config(width=40, height=20)  # Minimum size in character units
                
                self.video_labels[idx] = {
                    'container': container,
                    'username': username_label,
                    'video': video_label,
                    'client_id': None
                }
                idx += 1
    
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
                # Clean up stale video streams (no frame received in last 2 seconds)
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
                
                client_ids = list(self.video_streams.keys())
            
            # Build display streams from other clients only
            display_streams = {}
            
            # Other clients' video (only active streams)
            with self.streams_lock:
                for client_id, frame in self.video_streams.items():
                    display_streams[client_id] = frame
            
            # Self video (from camera) - only if capturing
            if self.capturing and self.camera is not None:
                ret, frame = self.camera.read()
                if ret:
                    display_streams[self.client_id] = frame
            
            # Calculate optimal grid size
            num_videos = len(display_streams)
            rows, cols = self.calculate_grid_size(num_videos)
            
            # Calculate uniform video size based on grid - all videos same size
            container_width = self.video_frame.winfo_width()
            container_height = self.video_frame.winfo_height()
            
            if container_width > 1 and container_height > 1:
                # Calculate available space per cell
                cell_width = (container_width // cols) - 20  # Account for padding
                cell_height = (container_height // rows) - 50  # Account for padding and username label
                
                # Maintain 4:3 aspect ratio and fit within cell
                aspect_ratio = 4.0 / 3.0
                
                # Try fitting by width first
                video_width = max(160, cell_width)
                video_height = int(video_width / aspect_ratio)
                
                # If height exceeds cell, fit by height instead
                if video_height > cell_height:
                    video_height = max(120, cell_height)
                    video_width = int(video_height * aspect_ratio)
            else:
                video_width = 320
                video_height = 240
            
            # Update video grid
            display_index = 0
            for idx, label_info in self.video_labels.items():
                if display_index < len(display_streams):
                    client_id = list(display_streams.keys())[display_index]
                    frame = display_streams[client_id]
                    
                    # Get username
                    with self.users_lock:
                        username = self.users.get(client_id, f"User {client_id}")
                    
                    if client_id == self.client_id:
                        username = f"{username} (You)"
                    
                    # Update username label
                    label_info['username'].config(text=username)
                    
                    # Convert and display frame - use SAME size for ALL videos
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_resized = cv2.resize(frame_rgb, (video_width, video_height))
                    
                    img = Image.fromarray(frame_resized)
                    imgtk = ImageTk.PhotoImage(image=img)
                    
                    # Set image and ensure label maintains fixed size
                    label_info['video'].config(image=imgtk, text="", width=video_width, height=video_height)
                    label_info['video'].image = imgtk
                    label_info['client_id'] = client_id
                    
                    # Make container visible
                    label_info['container'].grid()
                    display_index += 1
                else:
                    # Hide unused slots in auto mode, show "No Video" in manual mode
                    if self.current_layout == "auto":
                        # Hide the container completely in auto mode
                        label_info['container'].grid_remove()
                    else:
                        # Show "No Video" placeholder in manual mode with same size
                        label_info['username'].config(text="")
                        
                        # Create a black placeholder image with same dimensions as videos
                        placeholder = Image.new('RGB', (video_width, video_height), color='black')
                        placeholder_tk = ImageTk.PhotoImage(image=placeholder)
                        
                        label_info['video'].config(image=placeholder_tk, text="No Video", compound="center", 
                                                   fg="white", width=video_width, height=video_height)
                        label_info['video'].image = placeholder_tk
                        label_info['container'].grid()
                    
                    label_info['client_id'] = None
            
            # Update shared screen display
            with self.screen_lock:
                screen_frame_copy = self.shared_screen_frame
            
            if screen_frame_copy is not None and self.current_presenter_id is not None:
                # Decode and display screen frame
                try:
                    nparr = np.frombuffer(screen_frame_copy, np.uint8)
                    screen_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if screen_img is not None:
                        # Resize to fit screen area dynamically based on available space
                        screen_frame_width = self.screen_frame.winfo_width()
                        if screen_frame_width > 100:  # Only resize if frame has size
                            screen_width = max(300, screen_frame_width - 20)  # With padding
                        else:
                            screen_width = 500  # Default size
                        
                        aspect = screen_img.shape[1] / screen_img.shape[0]
                        screen_height = int(screen_width / aspect)
                        
                        screen_img = cv2.resize(screen_img, (screen_width, screen_height))
                        
                        # Convert and display
                        screen_rgb = cv2.cvtColor(screen_img, cv2.COLOR_BGR2RGB)
                        screen_pil = Image.fromarray(screen_rgb)
                        screen_tk = ImageTk.PhotoImage(image=screen_pil)
                        
                        # Get presenter name
                        with self.users_lock:
                            presenter_name = self.users.get(self.current_presenter_id, "Unknown")
                        
                        # Update label - keep reference to prevent garbage collection
                        self.screen_label.config(image=screen_tk, text="")
                        self.screen_label.image = screen_tk
                        self.screen_name_label.config(text=f"📺 {presenter_name}'s Screen")
                except Exception as e:
                    print(f"[{self.get_timestamp()}] Error displaying screen: {e}")
            else:
                # Show "No screen sharing" message
                self.screen_label.config(image="", text="No screen being shared")
                self.screen_label.image = None
                self.screen_name_label.config(text="")
            
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
            
            # Start audio capture and playback
            client.start_audio_capture()
            client.start_audio_playback()
            
            # Run GUI
            root.mainloop()
        else:
            messagebox.showerror("Connection Error", "Failed to connect to server")
            root.destroy()
    else:
        root.destroy()


if __name__ == "__main__":
    main()
