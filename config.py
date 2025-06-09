"""
Configuration settings for RTSP Camera Streaming Application
"""

from typing import Dict, Any

# RTSP Camera Configuration
# Update these settings to match your Amcrest camera
RTSP_CONFIG: Dict[str, Any] = {
    # Basic connection settings
    'username': 'admin',           # Default Amcrest username
    'password': 'mazepovs1523',        # Change this to your camera password
    'ip_address': '192.168.86.87', # Change this to your camera's IP address
    'port': 554,                   # Default RTSP port
    'channel': 1,                  # Camera channel (usually 1)
    'subtype': 0,                  # 0 = main stream, 1 = sub stream
}

# Application Settings
APP_CONFIG: Dict[str, Any] = {
    'host': '0.0.0.0',
    'port': 5000,
    'debug': True,
    'secret_key': 'change_this_secret_key_in_production',
}

# Video Recording Settings
RECORDING_CONFIG: Dict[str, Any] = {
    'output_directory': 'recordings',
    'video_codec': 'mp4v',         # Video codec for recording
    'default_fps': 30,             # Default FPS if not detected from stream
    'jpeg_quality': 80,            # JPEG compression quality for web streaming (1-100)
}

# Streaming Settings
STREAMING_CONFIG: Dict[str, Any] = {
    'buffer_size': 1,              # OpenCV buffer size (lower = less latency)
    'frame_rate': 30,              # Target frame rate for web streaming
    'reconnect_attempts': 3,       # Number of reconnection attempts
    'reconnect_delay': 5,          # Delay between reconnection attempts (seconds)
}

def get_rtsp_url() -> str:
    """Generate RTSP URL from configuration"""
    return (f"rtsp://{RTSP_CONFIG['username']}:{RTSP_CONFIG['password']}@"
            f"{RTSP_CONFIG['ip_address']}:{RTSP_CONFIG['port']}/cam/realmonitor"
            f"?channel={RTSP_CONFIG['channel']}&subtype={RTSP_CONFIG['subtype']}")

def get_app_config() -> Dict[str, Any]:
    """Get Flask application configuration"""
    return APP_CONFIG.copy()

def get_recording_config() -> Dict[str, Any]:
    """Get recording configuration"""
    return RECORDING_CONFIG.copy()

def get_streaming_config() -> Dict[str, Any]:
    """Get streaming configuration"""
    return STREAMING_CONFIG.copy()