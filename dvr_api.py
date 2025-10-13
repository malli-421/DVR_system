import os
import cv2
import json
import threading
import time
import re
from datetime import datetime, timedelta
import numpy as np

# Prefer TCP transport for RTSP when using FFmpeg backend
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

class DVR:
    def __init__(self, name, ip, username, password, rtsp_url):
        self.name = name
        self.ip = ip
        self.username = username
        self.password = password
        self.rtsp_url = rtsp_url

    def play_stream(self, start_time=None):
        url = self.rtsp_url
        
        # If timestamp is provided, modify URL for playback instead of live streaming
        if start_time:
            # For Hikvision DVRs, playback URL format: rtsp://user:pass@ip:port/Streaming/tracks/101?starttime=YYYYMMDDTHHMMSSZ&endtime=YYYYMMDDTHHMMSSZ
            # Convert timestamp to Hikvision format (YYYYMMDDTHHMMSSZ)
            if isinstance(start_time, str):
                from datetime import datetime
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%Y%m%dT%H%M%SZ')
            else:
                formatted_time = start_time.strftime('%Y%m%dT%H%M%SZ')
            
            # Calculate end time (1 hour later by default)
            from datetime import datetime, timedelta
            if isinstance(start_time, str):
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = dt + timedelta(hours=1)
            else:
                end_dt = start_time + timedelta(hours=1)
            end_time = end_dt.strftime('%Y%m%dT%H%M%SZ')
            
            # Modify URL for playback
            if "Streaming/Channels" in url:
                url = url.replace("Streaming/Channels/101", f"Streaming/tracks/101?starttime={formatted_time}&endtime={end_time}")
            print(f"Playing recorded footage from timestamp: {start_time}")
        
        print(f"Trying to open RTSP stream for {self.name}: {url}")
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            print(f"Cannot open stream for {self.name}.")
            print("Possible reasons:")
            print("- RTSP URL is incorrect or unreachable")
            print("- DVR credentials are wrong or permissions not set")
            print("- Network/firewall is blocking access")
            print("- DVR RTSP feature is disabled or port is wrong")
            print("- OpenCV/FFmpeg does not support this stream format")
            print("- No recording found for the specified timestamp")
            print("Try testing the RTSP URL in VLC first.")
            return
        
        stream_type = "recorded footage" if start_time else "live stream"
        print(f"Successfully connected to {self.name} {stream_type}. Press 'q' to quit.")
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame. Stream may have ended or connection lost.")
                break
            cv2.imshow(f"{self.name} RTSP Stream", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()

    @staticmethod
    def from_dict(d):
        return DVR(d['name'], d['ip'], d['username'], d['password'], d['rtsp_url'])

class DVRManager:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        self.dvrs = [DVR.from_dict(dvr) for dvr in config['dvrs']]

    def get_dvr(self, name):
        for dvr in self.dvrs:
            if dvr.name == name:
                return dvr
        return None

    def list_dvrs(self):
        return [dvr.name for dvr in self.dvrs]
    
    def get_all_dvrs(self):
        return self.dvrs

class MultiCameraPlayer:
    def __init__(self, dvr_manager):
        self.dvr_manager = dvr_manager
        self.cameras = []
        self.capture_threads = []
        self.running = False
        
    def setup_cameras(self):
        """Setup all available cameras by expanding each DVR into its channels."""
        base_dvrs = self.dvr_manager.get_all_dvrs()
        expanded = []
        for dvr in base_dvrs:
            expanded.extend(self._expand_dvr_to_channels(dvr))
        self.cameras = expanded
        print(f"Found {len(self.cameras)} camera channels:")
        for i, camera in enumerate(self.cameras, 1):
            print(f"  {i}. {camera.name} - {camera.ip}")

    def _expand_dvr_to_channels(self, dvr, max_channels: int = 16):
        """Create per-channel camera entries from a single DVR definition.

        This assumes Hikvision-like RTSP pattern: /Streaming/Channels/{channelId}
        Channels typically: 101, 201, 301, ... for main streams.
        """
        matches = re.search(r"Streaming/Channels/(\d+)", dvr.rtsp_url)
        if not matches:
            # Cannot detect channel pattern; return the DVR as-is
            return [dvr]

        # Try to detect channel count via ONVIF; fall back to max_channels if it fails
        detected = self._detect_channel_count(dvr)
        channel_count = detected if isinstance(detected, int) and detected > 0 else max_channels
        channel_count = min(channel_count, max_channels)
        # Use sub-streams to reduce bandwidth (102, 202, ...)
        channel_ids = [i * 100 + 2 for i in range(1, channel_count + 1)]

        expanded = []
        for channel_id in channel_ids:
            rtsp_url = re.sub(r"Streaming/Channels/\d+", f"Streaming/Channels/{channel_id}", dvr.rtsp_url)
            name = f"{dvr.name}-CH{channel_id//100}"
            expanded.append(DVR(name, dvr.ip, dvr.username, dvr.password, rtsp_url))
        return expanded

    def _detect_channel_count(self, dvr):
        """Best-effort channel count detection using ONVIF profiles.
        Returns an integer or None when not available.
        """
        try:
            from onvif import ONVIFCamera
            cam = ONVIFCamera(dvr.ip, 80, dvr.username, dvr.password)
            media = cam.create_media_service()
            profiles = media.GetProfiles()
            return len(profiles) if profiles else None
        except Exception:
            return None
    
    def get_playback_url(self, camera, start_time=None):
        """Get the appropriate URL for playback or live stream"""
        url = camera.rtsp_url
        
        if start_time:
            # Convert timestamp to Hikvision format
            if isinstance(start_time, str):
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%Y%m%dT%H%M%SZ')
            else:
                formatted_time = start_time.strftime('%Y%m%dT%H%M%SZ')
            
            # Calculate end time (1 hour later by default)
            if isinstance(start_time, str):
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = dt + timedelta(hours=1)
            else:
                end_dt = start_time + timedelta(hours=1)
            end_time = end_dt.strftime('%Y%m%dT%H%M%SZ')
            
            # Modify URL for playback using the detected channel id
            channel_match = re.search(r"Streaming/Channels/(\d+)", url)
            if channel_match:
                channel_id = channel_match.group(1)
                url = re.sub(r"Streaming/Channels/\d+", f"Streaming/tracks/{channel_id}?starttime={formatted_time}&endtime={end_time}", url)
        
        return url
    
    def capture_camera(self, camera, start_time=None):
        """Capture frames from a single camera"""
        url = self.get_playback_url(camera, start_time)
        print(f"Connecting to {camera.name}: {url}")
        
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            print(f"Cannot open stream for {camera.name}")
            return
        
        window_name = f"{camera.name} - {camera.ip}"
        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                print(f"Failed to grab frame from {camera.name}")
                time.sleep(0.1)
                continue
            
            # Resize frame for better display
            height, width = frame.shape[:2]
            if width > 640:
                scale = 640 / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            cv2.imshow(window_name, frame)
            
            # Check for quit key
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.running = False
                break
        
        cap.release()
        cv2.destroyWindow(window_name)
    
    def play_all_cameras(self, start_time=None):
        """Play all cameras simultaneously"""
        if not self.cameras:
            self.setup_cameras()
        
        if not self.cameras:
            print("No cameras available!")
            return
        
        self.running = True
        self.capture_threads = []
        
        stream_type = "recorded footage" if start_time else "live stream"
        print(f"\nPlaying {stream_type} from {len(self.cameras)} cameras...")
        if start_time:
            print(f"Timestamp: {start_time}")
        print("Press 'q' in any window to quit all streams")
        
        # Start capture thread for each camera
        for camera in self.cameras:
            thread = threading.Thread(target=self.capture_camera, args=(camera, start_time))
            thread.daemon = True
            thread.start()
            self.capture_threads.append(thread)
        
        # Wait for all threads to complete
        for thread in self.capture_threads:
            thread.join()
        
        cv2.destroyAllWindows()
        print("All camera streams stopped.")

    def play_all_cameras_grid(self, start_time=None):
        """Play streams from all cameras in a single window arranged in a grid.

        If start_time is provided, attempts recorded playback; otherwise live.
        """
        if not self.cameras:
            self.setup_cameras()

        if not self.cameras:
            print("No cameras available!")
            return

        # Open a capture for each camera (limit to first 4 to avoid bandwidth issues)
        captures = []
        for camera in self.cameras[:4]:
            # Use playback URL if timestamp, otherwise live
            url = self.get_playback_url(camera, start_time) if start_time else camera.rtsp_url
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                print(f"Cannot open stream for {camera.name}")
            captures.append((camera, cap))

        # Filter to only opened caps
        captures = [(cam, cap) for cam, cap in captures if cap.isOpened()]
        if not captures:
            print("No camera streams could be opened.")
            return

        window_name = "All Cameras - Grid"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)

        # Determine grid size (up to 2x2, 3x3, etc.)
        num_streams = len(captures)
        # Simple heuristic for rows/cols close to square
        import math
        cols = math.ceil(math.sqrt(num_streams))
        rows = math.ceil(num_streams / cols)

        target_cell_width = 640
        target_cell_height = 360

        print(f"Showing {num_streams} cameras in a {rows}x{cols} grid. Press 'q' to quit.")

        while True:
            frames = []
            for cam, cap in captures:
                ret, frame = cap.read()
                if not ret or frame is None:
                    frame_padded = np.zeros((target_cell_height, target_cell_width, 3), dtype=np.uint8)
                    cv2.putText(frame_padded, f"No Frame: {cam.name}", (10, target_cell_height // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
                    frames.append(frame_padded)
                    continue
                # Resize to cell size keeping aspect
                h, w = frame.shape[:2]
                scale = min(target_cell_width / max(w, 1), target_cell_height / max(h, 1))
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                frame_resized = cv2.resize(frame, (new_w, new_h))
                # Pad to cell size
                top = (target_cell_height - new_h) // 2
                bottom = target_cell_height - new_h - top
                left = (target_cell_width - new_w) // 2
                right = target_cell_width - new_w - left
                frame_padded = cv2.copyMakeBorder(frame_resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(20, 20, 20))
                # Add a small label
                cv2.putText(frame_padded, cam.name, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
                frames.append(frame_padded)

            # Build grid canvas
            # Fill missing cells with black frames if needed
            try:
                import numpy as np
                while len(frames) < rows * cols:
                    frames.append(np.zeros((target_cell_height, target_cell_width, 3), dtype=np.uint8))
            except Exception:
                pass

            # Assemble rows
            grid_rows = []
            idx = 0
            for r in range(rows):
                row_frames = frames[idx:idx + cols]
                idx += cols
                row = cv2.hconcat(row_frames)
                grid_rows.append(row)
            grid = cv2.vconcat(grid_rows)

            cv2.imshow(window_name, grid)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

        for _, cap in captures:
            cap.release()
        cv2.destroyWindow(window_name)

    def play_single_camera_live(self, camera_name=None):
        """Play a single camera live stream in one window."""
        if not self.cameras:
            self.setup_cameras()
        cams = self.cameras
        if not cams:
            print("No cameras available!")
            return
        cam = None
        if camera_name:
            for c in cams:
                if c.name == camera_name:
                    cam = c
                    break
            if cam is None:
                print(f"Camera '{camera_name}' not found. Using first available.")
        if cam is None:
            cam = cams[0]

        url = cam.rtsp_url
        print(f"Opening live stream for {cam.name}: {url}")
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            print(f"Cannot open stream for {cam.name}")
            return
        window_name = f"{cam.name} - Live"
        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame.")
                break
            cv2.imshow(window_name, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyWindow(window_name)
    
    def show_day_highlights(self, date_str):
        """Show highlights from all cameras for a specific day"""
        try:
            # Parse date (YYYY-MM-DD format)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Create timestamps for different times of the day
            highlight_times = [
                date_obj.replace(hour=8, minute=0, second=0),   # 8:00 AM
                date_obj.replace(hour=12, minute=0, second=0),  # 12:00 PM
                date_obj.replace(hour=16, minute=0, second=0),  # 4:00 PM
                date_obj.replace(hour=20, minute=0, second=0),  # 8:00 PM
            ]
            
            print(f"Day highlights for {date_str}:")
            for i, time in enumerate(highlight_times, 1):
                print(f"{i}. {time.strftime('%H:%M')}")
            
            choice = input("Select highlight time (1-4) or 'all' for all times: ").strip()
            
            if choice == 'all':
                for time in highlight_times:
                    print(f"\nPlaying highlights at {time.strftime('%H:%M')}...")
                    self.play_all_cameras(time)
                    input("Press Enter to continue to next highlight...")
            else:
                try:
                    time_index = int(choice) - 1
                    if 0 <= time_index < len(highlight_times):
                        selected_time = highlight_times[time_index]
                        print(f"Playing highlights at {selected_time.strftime('%H:%M')}...")
                        self.play_all_cameras(selected_time)
                    else:
                        print("Invalid choice!")
                except ValueError:
                    print("Invalid choice!")
                    
        except ValueError:
            print("Invalid date format! Use YYYY-MM-DD (e.g., 2025-01-11)")
    
    def stop_all(self):
        """Stop all camera streams"""
        self.running = False
        cv2.destroyAllWindows()
