# RTSP Camera Streaming Application

A Python-based web application for streaming video from RTSP cameras (specifically optimized for Amcrest cameras) with real-time web viewing and video recording capabilities.

## Features

✨ **Real-time Video Streaming**
- Live RTSP stream viewing in web browser
- WebSocket-based real-time frame transmission
- Automatic reconnection on connection loss

🎥 **Video Recording**
- Record video streams to disk
- Timestamped MP4 files
- Start/stop recording on demand

🌐 **Modern Web Interface**
- Responsive design that works on desktop and mobile
- Real-time status monitoring
- Easy-to-use controls
- Beautiful modern UI with gradients and animations

🔧 **Configurable Settings**
- Easy configuration through `config.py`
- Support for different camera settings
- Adjustable video quality and streaming parameters

## Screenshots

### Web Interface
The application provides a clean, modern web interface with:
- Live video feed display
- Stream and recording controls
- Real-time status indicators
- Responsive design for all devices

## Requirements

- Python 3.7+
- Amcrest IP camera (or any RTSP-compatible camera)
- Network connection to camera

## Quick Start

### Option 1: Automated Setup (Recommended)

1. **Clone the project**
   ```bash
   git clone <repository-url>
   cd rtsp-camera-streaming
   ```

2. **Run the automated setup**
   ```bash
   python3 setup_env.py
   ```
   This will:
   - Create a virtual environment
   - Install all dependencies
   - Set up development tools (optional)

3. **Activate the virtual environment**
   ```bash
   # On macOS/Linux:
   source activate.sh
   # or
   source venv/bin/activate

   # On Windows:
   activate.bat
   # or
   venv\Scripts\activate.bat
   ```

4. **Configure your camera** (edit `config.py`)
   ```python
   RTSP_CONFIG = {
       'username': 'admin',
       'password': 'your_camera_password',
       'ip_address': '192.168.1.XXX',  # Your camera IP
       'port': 554,
       'channel': 1,
       'subtype': 0,
   }
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

### Option 2: Manual Installation

1. **Clone the project**
   ```bash
   git clone <repository-url>
   cd rtsp-camera-streaming
   ```

2. **Create virtual environment (optional but recommended)**
   ```bash
   python3 -m venv venv

   # Activate it:
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate.bat
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your camera** (edit `config.py`)
   ```python
   RTSP_CONFIG = {
       'username': 'admin',
       'password': 'your_camera_password',
       'ip_address': '192.168.1.XXX',  # Your camera IP
       'port': 554,
       'channel': 1,
       'subtype': 0,
   }
   ```

5. **Run the application**
   ```bash
   python app.py
   # or
   python run.py
   ```

6. **Access the web interface**
   Open your browser and go to: `http://localhost:5000`

## Virtual Environment Benefits

Using a virtual environment provides several advantages:
- ✅ **Isolated dependencies** - No conflicts with system packages
- ✅ **Easy cleanup** - Remove `venv/` folder to uninstall everything
- ✅ **Reproducible setup** - Same environment across different machines
- ✅ **Version control** - Pin exact dependency versions

### Virtual Environment Commands

```bash
# Create virtual environment
python3 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate.bat

# Deactivate (all platforms)
deactivate

# Install dependencies
pip install -r requirements.txt

# Install development tools
pip install mypy==1.7.1
```

## Configuration

### Camera Settings (`config.py`)

```python
RTSP_CONFIG = {
    'username': 'admin',           # Default Amcrest username
    'password': 'password',        # Change this to your camera password
    'ip_address': '192.168.1.100', # Change this to your camera's IP address
    'port': 554,                   # Default RTSP port
    'channel': 1,                  # Camera channel (usually 1)
    'subtype': 0,                  # 0 = main stream, 1 = sub stream
}
```

### Application Settings

```python
APP_CONFIG = {
    'host': '0.0.0.0',      # Server host (0.0.0.0 for all interfaces)
    'port': 5000,           # Server port
    'debug': True,          # Debug mode
    'secret_key': 'change_this_secret_key_in_production',
}
```

### Recording Settings

```python
RECORDING_CONFIG = {
    'output_directory': 'recordings',  # Where to save recorded videos
    'video_codec': 'mp4v',            # Video codec for recording
    'default_fps': 30,                # Default FPS if not detected
    'jpeg_quality': 80,               # JPEG quality for web streaming (1-100)
}
```

## Usage

### Starting a Stream

1. Click the **"Start Stream"** button in the web interface
2. The application will connect to your RTSP camera
3. Live video will appear in the web interface
4. Status indicators will show connection status

### Recording Video

1. Ensure the stream is active
2. Click **"Start Recording"** to begin recording
3. Video will be saved to the `recordings/` directory
4. Click **"Stop Recording"** when finished
5. Files are saved with timestamps: `recording_YYYYMMDD_HHMMSS.mp4`

### Monitoring Status

The web interface provides real-time status information:
- **Connection**: Shows if connected to camera
- **Streaming**: Shows if video stream is active
- **Recording**: Shows if currently recording

## Development

### Type Checking

The project includes comprehensive type annotations. To run type checking:

```bash
# Install mypy (if not already installed)
pip install mypy==1.7.1

# Run type checking
python check_types.py
# or
mypy app.py config.py run.py
```

### Project Scripts

- `setup_env.py` - Automated virtual environment setup
- `run.py` - Enhanced application launcher with environment detection
- `check_types.py` - Type checking utility
- `activate.sh` / `activate.bat` - Quick virtual environment activation

## Troubleshooting

### Common Issues

**Cannot connect to camera:**
- Verify camera IP address and credentials in `config.py`
- Ensure camera is on the same network
- Check that RTSP is enabled on your camera
- Try accessing the camera's web interface to verify it's working

**Poor video quality:**
- Adjust `jpeg_quality` in `config.py` (higher = better quality, more bandwidth)
- Check your network connection speed
- Consider using the sub-stream (`subtype = 1`) for lower bandwidth

**Recording issues:**
- Ensure the `recordings/` directory is writable
- Check available disk space
- Verify video codec support on your system

**Web interface not loading:**
- Check that Flask server is running on the correct port
- Verify firewall settings allow access to port 5000
- Try accessing via `http://localhost:5000` instead of the server IP

**Virtual environment issues:**
- Make sure you've activated the virtual environment
- Try recreating it: `rm -rf venv && python3 setup_env.py`
- Check Python version: `python --version` (should be 3.7+)

### Amcrest Camera Setup

1. **Enable RTSP on your camera:**
   - Access camera web interface
   - Go to Setup → Network → Port
   - Enable RTMP Port (usually 554)

2. **Find your camera's IP address:**
   - Use Amcrest IP Config Tool
   - Check your router's device list
   - Use network scanning tools

3. **Test RTSP URL:**
   You can test your RTSP URL using VLC or similar media player:
   ```
   rtmp://username:password@camera_ip:554/cam/realmonitor?channel=1&subtype=0
   ```

## File Structure

```
rtsp-camera-streaming/
├── .git/                   # Git repository
├── .gitignore             # Git ignore rules
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── setup_env.py           # Virtual environment setup
├── run.py                 # Enhanced launcher
├── check_types.py         # Type checking utility
├── mypy.ini               # Type checking configuration
├── activate.sh            # Virtual environment activation (Unix)
├── activate.bat           # Virtual environment activation (Windows)
├── README.md              # This file
├── templates/
│   └── index.html         # Web interface template
├── venv/                  # Virtual environment (created by setup)
└── recordings/            # Recorded videos (created automatically)
```

## Technical Details

### Technology Stack
- **Backend**: Python Flask + Flask-SocketIO
- **Frontend**: HTML5, CSS3, JavaScript, WebSockets
- **Video Processing**: OpenCV (cv2)
- **Real-time Communication**: Socket.IO
- **Type Safety**: MyPy for static type checking

### Architecture
1. **RTSP Stream Capture**: OpenCV captures frames from RTSP stream
2. **Frame Processing**: Frames are encoded as JPEG for web transmission
3. **WebSocket Streaming**: Real-time frame transmission to web clients
4. **Video Recording**: Simultaneous recording to MP4 files
5. **Web Interface**: Modern responsive UI for control and monitoring

## Security Considerations

- Change default passwords and secret keys in production
- Consider using HTTPS for web interface
- Restrict network access to camera and application
- Regularly update dependencies

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this application.

## License

This project is open source. Feel free to use and modify as needed.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify your camera and network configuration
3. Check application logs for error messages
4. Ensure all dependencies are properly installed
5. Make sure virtual environment is activated