# config.py

# Server configuration
SERVER_HOST = '127.0.0.1'  # The server's hostname or IP address
SERVER_PORT = 65432       # The port used by the server
TIMEOUT = 5               # 🆕 Add this line. Timeout in seconds for socket operations.

# Protocol messages
MESSAGE_TYPE_TEXT = 1
MESSAGE_TYPE_IMAGE = 2
MESSAGE_TYPE_DOCUMENT = 3
MESSAGE_TYPE_VIDEO = 4

# Maximum file sizes in bytes
MAX_IMAGE_SIZE = 5 * 1024 * 1024    # 5 MB
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024 # 10 MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024   # 50 MB

# UI constants
WINDOW_TITLE = "Secure Chat"