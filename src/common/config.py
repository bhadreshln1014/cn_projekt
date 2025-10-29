"""
Configuration file for the LAN Communication Application
"""

# Server Configuration
SERVER_HOST = '0.0.0.0'  # Listen on all network interfaces
SERVER_TCP_PORT = 5000    # For control messages (user connection, session management)
SERVER_UDP_PORT = 5001    # For video streaming
SERVER_AUDIO_PORT = 5002  # For audio streaming

# Video Configuration
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
VIDEO_FPS = 30
VIDEO_QUALITY = 60  # JPEG compression quality (0-100)

# Audio Configuration
AUDIO_RATE = 44100        # Sample rate (Hz)
AUDIO_CHUNK = 2048        # Samples per chunk (increased for better sync and less choppy audio)
AUDIO_CHANNELS = 1        # Mono audio
AUDIO_FORMAT = 8          # pyaudio.paInt16 (16-bit audio)
AUDIO_FORMAT_BYTES = 2    # Bytes per sample

# Network Configuration
MAX_PACKET_SIZE = 65507  # Max UDP packet size
CHUNK_SIZE = 60000       # Size of each video chunk

# Session Configuration
MAX_USERS = 10
HEARTBEAT_INTERVAL = 5   # seconds

# GUI Configuration
WINDOW_TITLE = "LAN Communication App"
GRID_COLS = 3  # Number of columns in video grid
