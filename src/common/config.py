"""
Configuration file for the LAN Communication Application
"""

# Server Configuration
SERVER_HOST = '0.0.0.0'  # Listen on all network interfaces
SERVER_TCP_PORT = 5000    # For control messages (user connection, session management)
SERVER_UDP_PORT = 5001    # For video streaming
SERVER_AUDIO_PORT = 5002  # For audio streaming
SERVER_SCREEN_PORT = 5003 # For screen sharing control (TCP)
SERVER_SCREEN_UDP_PORT = 5004 # For screen frame data (UDP)
SERVER_CHAT_PORT = 5000   # Chat uses same TCP connection as control messages
SERVER_FILE_PORT = 5005   # For file transfer (TCP)

# Message Types
MSG_CHAT = "CHAT_MESSAGE"
MSG_CHAT_HISTORY = "CHAT_HISTORY"
MSG_PRIVATE_CHAT = "PRIVATE_CHAT"
MSG_FILE_OFFER = "FILE_OFFER"
MSG_FILE_REQUEST = "FILE_REQUEST"
MSG_FILE_DATA = "FILE_DATA"

# File Transfer Configuration
FILE_CHUNK_SIZE = 8192    # Size of each file chunk (8KB)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB max file size

# Video Configuration
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
VIDEO_FPS = 30
VIDEO_QUALITY = 60  # JPEG compression quality (0-100)

# Audio Configuration
AUDIO_RATE = 44100        # Sample rate (Hz)
AUDIO_CHUNK = 1024        # Samples per chunk (smaller chunks = lower latency ~23ms)
AUDIO_CHANNELS = 1        # Mono audio
AUDIO_FORMAT = 8          # pyaudio.paInt16 (16-bit audio)
AUDIO_FORMAT_BYTES = 2    # Bytes per sample
AUDIO_BUFFER_SIZE = 10    # Number of chunks to buffer for jitter compensation

# Screen Sharing Configuration
SCREEN_WIDTH = 960        # Screen sharing resolution width (reduced for UDP packet size)
SCREEN_HEIGHT = 540       # Screen sharing resolution height (16:9 aspect ratio)
SCREEN_FPS = 10           # Screen sharing frame rate (lower than video for bandwidth)
SCREEN_QUALITY = 50       # JPEG compression quality for screen sharing (reduced to fit UDP)
MAX_SCREEN_PACKET_SIZE = 65000 # Max UDP packet size for screen frames

# Network Configuration
MAX_PACKET_SIZE = 65507  # Max UDP packet size
CHUNK_SIZE = 60000       # Size of each video chunk

# Session Configuration
MAX_USERS = 10
HEARTBEAT_INTERVAL = 5   # seconds

# GUI Configuration
WINDOW_TITLE = "LAN Communication App"
GRID_COLS = 3  # Number of columns in video grid
