"""
Configuration settings for RTSP Camera Streaming Application (FFmpeg-based)

For private/sensitive settings, create a config_private.py file (see config_private.py.example)
"""

from typing import Dict, Any

# RTSP Camera Configuration - DEFAULT VALUES
# For actual credentials, create config_private.py (see config_private.py.example)
RTSP_CONFIG: Dict[str, Any] = {
    # Basic connection settings
    'username': 'admin',           # Default Amcrest username
    'password': 'password',        # Change this to your camera password
    'ip_address': '192.168.1.100', # Change this to your camera's IP address
    'port': 554,                   # Default RTSP port
    'channel': 1,                  # Camera channel (usually 1)
    'subtype': 0,                  # 0 = main stream, 1 = sub stream
}

# Application Settings - DEFAULT VALUES
APP_CONFIG: Dict[str, Any] = {
    'host': '0.0.0.0',
    'port': 5000,
    'debug': True,
    'secret_key': 'change_this_secret_key_in_production',
}

# Video Recording Settings (FFmpeg-based)
RECORDING_CONFIG: Dict[str, Any] = {
    'output_directory': 'recordings',
    'video_codec': 'libx264',      # FFmpeg video codec for recording
    'audio_codec': 'aac',          # FFmpeg audio codec for recording
    'preset': 'fast',              # FFmpeg encoding preset (ultrafast, superfast, veryfast, faster, fast, medium, slow)
    'crf': 23,                     # Constant Rate Factor (18-28, lower = better quality, higher = more compression)
    'default_fps': 30,             # Default FPS if not detected from stream
    'jpeg_quality': 80,            # JPEG quality for web streaming (1-100)
    'resolution': None,            # Downscale resolution for recordings (e.g., '1280x720'), None = keep original
    'max_file_size_mb': 10,        # Maximum file size in MB before rotation (default: 10 MB)
}

# Streaming Settings (FFmpeg-based)
STREAMING_CONFIG: Dict[str, Any] = {
    'frame_rate': 5,               # Frames per second for web preview (1-10 recommended)
    'reconnect_attempts': 3,       # Number of reconnection attempts
    'reconnect_delay': 5,          # Delay between reconnection attempts (seconds)
    'buffer_size': 10**8,          # FFmpeg buffer size for video data
    'ffmpeg_timeout': 30,          # FFmpeg connection timeout in seconds
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

# Try to import private configuration and merge with defaults
# This must be done AFTER all config dictionaries are defined
try:
    from config_private import RTSP_CONFIG_PRIVATE, APP_CONFIG_PRIVATE
    RTSP_CONFIG.update(RTSP_CONFIG_PRIVATE)
    APP_CONFIG.update(APP_CONFIG_PRIVATE)

    # Also try to import streaming and recording config overrides
    try:
        from config_private import STREAMING_CONFIG_PRIVATE
        STREAMING_CONFIG.update(STREAMING_CONFIG_PRIVATE)
    except ImportError:
        pass

    try:
        from config_private import RECORDING_CONFIG_PRIVATE
        RECORDING_CONFIG.update(RECORDING_CONFIG_PRIVATE)
    except ImportError:
        pass

    print("✅ Loaded private configuration from config_private.py")
except ImportError:
    print("ℹ️  No config_private.py found - using default configuration")
    print("   To use private settings, copy config_private.py.example to config_private.py")