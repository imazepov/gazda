import threading
import time
import os
import subprocess
import json
import tempfile
import glob
from datetime import datetime
from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit
from flask_httpauth import HTTPBasicAuth
import base64
import numpy as np
from io import BytesIO
from PIL import Image
import ffmpeg
from config import get_rtsp_url, get_app_config, get_recording_config, get_streaming_config, get_auth_config
from typing import Dict, Any, Optional, Iterator, Tuple, Union

app: Flask = Flask(__name__)
app_config: Dict[str, Any] = get_app_config()
app.config['SECRET_KEY'] = app_config['secret_key']
socketio: SocketIO = SocketIO(
    app, cors_allowed_origins="*", async_mode='threading')

# HTTP Basic Authentication setup
auth: HTTPBasicAuth = HTTPBasicAuth()
auth_config: Dict[str, Any] = get_auth_config()


@auth.verify_password
def verify_password(username: str, password: str) -> Optional[str]:
    """Verify username and password for HTTP Basic Auth"""
    if not auth_config.get('enabled', True):
        return username  # Auth disabled, allow all

    if username == auth_config['username'] and password == auth_config['password']:
        return username
    return None


@app.before_request
def require_authentication() -> Optional[Response]:
    """Require authentication for all routes"""
    if not auth_config.get('enabled', True):
        return None  # Auth disabled, allow all

    # Allow WebSocket connections (they'll be authenticated via the initial HTTP handshake)
    if request.path.startswith('/socket.io/'):
        return None

    # Extract credentials from Authorization header
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Basic '):
        # No auth provided, return 401 with WWW-Authenticate header to trigger browser dialog
        return Response(
            'Authentication required',
            401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'}
        )

    # Decode Basic Auth credentials
    try:
        encoded_credentials = auth_header.split(' ')[1]
        decoded_credentials = base64.b64decode(
            encoded_credentials).decode('utf-8')
        username, password = decoded_credentials.split(':', 1)
    except (IndexError, ValueError, UnicodeDecodeError):
        # Invalid auth header format
        return Response(
            'Invalid authentication format',
            401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'}
        )

    # Verify credentials using our verify_password function
    auth_result = verify_password(username, password)
    if auth_result is None:
        # Invalid credentials - return 401 to trigger dialog again
        return Response(
            'Invalid credentials',
            401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'}
        )

    # Authentication successful
    return None


class RTSPStreamer:
    def __init__(self, rtsp_url: str, recording_config: Optional[Dict[str, Any]] = None, streaming_config: Optional[Dict[str, Any]] = None) -> None:
        self.rtsp_url: str = rtsp_url
        self.recording_config = recording_config or get_recording_config()
        self.streaming_config = streaming_config or get_streaming_config()
        self.output_dir: str = self.recording_config['output_directory']

        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.recording_process: Optional[subprocess.Popen] = None
        self.recording: bool = False
        self.streaming: bool = False
        self.frame: Optional[np.ndarray] = None
        self.lock: threading.Lock = threading.Lock()
        self.frame_buffer: bytes = b""
        self.frame_ready: threading.Event = threading.Event()
        self.last_frame_time: float = 0
        self.temp_dir: Optional[str] = None

        # Monitoring statistics
        self.frames_received: int = 0
        self.frames_emitted: int = 0
        self.last_stats_report: float = time.time()
        self.ffmpeg_restart_count: int = 0
        self.last_frame_warning_time: float = 0

        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def check_ffmpeg_installed(self) -> bool:
        """Check if FFmpeg is installed on the system"""
        try:
            subprocess.run(['ffmpeg', '-version'],
                           capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_stream_info(self) -> Optional[Dict[str, Any]]:
        """Get stream information using FFprobe"""
        try:
            probe = ffmpeg.probe(self.rtsp_url)
            if probe and 'streams' in probe:
                video_stream = next(
                    (s for s in probe['streams'] if s['codec_type'] == 'video'), None)
                if video_stream:
                    return {
                        'width': int(video_stream.get('width', 640)),
                        'height': int(video_stream.get('height', 480)),
                        'fps': eval(video_stream.get('r_frame_rate', '30/1')),
                        'codec': video_stream.get('codec_name', 'h264')
                    }
        except Exception as e:
            print(f"Error probing stream: {e}")
        return None

    def connect(self) -> bool:
        """Connect to RTSP stream with FFmpeg"""
        if not self.check_ffmpeg_installed():
            print("❌ FFmpeg is not installed. Please install FFmpeg first.")
            print("   macOS: brew install ffmpeg")
            print("   Ubuntu: sudo apt install ffmpeg")
            print("   Windows: Download from https://ffmpeg.org/download.html")
            return False

        try:
            print(f"🔗 Connecting to RTSP stream: {self.rtsp_url}")

            # Get stream information
            stream_info = self.get_stream_info()
            if stream_info:
                print(
                    f"📺 Stream info: {stream_info['width']}x{stream_info['height']} @ {stream_info['fps']} FPS")
                self.stream_info = stream_info
            else:
                print("⚠️  Could not get stream info, using defaults")
                self.stream_info = {'width': 640,
                                    'height': 480, 'fps': 30, 'codec': 'h264'}

            # Start FFmpeg process for frame extraction
            self.start_ffmpeg_process()
            return True

        except Exception as e:
            print(f"❌ Failed to connect to RTSP stream: {e}")
            return False

    def start_ffmpeg_process(self) -> None:
        """Start FFmpeg process to extract frames from RTSP stream"""
        try:
            # Create temporary directory for frames
            self.temp_dir = tempfile.mkdtemp(prefix="rtsp_frames_")

            # Extract frames at the configured frame rate
            fps = self.streaming_config['frame_rate']
            frame_pattern = os.path.join(self.temp_dir, "frame_%04d.jpg")
            cmd = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',  # Use TCP instead of UDP for more reliable connection
                '-timeout', '5000000',  # 5 second timeout for connection (in microseconds)
                '-stimeout', '5000000',  # 5 second timeout for socket operations
                '-rw_timeout', '10000000',  # 10 second timeout for read/write operations
                '-reconnect', '1',  # Enable automatic reconnection
                '-reconnect_streamed', '1',  # Reconnect for streamed input
                '-reconnect_delay_max', '5',  # Max delay between reconnect attempts (seconds)
                '-i', self.rtsp_url,
                '-f', 'image2',
                '-vf', f'fps={fps}',  # Extract frames at configured FPS
                '-y',  # Overwrite output files
                frame_pattern
            ]

            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Start frame reading thread
            self.frame_thread = threading.Thread(
                target=self._read_frames, daemon=True)
            self.frame_thread.start()

            # Start stderr monitoring thread
            self.stderr_thread = threading.Thread(
                target=self._monitor_stderr, daemon=True)
            self.stderr_thread.start()

            # Start health monitoring thread
            self.monitor_thread = threading.Thread(
                target=self._monitor_health, daemon=True)
            self.monitor_thread.start()

            print("✅ FFmpeg process started successfully")

        except Exception as e:
            print(f"Failed to start FFmpeg process: {e}")

    def _monitor_stderr(self) -> None:
        """Monitor FFmpeg stderr for errors and info"""
        while self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            try:
                line = self.ffmpeg_process.stderr.readline()
                if line:
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    # Only log errors and warnings, skip normal status messages
                    if line_str and ('error' in line_str.lower() or 'warning' in line_str.lower()):
                        print(f"🔍 FFmpeg: {line_str}")
            except Exception as e:
                print(f"Error reading stderr: {e}")
                break

    def _read_frames(self) -> None:
        """Read frames from temporary files created by FFmpeg"""
        frame_count = 0
        last_frame_number = 0

        while self.streaming and self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            try:
                # Look for new frame files
                frame_files = glob.glob(
                    os.path.join(self.temp_dir, "frame_*.jpg"))
                frame_files.sort()

                if frame_files:
                    # Get the latest frame file
                    latest_frame = frame_files[-1]

                    # Extract frame number from filename
                    frame_number = int(
                        latest_frame.split("_")[-1].split(".")[0])

                    if frame_number > last_frame_number:
                        # Wait a moment to ensure file is fully written
                        time.sleep(0.1)

                        # Read the frame file
                        with open(latest_frame, 'rb') as f:
                            frame_data = f.read()

                        if frame_data and len(frame_data) > 1000:
                            frame_count += 1
                            with self.lock:
                                self.frame_buffer = frame_data
                                self.frame_ready.set()
                                self.last_frame_time = time.time()
                                self.frames_received += 1

                            last_frame_number = frame_number

                            # Clean up old frame files (keep only the latest 5)
                            if len(frame_files) > 5:
                                for old_file in frame_files[:-5]:
                                    try:
                                        os.remove(old_file)
                                    except:
                                        pass

                time.sleep(0.2)  # Check for new frames every 200ms

            except Exception as e:
                print(f"Error reading frame: {e}")
                time.sleep(0.1)

    def _monitor_health(self) -> None:
        """Monitor stream health, detect crashes, and report stats"""
        FRAME_TIMEOUT = 30  # Warn if no frames for 30 seconds
        FRAME_TIMEOUT_RESTART = 60  # Restart FFmpeg if no frames for 60 seconds
        STATS_INTERVAL = 60  # Report stats every 60 seconds

        while self.streaming:
            try:
                current_time = time.time()

                # Check for frame timeout
                if self.last_frame_time > 0:
                    time_since_last_frame = current_time - self.last_frame_time

                    if time_since_last_frame > FRAME_TIMEOUT:
                        # Only warn once every 60 seconds to avoid log spam
                        if current_time - self.last_frame_warning_time > 60:
                            print(f"⚠️  WARNING: No frames received for {int(time_since_last_frame)} seconds")
                            self.last_frame_warning_time = current_time

                    # If FFmpeg is stuck (running but not producing frames), restart it
                    if time_since_last_frame > FRAME_TIMEOUT_RESTART:
                        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
                            print(f"💀 FFmpeg stuck (running but no frames for {int(time_since_last_frame)}s)")
                            print(f"🔄 Killing and restarting FFmpeg... (restart #{self.ffmpeg_restart_count + 1})")

                            # Force kill the stuck process
                            try:
                                self.ffmpeg_process.terminate()
                                time.sleep(2)
                                if self.ffmpeg_process.poll() is None:
                                    self.ffmpeg_process.kill()
                            except Exception as e:
                                print(f"Error killing FFmpeg: {e}")

                            self.ffmpeg_restart_count += 1

                            # Try to restart FFmpeg
                            try:
                                time.sleep(2)  # Brief pause before restart
                                self.start_ffmpeg_process()
                                print("✅ FFmpeg process restarted successfully")
                                # Reset frame time tracking
                                self.last_frame_time = 0
                                self.last_frame_warning_time = 0
                            except Exception as e:
                                print(f"❌ Failed to restart FFmpeg: {e}")
                                print(f"⏸️  Will retry in 10 seconds...")
                                time.sleep(10)

                # Check if FFmpeg process has crashed (exited)
                elif self.ffmpeg_process and self.ffmpeg_process.poll() is not None:
                    print(f"❌ FFmpeg process crashed (exit code: {self.ffmpeg_process.returncode})")
                    print(f"🔄 Attempting to restart FFmpeg... (restart #{self.ffmpeg_restart_count + 1})")

                    self.ffmpeg_restart_count += 1

                    # Try to restart FFmpeg
                    try:
                        time.sleep(2)  # Brief pause before restart
                        self.start_ffmpeg_process()
                        print("✅ FFmpeg process restarted successfully")
                    except Exception as e:
                        print(f"❌ Failed to restart FFmpeg: {e}")
                        print(f"⏸️  Will retry in 10 seconds...")
                        time.sleep(10)

                # Report stats periodically
                if current_time - self.last_stats_report > STATS_INTERVAL:
                    uptime = current_time - self.last_stats_report
                    fps_received = self.frames_received / uptime if uptime > 0 else 0
                    fps_emitted = self.frames_emitted / uptime if uptime > 0 else 0

                    print(f"📊 Stats (last {int(uptime)}s): "
                          f"Received: {self.frames_received} frames ({fps_received:.1f} FPS), "
                          f"Emitted: {self.frames_emitted} frames ({fps_emitted:.1f} FPS), "
                          f"FFmpeg restarts: {self.ffmpeg_restart_count}")

                    # Reset counters for next interval
                    self.frames_received = 0
                    self.frames_emitted = 0
                    self.last_stats_report = current_time

                time.sleep(5)  # Check every 5 seconds

            except Exception as e:
                print(f"Error in health monitor: {e}")
                time.sleep(5)

    def start_recording(self) -> bool:
        """Start continuous recording with automatic file rotation"""
        if not self.streaming:
            return False

        self.recording = True
        # Start recording loop in background thread
        self.recording_thread = threading.Thread(
            target=self._recording_loop, daemon=True)
        self.recording_thread.start()
        return True

    def _recording_loop(self) -> None:
        """Continuous recording loop with file rotation based on size"""
        # Get max file size from config (in MB) and convert to bytes
        max_file_size_mb = self.recording_config.get('max_file_size_mb', 10)
        MAX_FILE_SIZE = max_file_size_mb * 1024 * 1024

        while self.recording and self.streaming:
            try:
                # Create output filename with timestamp
                timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path: str = os.path.join(
                    self.output_dir, f"recording_{timestamp}.mp4")

                # Build FFmpeg command with compression settings
                cmd = [
                    'ffmpeg',
                    '-rtsp_transport', 'tcp',
                    '-timeout', '5000000',  # 5 second timeout for connection (in microseconds)
                    '-stimeout', '5000000',  # 5 second timeout for socket operations
                    '-rw_timeout', '10000000',  # 10 second timeout for read/write operations
                    '-reconnect', '1',  # Enable automatic reconnection
                    '-reconnect_streamed', '1',  # Reconnect for streamed input
                    '-reconnect_delay_max', '5',  # Max delay between reconnect attempts (seconds)
                    '-i', self.rtsp_url,
                ]

                # Video encoding settings
                cmd.extend([
                    '-c:v', self.recording_config['video_codec'],
                    '-preset', self.recording_config['preset'],
                    '-crf', str(self.recording_config['crf']),
                ])

                # Add resolution scaling if configured
                if self.recording_config.get('resolution'):
                    cmd.extend(
                        ['-vf', f"scale={self.recording_config['resolution']}"])

                # Audio encoding
                cmd.extend([
                    '-c:a', self.recording_config['audio_codec'],
                    '-f', 'mp4',
                    '-movflags', '+faststart',
                    '-y',
                    output_path
                ])

                print(f"🎥 Started recording: {output_path}")

                self.recording_process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,  # Allow sending 'q' to gracefully stop
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                # Monitor the recording process and file size
                start_time = time.time()
                while self.recording and self.streaming:
                    if self.recording_process.poll() is not None:
                        # Process ended unexpectedly - log error
                        stderr_output = self.recording_process.stderr.read().decode('utf-8',
                                                                                    errors='ignore')
                        print(f"❌ Recording process ended unexpectedly")
                        if stderr_output:
                            # Only show last few lines of error
                            error_lines = stderr_output.strip().split('\n')
                            for line in error_lines[-5:]:
                                if 'error' in line.lower() or 'invalid' in line.lower():
                                    print(f"   FFmpeg error: {line}")
                        print("📹 Restarting recording in 5 seconds...")
                        time.sleep(5)
                        break

                    # Check file size every 10 seconds
                    if os.path.exists(output_path):
                        file_size = os.path.getsize(output_path)
                        if file_size >= MAX_FILE_SIZE:
                            print(
                                f"📏 File reached {file_size / (1024*1024):.1f}MB, rotating...")
                            # Gracefully stop this recording to start a new file
                            self._stop_recording_gracefully()
                            break

                    time.sleep(10)

                # Clean up this recording process if still running
                if self.recording_process and self.recording_process.poll() is None:
                    self._stop_recording_gracefully()

            except Exception as e:
                print(f"❌ Error in recording loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)  # Wait before retrying

    def _stop_recording_gracefully(self) -> None:
        """Gracefully stop FFmpeg recording process to ensure file is properly finalized"""
        if not self.recording_process or self.recording_process.poll() is not None:
            return

        try:
            # Method 1: Send 'q' to FFmpeg stdin to trigger graceful shutdown
            # This tells FFmpeg to finish writing and close the file properly
            print("📝 Finalizing recording file...")
            self.recording_process.stdin.write(b'q')
            self.recording_process.stdin.flush()

            # Wait up to 10 seconds for graceful shutdown
            try:
                self.recording_process.wait(timeout=10)
                print("✅ Recording file finalized successfully")
            except subprocess.TimeoutExpired:
                print("⚠️  FFmpeg didn't stop gracefully, sending SIGTERM...")
                # Method 2: Send SIGTERM (still allows FFmpeg to finish writing)
                self.recording_process.terminate()
                try:
                    self.recording_process.wait(timeout=5)
                    print("✅ Recording stopped with SIGTERM")
                except subprocess.TimeoutExpired:
                    # Last resort: SIGKILL (may corrupt the file)
                    print("⚠️  Force killing FFmpeg (file may be incomplete)")
                    self.recording_process.kill()
                    self.recording_process.wait()

        except Exception as e:
            print(f"❌ Error stopping recording gracefully: {e}")
            # Fallback to terminate
            try:
                self.recording_process.terminate()
                self.recording_process.wait(timeout=5)
            except:
                self.recording_process.kill()

    def stop_recording(self) -> None:
        """Stop recording video"""
        self.recording = False
        self._stop_recording_gracefully()
        self.recording_process = None
        print("⏹️  Recording stopped")

    def start_streaming(self) -> bool:
        """Start streaming video"""
        # Set streaming to True BEFORE connecting so threads can start
        self.streaming = True

        if not self.connect():
            self.streaming = False  # Reset on failure
            return False

        return True

    def stop_streaming(self) -> None:
        """Stop streaming video"""
        self.streaming = False

        # Stop FFmpeg process
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()
            self.ffmpeg_process = None

        # Clean up temporary directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temp directory: {e}")

        # Stop recording if active
        if self.recording:
            self.stop_recording()

    def get_frame(self) -> Optional[bytes]:
        """Get current frame for HTTP streaming"""
        # Check if we have a recent frame (within last 10 seconds)
        if time.time() - self.last_frame_time < 10:
            with self.lock:
                if self.frame_buffer and len(self.frame_buffer) > 1000:
                    return self.frame_buffer
        return None

    def _emit_frame(self) -> None:
        """Emit frame to web clients"""
        try:
            frame_data = self.get_frame()
            if frame_data:
                frame_base64 = base64.b64encode(frame_data).decode('utf-8')
                # Emit to all connected clients using Flask-SocketIO
                socketio.emit('video_frame', {'image': frame_base64})
                self.frames_emitted += 1
        except Exception as e:
            print(f"Error emitting frame: {e}")

    def emit_frames_loop(self) -> None:
        """Loop to emit frames to web clients"""
        while self.streaming:
            self._emit_frame()
            time.sleep(1.0 / self.streaming_config['frame_rate'])


# Global streamer instance
streamer: Optional[RTSPStreamer] = None


@app.route('/')
def index() -> str:
    """Main page"""
    return render_template('index.html')


@app.route('/video_feed')
def video_feed() -> Response:
    """Video feed for HTTP streaming (backup/alternative to WebSocket)"""
    def generate() -> Iterator[bytes]:
        while True:
            if streamer:
                frame = streamer.get_frame()
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.1)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/status')
def status() -> Response:
    """Get current status"""
    if streamer:
        return jsonify({
            "streaming": streamer.streaming,
            "recording": streamer.recording,
            "connected": streamer.ffmpeg_process is not None and streamer.ffmpeg_process.poll() is None,
            "max_file_size_mb": streamer.recording_config.get('max_file_size_mb', 10)
        })
    else:
        return jsonify({
            "streaming": False,
            "recording": False,
            "connected": False,
            "max_file_size_mb": 10
        })


@app.route('/recordings')
def recordings_page() -> str:
    """Recordings browser page"""
    return render_template('recordings.html')


@app.route('/api/recordings')
def list_recordings() -> Response:
    """List all recordings with metadata"""
    from config import get_recording_config
    import re
    from datetime import datetime as dt

    recording_config = get_recording_config()
    recordings_dir = recording_config['output_directory']

    if not os.path.exists(recordings_dir):
        return jsonify([])

    recordings = []
    pattern = re.compile(r'recording_(\d{8})_(\d{6})\.mp4')

    for filename in os.listdir(recordings_dir):
        if not filename.endswith('.mp4'):
            continue

        filepath = os.path.join(recordings_dir, filename)

        # Parse timestamp from filename
        match = pattern.match(filename)
        if match:
            date_str = match.group(1)  # YYYYMMDD
            time_str = match.group(2)  # HHMMSS
            timestamp = dt.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
        else:
            # Fallback to file modification time
            timestamp = dt.fromtimestamp(os.path.getmtime(filepath))

        # Get file info
        file_size = os.path.getsize(filepath)

        # Try to get video duration using ffmpeg.probe
        duration = None
        try:
            probe = ffmpeg.probe(filepath)
            duration = float(probe['format']['duration'])
        except:
            pass

        recordings.append({
            'filename': filename,
            'timestamp': timestamp.isoformat(),
            'date': timestamp.strftime('%Y-%m-%d'),
            'time': timestamp.strftime('%H:%M:%S'),
            'size': file_size,
            'size_mb': round(file_size / (1024 * 1024), 2),
            'duration': duration,
            'duration_formatted': f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else None
        })

    # Sort by timestamp, newest first
    recordings.sort(key=lambda x: x['timestamp'], reverse=True)

    return jsonify(recordings)


@app.route('/api/recordings/<filename>')
def serve_recording(filename: str) -> Response:
    """Serve a recording file"""
    from config import get_recording_config
    from flask import send_from_directory

    recording_config = get_recording_config()
    recordings_dir = recording_config['output_directory']

    # Security: prevent directory traversal
    if '..' in filename or '/' in filename:
        return jsonify({"error": "Invalid filename"}), 400

    return send_from_directory(recordings_dir, filename)


@app.route('/api/recordings/<filename>', methods=['DELETE'])
def delete_recording(filename: str) -> Response:
    """Delete a recording file"""
    from config import get_recording_config

    recording_config = get_recording_config()
    recordings_dir = recording_config['output_directory']

    # Security: prevent directory traversal
    if '..' in filename or '/' in filename:
        return jsonify({"error": "Invalid filename"}), 400

    filepath = os.path.join(recordings_dir, filename)

    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    try:
        os.remove(filepath)
        return jsonify({"success": True, "message": f"Deleted {filename}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@socketio.on('connect')
def handle_connect() -> None:
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect() -> None:
    print('Client disconnected')


# Global initialization lock to prevent multiple starts
_initialization_lock = threading.Lock()
_initialized = False


def initialize_streaming() -> None:
    """Initialize streaming and recording on startup"""
    global streamer, _initialized

    with _initialization_lock:
        # Prevent multiple initializations
        if _initialized or streamer is not None:
            print("⚠️  Streaming already initialized, skipping...")
            return

        _initialized = True

        rtsp_url = get_rtsp_url()
        print(f"🚀 Starting continuous streaming and recording...")
        print(f"📹 RTSP URL: {rtsp_url}")

        streamer = RTSPStreamer(rtsp_url)

        if streamer.start_streaming():
            # Start frame emission using Flask-SocketIO background task
            socketio.start_background_task(streamer.emit_frames_loop)

            # Start continuous recording
            if streamer.start_recording():
                max_size = streamer.recording_config.get(
                    'max_file_size_mb', 10)
                print("✅ Streaming and recording started successfully")
                print(f"📂 Recordings will be saved to: {streamer.output_dir}")
                print(f"📏 Files will auto-rotate at {max_size}MB")
            else:
                print("⚠️  Streaming started but recording failed")
        else:
            print("❌ Failed to start streaming")
            _initialized = False  # Reset on failure


_auto_start_scheduled = False


def start_auto_streaming():
    """Schedule auto-start streaming - call this from server startup"""
    global _auto_start_scheduled

    if _auto_start_scheduled:
        print("⚠️  Auto-start already scheduled, skipping...")
        return

    _auto_start_scheduled = True
    print("📅 Scheduling auto-start in 2 seconds...")

    def _auto_start_streaming():
        time.sleep(2)  # Wait for server to fully initialize
        initialize_streaming()

    socketio.start_background_task(_auto_start_streaming)


def cleanup_on_exit():
    """Cleanup function called on exit"""
    global streamer
    print("\n🛑 Shutting down gracefully...")
    if streamer:
        print("⏸️  Stopping streaming and finalizing recordings...")
        streamer.stop_streaming()
    print("✅ Cleanup complete")


if __name__ == '__main__':
    import signal
    import atexit

    # Register cleanup handler
    atexit.register(cleanup_on_exit)

    # Handle SIGTERM and SIGINT gracefully
    def signal_handler(sig, frame):
        print(f"\n⚠️  Received signal {sig}")
        cleanup_on_exit()
        import sys
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        config: Dict[str, Any] = get_app_config()
        print("="*50)
        print("RTSP Camera Streaming Server (FFmpeg)")
        print("Continuous Streaming & Recording Mode")
        print("="*50)
        print(f"Server starting on: http://{config['host']}:{config['port']}")
        print("Make sure FFmpeg is installed on your system.")
        print("="*50)

        # Start auto-streaming
        start_auto_streaming()

        socketio.run(
            app,
            host=config['host'],
            port=config['port'],
            debug=config['debug']
        )
    except KeyboardInterrupt:
        pass  # Handled by signal_handler
    except Exception as e:
        print(f"❌ Error: {e}")
        cleanup_on_exit()
    finally:
        print("👋 Server stopped")
