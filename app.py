import threading
import time
import os
import subprocess
import json
import tempfile
import glob
from datetime import datetime
from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO, emit
import base64
import numpy as np
from io import BytesIO
from PIL import Image
import ffmpeg
from config import get_rtsp_url, get_app_config, get_recording_config, get_streaming_config
from typing import Dict, Any, Optional, Iterator, Tuple, Union

app: Flask = Flask(__name__)
app_config: Dict[str, Any] = get_app_config()
app.config['SECRET_KEY'] = app_config['secret_key']
socketio: SocketIO = SocketIO(app, cors_allowed_origins="*")

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

        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def check_ffmpeg_installed(self) -> bool:
        """Check if FFmpeg is installed on the system"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_stream_info(self) -> Optional[Dict[str, Any]]:
        """Get stream information using FFprobe"""
        try:
            probe = ffmpeg.probe(self.rtsp_url)
            if probe and 'streams' in probe:
                video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
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
                print(f"📺 Stream info: {stream_info['width']}x{stream_info['height']} @ {stream_info['fps']} FPS")
                self.stream_info = stream_info
            else:
                print("⚠️  Could not get stream info, using defaults")
                self.stream_info = {'width': 640, 'height': 480, 'fps': 30, 'codec': 'h264'}

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
            print(f"📁 Using temp directory: {self.temp_dir}")

            # Simpler FFmpeg command - just extract frames without complex filtering
            frame_pattern = os.path.join(self.temp_dir, "frame_%04d.jpg")
            cmd = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',  # Use TCP instead of UDP for more reliable connection
                '-i', self.rtsp_url,
                '-f', 'image2',
                '-vf', 'fps=1',  # Extract 1 frame per second (simpler)
                '-y',  # Overwrite output files
                frame_pattern
            ]

            print(f"🔧 FFmpeg command: {' '.join(cmd)}")

            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Start frame reading thread
            self.frame_thread = threading.Thread(target=self._read_frames, daemon=True)
            self.frame_thread.start()

            # Start stderr monitoring thread
            self.stderr_thread = threading.Thread(target=self._monitor_stderr, daemon=True)
            self.stderr_thread.start()

            print("✅ FFmpeg process started successfully")

        except Exception as e:
            print(f"❌ Failed to start FFmpeg process: {e}")

    def _monitor_stderr(self) -> None:
        """Monitor FFmpeg stderr for errors and info"""
        while self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            try:
                line = self.ffmpeg_process.stderr.readline()
                if line:
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    if line_str and not line_str.startswith('frame='):
                        print(f"🔍 FFmpeg: {line_str}")
            except Exception as e:
                print(f"Error reading stderr: {e}")
                break

    def _read_frames(self) -> None:
        """Read frames from temporary files created by FFmpeg"""
        frame_count = 0
        last_frame_number = 0

        print("👀 Starting frame monitoring...")

        while self.streaming and self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            try:
                # Look for new frame files
                frame_files = glob.glob(os.path.join(self.temp_dir, "frame_*.jpg"))
                frame_files.sort()

                if frame_files:
                    # Get the latest frame file
                    latest_frame = frame_files[-1]

                    # Extract frame number from filename
                    frame_number = int(latest_frame.split("_")[-1].split(".")[0])

                    if frame_number > last_frame_number:
                        # Read the frame file
                        with open(latest_frame, 'rb') as f:
                            frame_data = f.read()

                        if frame_data and len(frame_data) > 1000:
                            frame_count += 1
                            with self.lock:
                                self.frame_buffer = frame_data
                                self.frame_ready.set()
                                self.last_frame_time = time.time()

                            if frame_count % 10 == 0:  # Log every 10th frame
                                print(f"📸 Read frame {frame_count}, size: {len(frame_data)} bytes")

                            last_frame_number = frame_number

                            # Clean up old frame files (keep only the latest 5)
                            if len(frame_files) > 5:
                                for old_file in frame_files[:-5]:
                                    try:
                                        os.remove(old_file)
                                    except:
                                        pass
                else:
                    # Log when no frame files are found
                    if frame_count == 0:
                        print(f"🔍 No frame files found in {self.temp_dir}")
                        # List contents of temp directory
                        try:
                            temp_contents = os.listdir(self.temp_dir)
                            print(f"📁 Temp directory contents: {temp_contents}")
                        except Exception as e:
                            print(f"Error listing temp directory: {e}")

                time.sleep(0.2)  # Check for new frames every 200ms

            except Exception as e:
                print(f"Error reading frame: {e}")
                time.sleep(0.1)

    def start_recording(self) -> bool:
        """Start recording video using FFmpeg"""
        if not self.streaming:
            return False

        try:
            # Create output filename with timestamp
            timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path: str = os.path.join(self.output_dir, f"recording_{timestamp}.mp4")

            # FFmpeg command for recording
            cmd = [
                'ffmpeg',
                '-i', self.rtsp_url,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',  # Good quality
                '-c:a', 'aac',
                '-f', 'mp4',
                '-y',  # Overwrite output file
                output_path
            ]

            self.recording_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            self.recording = True
            print(f"🎥 Started recording to: {output_path}")
            return True

        except Exception as e:
            print(f"❌ Error starting recording: {e}")
            return False

    def stop_recording(self) -> None:
        """Stop recording video"""
        self.recording = False
        if self.recording_process:
            self.recording_process.terminate()
            try:
                self.recording_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.recording_process.kill()
            self.recording_process = None
        print("⏹️  Recording stopped")

    def start_streaming(self) -> bool:
        """Start streaming video"""
        if not self.connect():
            return False

        self.streaming = True
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
                print(f"🗑️  Cleaned up temp directory: {self.temp_dir}")
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
                socketio.emit('video_frame', {'image': frame_base64})
            else:
                print("⚠️  No frame data available for web streaming")
        except Exception as e:
            print(f"Error emitting frame: {e}")

    def emit_frames_loop(self) -> None:
        """Loop to emit frames to web clients"""
        emit_count = 0
        while self.streaming:
            self._emit_frame()
            emit_count += 1
            if emit_count % 30 == 0:  # Log every 30th emission
                print(f"📡 Emitted {emit_count} frames to web clients")
            time.sleep(1.0 / self.streaming_config['frame_rate'])

# Global streamer instance
streamer: Optional[RTSPStreamer] = None

@app.route('/')
def index() -> str:
    """Main page"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed() -> Response:
    """Video feed for HTTP streaming"""
    def generate() -> Iterator[bytes]:
        while True:
            if streamer:
                frame = streamer.get_frame()
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.1)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_stream', methods=['POST'])
def start_stream() -> Response:
    """Start RTSP streaming"""
    global streamer

    # Get RTSP URL from configuration
    rtsp_url: str = get_rtsp_url()
    print(f"🚀 Starting stream with URL: {rtsp_url}")

    if streamer:
        streamer.stop_streaming()

    streamer = RTSPStreamer(rtsp_url)

    if streamer.start_streaming():
        # Start frame emission thread
        streamer.emit_thread = threading.Thread(target=streamer.emit_frames_loop, daemon=True)
        streamer.emit_thread.start()

        return jsonify({"status": "success", "message": "Stream started successfully"})
    else:
        return jsonify({"status": "error", "message": "Failed to start stream. Check camera connection and FFmpeg installation."})

@app.route('/stop_stream', methods=['POST'])
def stop_stream() -> Response:
    """Stop RTSP streaming"""
    global streamer

    if streamer:
        streamer.stop_streaming()
        streamer = None

    return jsonify({"status": "success", "message": "Stream stopped"})

@app.route('/start_recording', methods=['POST'])
def start_recording() -> Response:
    """Start recording video"""
    if streamer and streamer.start_recording():
        return jsonify({"status": "success", "message": "Recording started"})
    else:
        return jsonify({"status": "error", "message": "Failed to start recording. Make sure stream is active."})

@app.route('/stop_recording', methods=['POST'])
def stop_recording() -> Response:
    """Stop recording video"""
    if streamer:
        streamer.stop_recording()

    return jsonify({"status": "success", "message": "Recording stopped"})

@app.route('/status')
def status() -> Response:
    """Get current status"""
    if streamer:
        return jsonify({
            "streaming": streamer.streaming,
            "recording": streamer.recording,
            "connected": streamer.ffmpeg_process is not None and streamer.ffmpeg_process.poll() is None
        })
    else:
        return jsonify({
            "streaming": False,
            "recording": False,
            "connected": False
        })

@socketio.on('connect')
def handle_connect() -> None:
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect() -> None:
    print('Client disconnected')

if __name__ == '__main__':
    try:
        config: Dict[str, Any] = get_app_config()
        print("="*50)
        print("RTSP Camera Streaming Server (FFmpeg)")
        print("="*50)
        print(f"Server starting on: http://{config['host']}:{config['port']}")
        print(f"RTSP URL: {get_rtsp_url()}")
        print("\nIMPORTANT: Update config.py with your camera credentials!")
        print("Make sure FFmpeg is installed on your system.")
        print("="*50)

        socketio.run(
            app,
            host=config['host'],
            port=config['port'],
            debug=config['debug']
        )
    except KeyboardInterrupt:
        print("\nShutting down...")
        if streamer:
            streamer.stop_streaming()