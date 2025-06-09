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

## Installation

1. **Clone or download this project**
   ```bash
   git clone <repository-url>
   cd rtsp-camera-streaming
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your camera settings**
   Edit `config.py` and update the RTSP configuration:
   ```python
   RTSP_CONFIG = {
       'username': 'admin',           # Your camera username
       'password': 'your_password',   # Your camera password
       'ip_address': '192.168.1.100', # Your camera IP address
       'port': 554,                   # RTSP port (usually 554)
       'channel': 1,                  # Camera channel
       'subtype': 0,                  # 0 = main stream, 1 = sub stream
   }
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the web interface**
   Open your browser and go to: `http://localhost:5000`

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
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── templates/
│   └── index.html     # Web interface template
└── recordings/        # Recorded videos (created automatically)
```

## Technical Details

### Technology Stack
- **Backend**: Python Flask + Flask-SocketIO
- **Frontend**: HTML5, CSS3, JavaScript, WebSockets
- **Video Processing**: OpenCV (cv2)
- **Real-time Communication**: Socket.IO

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