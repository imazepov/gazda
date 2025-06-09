#!/usr/bin/env python3
"""
RTSP Camera Streaming Application Launcher
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

def check_dependencies() -> bool:
    """Check if all required dependencies are installed"""
    try:
        import cv2
        import flask
        import flask_socketio
        import numpy
        import PIL
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install dependencies with: pip install -r requirements.txt")
        return False

def check_config() -> bool:
    """Check if configuration has been updated"""
    try:
        from config import RTSP_CONFIG

        # Check if default values are still being used
        if (RTSP_CONFIG['password'] == 'password' or
            RTSP_CONFIG['ip_address'] == '192.168.1.100'):
            print("⚠️  WARNING: You're using default camera configuration!")
            print("   Please update config.py with your camera settings:")
            print(f"   - IP Address: {RTSP_CONFIG['ip_address']}")
            print(f"   - Username: {RTSP_CONFIG['username']}")
            print(f"   - Password: {RTSP_CONFIG['password']}")
            print()

            response: str = input("Continue anyway? (y/N): ").lower().strip()
            if response != 'y':
                return False

        return True
    except ImportError:
        print("❌ Cannot import config.py. Make sure the file exists.")
        return False

def create_directories() -> None:
    """Create necessary directories"""
    directories: list[str] = ['recordings', 'templates']

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Directory '{directory}' ready")

def main() -> None:
    """Main launcher function"""
    print("🎥 RTSP Camera Streaming Application")
    print("=" * 40)

    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        sys.exit(1)

    print(f"✅ Python {sys.version.split()[0]} detected")

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    print("✅ All dependencies installed")

    # Check configuration
    if not check_config():
        sys.exit(1)
    print("✅ Configuration checked")

    # Create directories
    create_directories()

    # Start the application
    print("🚀 Starting RTSP Camera Streaming Server...")
    print("   Press Ctrl+C to stop the server")
    print("=" * 40)

    try:
        # Import and run the main application
        from app import app, socketio
        from config import get_app_config

        config: Dict[str, Any] = get_app_config()
        socketio.run(
            app,
            host=config['host'],
            port=config['port'],
            debug=config['debug']
        )

    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()