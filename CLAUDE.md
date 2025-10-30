# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RTSP Camera Streaming Application - A Python Flask web application for streaming video from RTSP cameras (optimized for Amcrest cameras) with real-time web viewing and video recording capabilities using FFmpeg.

## Development Commands

### Running the Application

```bash
# Using the enhanced launcher (recommended)
python run.py

# Or directly
python app.py
```

The application will start on `http://localhost:5005` (configured in `config.py`).

### Virtual Environment

```bash
# Setup (creates venv and installs dependencies)
python setup_env.py

# Activate (macOS/Linux)
source venv/bin/activate
# or
source activate.sh

# Activate (Windows)
activate.bat
# or
venv\Scripts\activate.bat
```

### Type Checking

```bash
# Run type checker (requires mypy)
python check_types.py

# Or manually
mypy app.py config.py run.py
```

The codebase has comprehensive type annotations throughout - all functions, methods, and variables are typed.

### Installing Dependencies

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install development dependencies
pip install mypy>=1.7.0,<2.0.0
```

## Architecture

### Core Components

**RTSPStreamer Class** (`app.py`):
- Manages RTSP stream connection via FFmpeg subprocess
- Handles frame extraction using temporary file system
- Provides simultaneous streaming and recording capabilities
- Thread-safe frame buffer with locking mechanism
- Automatic cleanup of temporary frame files

**Video Processing Pipeline**:
1. FFmpeg process connects to RTSP stream (TCP transport for reliability)
2. Frames extracted to temporary directory as JPEG files at 1 FPS
3. Background thread (`_read_frames`) monitors temp directory and reads new frames
4. Frame buffer updated with latest frame data
5. WebSocket emission thread sends frames to web clients
6. Separate recording process captures full stream to MP4

**Key Threading Model**:
- `frame_thread`: Monitors temporary directory for new frames
- `stderr_thread`: Monitors FFmpeg stderr output for errors
- `emit_thread`: Sends frames to web clients via WebSocket
- Recording runs in separate FFmpeg subprocess

### Configuration System

All configuration is centralized in `config.py` with typed dictionaries:

- `RTSP_CONFIG`: Camera connection settings (IP, credentials, port, channel)
- `APP_CONFIG`: Flask server settings (host, port, debug, secret_key)
- `RECORDING_CONFIG`: FFmpeg recording parameters (codec, preset, CRF, quality)
- `STREAMING_CONFIG`: Frame rate, reconnection settings, buffer size

Helper functions (`get_rtsp_url()`, `get_app_config()`, etc.) provide defensive copies to prevent mutation.

### FFmpeg Integration

**Why FFmpeg over OpenCV**:
- More robust RTSP connection handling (TCP transport)
- Hardware acceleration support
- Better codec compatibility
- Lower latency and CPU usage
- Industry-standard reliability

**Two FFmpeg Processes**:
1. **Streaming process**: Extracts frames to temp directory for web preview
2. **Recording process**: Direct stream-to-file recording with minimal overhead

### Flask Routes

- `GET /`: Main web interface
- `GET /video_feed`: HTTP multipart stream (fallback)
- `POST /start_stream`: Initialize RTSP connection
- `POST /stop_stream`: Disconnect and cleanup
- `POST /start_recording`: Begin MP4 recording
- `POST /stop_recording`: Stop recording
- `GET /status`: Current state (streaming/recording/connected)

### WebSocket Events

- `connect`: Client connection established
- `disconnect`: Client disconnected
- `video_frame`: Server emits base64-encoded JPEG frames

## Important Implementation Details

### Frame Extraction Strategy

The application uses a **file-based frame extraction** approach rather than piping frames directly from FFmpeg stdout:
- FFmpeg writes frames to temp directory as `frame_XXXX.jpg`
- Background thread uses `glob.glob()` to find new frames
- Latest frame is read, older frames are deleted (keeps only 5 most recent)
- This approach is more reliable than reading from stdout pipe

### Resource Cleanup

When stopping the stream:
1. Set `streaming` flag to False (stops threads)
2. Terminate FFmpeg process (5 second timeout, then SIGKILL)
3. Remove temporary directory with `shutil.rmtree()`
4. Stop recording if active

### Camera Connection

RTSP URL format for Amcrest cameras:
```
rtsp://username:password@ip_address:port/cam/realmonitor?channel=X&subtype=Y
```
- `subtype=0`: Main stream (high quality)
- `subtype=1`: Sub stream (lower bandwidth)

## Common Development Tasks

### Adding New Camera Support

1. Update `config.py` RTSP URL format in `get_rtsp_url()`
2. Adjust FFmpeg parameters in `start_ffmpeg_process()` if needed
3. Test connection with `ffmpeg.probe()` in `get_stream_info()`

### Adjusting Video Quality

**Streaming quality**: Modify `RECORDING_CONFIG['jpeg_quality']` (1-100)
**Recording quality**: Modify `RECORDING_CONFIG['crf']` (18-28, lower = better)
**Frame rate**: Modify `STREAMING_CONFIG['frame_rate']` (1-10 recommended)

### Debugging FFmpeg Issues

The `_monitor_stderr()` thread logs FFmpeg output with "🔍 FFmpeg:" prefix. Check console for:
- Connection errors
- Codec issues
- Stream information
- Frame processing status

### Running Without Virtual Environment

The `run.py` launcher detects virtual environment status and provides helpful instructions but will run without it if dependencies are installed globally.

## File Structure

```
.
├── app.py              # Main Flask application with RTSPStreamer class
├── config.py           # All configuration settings
├── run.py              # Enhanced launcher with checks
├── setup_env.py        # Virtual environment setup automation
├── check_types.py      # Type checking utility
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Web interface
└── recordings/         # MP4 recordings (auto-created)
```

## Dependencies

**Runtime**:
- Flask + Flask-SocketIO: Web server and WebSocket
- ffmpeg-python: FFmpeg wrapper for stream probing
- numpy, Pillow: Image processing
- opencv-python: Currently imported but functionality replaced by FFmpeg

**System**:
- FFmpeg (required external dependency, not installed via pip)

**Development**:
- mypy: Static type checking

## Python Version Compatibility

- Minimum: Python 3.7
- Tested: Python 3.11, 3.12
- Python 3.13+: May have package compatibility issues (warning shown by setup_env.py)
