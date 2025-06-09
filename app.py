import cv2
import threading
import time
import os
from datetime import datetime
from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO, emit
import base64
import numpy as np
from io import BytesIO
from PIL import Image
from config import get_rtsp_url, get_app_config, get_recording_config, get_streaming_config

app = Flask(__name__)
app_config = get_app_config()
app.config['SECRET_KEY'] = app_config['secret_key']
socketio = SocketIO(app, cors_allowed_origins="*")

class RTSPStreamer:
    def __init__(self, rtsp_url, recording_config=None, streaming_config=None):
        self.rtsp_url = rtsp_url
        self.recording_config = recording_config or get_recording_config()
        self.streaming_config = streaming_config or get_streaming_config()
        self.output_dir = self.recording_config['output_directory']

        self.cap = None
        self.out = None
        self.recording = False
        self.streaming = False
        self.frame = None
        self.lock = threading.Lock()

        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def connect(self):
        """Connect to RTSP stream with retry logic"""
        attempts = 0
        max_attempts = self.streaming_config['reconnect_attempts']
        delay = self.streaming_config['reconnect_delay']

        while attempts < max_attempts:
            try:
                print(f"Attempting to connect to RTSP stream (attempt {attempts + 1}/{max_attempts})")
                self.cap = cv2.VideoCapture(self.rtsp_url)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.streaming_config['buffer_size'])

                if self.cap.isOpened():
                    # Test if we can read a frame
                    ret, _ = self.cap.read()
                    if ret:
                        print(f"Successfully connected to RTSP stream: {self.rtsp_url}")
                        # Reset to beginning for streaming
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        return True
                    else:
                        print("Connected to stream but couldn't read frames")
                        self.cap.release()

                print(f"Failed to connect to RTSP stream: {self.rtsp_url}")

            except Exception as e:
                print(f"Error connecting to RTSP stream: {e}")

            attempts += 1
            if attempts < max_attempts:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)

        print(f"Failed to connect after {max_attempts} attempts")
        return False

    def start_recording(self):
        """Start recording video to disk"""
        if not self.cap or not self.cap.isOpened():
            return False

        try:
            # Get video properties
            fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or self.recording_config['default_fps']
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            print(f"Video properties: {width}x{height} @ {fps} FPS")

            # Create output filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"recording_{timestamp}.mp4")

            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*self.recording_config['video_codec'])
            self.out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            if not self.out.isOpened():
                print("Failed to create video writer")
                return False

            self.recording = True
            print(f"Started recording to: {output_path}")
            return True

        except Exception as e:
            print(f"Error starting recording: {e}")
            return False

    def stop_recording(self):
        """Stop recording video"""
        self.recording = False
        if self.out:
            self.out.release()
            self.out = None
        print("Recording stopped")

    def start_streaming(self):
        """Start streaming video"""
        if not self.connect():
            return False

        self.streaming = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()
        return True

    def stop_streaming(self):
        """Stop streaming video"""
        self.streaming = False
        if self.cap:
            self.cap.release()
        if self.out:
            self.out.release()

    def _stream_loop(self):
        """Main streaming loop"""
        frame_time = 1.0 / self.streaming_config['frame_rate']
        consecutive_failures = 0
        max_failures = 10

        while self.streaming and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()

            if not ret:
                consecutive_failures += 1
                print(f"Failed to read frame from RTSP stream (failure {consecutive_failures})")

                if consecutive_failures >= max_failures:
                    print("Too many consecutive failures, attempting to reconnect...")
                    if self.connect():
                        consecutive_failures = 0
                        continue
                    else:
                        print("Reconnection failed, stopping stream")
                        break

                time.sleep(0.1)
                continue

            consecutive_failures = 0  # Reset failure counter on successful read

            # Store frame for web streaming
            with self.lock:
                self.frame = frame.copy()

            # Write frame to disk if recording
            if self.recording and self.out:
                self.out.write(frame)

            # Emit frame to web clients
            self._emit_frame(frame)

            time.sleep(frame_time)

    def _emit_frame(self, frame):
        """Emit frame to web clients"""
        try:
            # Convert frame to JPEG
            quality = self.recording_config['jpeg_quality']
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')

            # Emit to all connected clients
            socketio.emit('video_frame', {'image': frame_base64})
        except Exception as e:
            print(f"Error emitting frame: {e}")

    def get_frame(self):
        """Get current frame for HTTP streaming"""
        with self.lock:
            if self.frame is not None:
                quality = self.recording_config['jpeg_quality']
                _, buffer = cv2.imencode('.jpg', self.frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                return buffer.tobytes()
        return None

# Global streamer instance
streamer = None

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video feed for HTTP streaming"""
    def generate():
        while True:
            if streamer:
                frame = streamer.get_frame()
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.033)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_stream', methods=['POST'])
def start_stream():
    """Start RTSP streaming"""
    global streamer

    # Get RTSP URL from configuration
    rtsp_url = get_rtsp_url()
    print(f"Starting stream with URL: {rtsp_url}")

    if streamer:
        streamer.stop_streaming()

    streamer = RTSPStreamer(rtsp_url)

    if streamer.start_streaming():
        return jsonify({"status": "success", "message": "Stream started successfully"})
    else:
        return jsonify({"status": "error", "message": "Failed to start stream. Check camera connection and credentials."})

@app.route('/stop_stream', methods=['POST'])
def stop_stream():
    """Stop RTSP streaming"""
    global streamer

    if streamer:
        streamer.stop_streaming()
        streamer = None

    return jsonify({"status": "success", "message": "Stream stopped"})

@app.route('/start_recording', methods=['POST'])
def start_recording():
    """Start recording video"""
    if streamer and streamer.start_recording():
        return jsonify({"status": "success", "message": "Recording started"})
    else:
        return jsonify({"status": "error", "message": "Failed to start recording. Make sure stream is active."})

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    """Stop recording video"""
    if streamer:
        streamer.stop_recording()

    return jsonify({"status": "success", "message": "Recording stopped"})

@app.route('/status')
def status():
    """Get current status"""
    if streamer:
        return jsonify({
            "streaming": streamer.streaming,
            "recording": streamer.recording,
            "connected": streamer.cap is not None and streamer.cap.isOpened()
        })
    else:
        return jsonify({
            "streaming": False,
            "recording": False,
            "connected": False
        })

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    try:
        config = get_app_config()
        print("="*50)
        print("RTSP Camera Streaming Server")
        print("="*50)
        print(f"Server starting on: http://{config['host']}:{config['port']}")
        print(f"RTSP URL: {get_rtsp_url()}")
        print("\nIMPORTANT: Update config.py with your camera credentials!")
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