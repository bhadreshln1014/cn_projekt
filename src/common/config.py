"""
Configuration file for the LAN Communication Application
"""

# Server Configuration
SERVER_HOST = '0.0.0.0'  # Listen on all network interfaces
SERVER_TCP_PORT = 5000    # For control messages (user connection, session management)
SERVER_UDP_PORT = 5001    # For video streaming

# Video Configuration
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
VIDEO_FPS = 30
VIDEO_QUALITY = 60  # JPEG compression quality (0-100)

# Network Configuration
MAX_PACKET_SIZE = 65507  # Max UDP packet size
CHUNK_SIZE = 60000       # Size of each video chunk

# Session Configuration
MAX_USERS = 10
HEARTBEAT_INTERVAL = 5   # seconds

# GUI Configuration
WINDOW_TITLE = "LAN Communication App"
GRID_COLS = 3  # Number of columns in video grid
