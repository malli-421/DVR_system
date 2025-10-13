import os
import cv2
import json
import math
import numpy as np
from datetime import datetime, timedelta
from typing import List

from brands.base import DVRInfo
from brands.factory import get_brand

os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

TARGET_CELL_W = 640
TARGET_CELL_H = 360
MAX_CHANNELS = 4


def load_config(path: str) -> List[DVRInfo]:
    with open(path, 'r') as f:
        cfg = json.load(f)
    dvrs: List[DVRInfo] = []
    for d in cfg['dvrs']:
        dvrs.append(DVRInfo(
            name=d['name'], ip=d['ip'], username=d['username'], password=d['password'], rtsp_url=d['rtsp_url']
        ))
    return dvrs


def expand_all(dvrs: List[DVRInfo], use_substream: bool = True, max_channels: int = 16) -> List[DVRInfo]:
    out: List[DVRInfo] = []
    for d in dvrs:
        brand = get_brand(d.name)
        out.extend(brand.expand_channels(d, max_channels=max_channels, use_substream=use_substream))
    return out


def playback_url(d: DVRInfo, start_time: datetime, duration: timedelta) -> str:
    brand = get_brand(d.name)
    return brand.build_playback_url(d, start_time, duration)


def live_url(d: DVRInfo) -> str:
    brand = get_brand(d.name)
    return brand.build_live_url(d)


def play_single_camera_at_timestamp(config_path: str, camera_name: str, ts: str, duration_minutes: int = 60):
    """Play a single camera by name at a specific timestamp."""
    dvrs = load_config(config_path)
    cams = expand_all(dvrs, use_substream=True)
    target = None
    for c in cams:
        if c.name.lower() == camera_name.lower():
            target = c
            break
    if target is None:
        print(f"Camera '{camera_name}' not found. Available: {[c.name for c in cams]}")
        return
    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    url = playback_url(target, dt, timedelta(minutes=duration_minutes))
    window = f"Playback - {target.name}"
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print(f"Cannot open playback stream for {target.name}")
        return
    cv2.namedWindow(window, cv2.WINDOW_AUTOSIZE)
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break
        cv2.imshow(window, frame)
        if (cv2.waitKey(1) & 0xFF) == ord('q'):
            break
    cap.release()
    cv2.destroyWindow(window)


def run_playback_for_timestamps(config_path: str, timestamps: List[str], duration_minutes: int = 60):
    """Given a list of timestamps from an ML model, pick one and play grid playback.

    Integrate this by passing the clicked timestamp from your UI.
    """
    if not timestamps:
        print("No timestamps provided")
        return
    # Take the first timestamp (your UI can choose a specific one)
    ts = timestamps[0]
    run_playback(config_path, ts, duration_minutes)


def grid_play(urls_with_names: List[tuple]):
    window_name = "All Cameras - Scalable Grid"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    caps = []
    # Probe and include only working streams, up to MAX_CHANNELS
    for name, url in urls_with_names:
        if len(caps) >= MAX_CHANNELS:
            break
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            cap.release()
            continue
        # Read one frame to confirm
        ret, frame = cap.read()
        if not ret or frame is None:
            cap.release()
            continue
        caps.append((name, cap))

    cols = math.ceil(math.sqrt(len(caps)))
    rows = math.ceil(len(caps) / cols)

    print(f"Showing {len(caps)} cameras in a {rows}x{cols} grid. Press 'q' to quit.")

    while True:
        frames = []
        for name, cap in caps:
            ret, frame = cap.read()
            if not ret or frame is None:
                tile = np.zeros((TARGET_CELL_H, TARGET_CELL_W, 3), dtype=np.uint8)
                cv2.putText(tile, f"No Frame: {name}", (10, TARGET_CELL_H // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
                frames.append(tile)
                continue
            h, w = frame.shape[:2]
            scale = min(TARGET_CELL_W / max(w, 1), TARGET_CELL_H / max(h, 1))
            nw = max(1, int(w * scale)); nh = max(1, int(h * scale))
            fr = cv2.resize(frame, (nw, nh))
            top = (TARGET_CELL_H - nh) // 2; bottom = TARGET_CELL_H - nh - top
            left = (TARGET_CELL_W - nw) // 2; right = TARGET_CELL_W - nw - left
            fr = cv2.copyMakeBorder(fr, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(20, 20, 20))
            cv2.putText(fr, name, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
            frames.append(fr)
        while len(frames) < rows * cols:
            frames.append(np.zeros((TARGET_CELL_H, TARGET_CELL_W, 3), dtype=np.uint8))
        grid_rows = []
        idx = 0
        for r in range(rows):
            row_frames = frames[idx:idx + cols]
            idx += cols
            grid_rows.append(cv2.hconcat(row_frames))
        grid = cv2.vconcat(grid_rows)
        cv2.imshow(window_name, grid)
        if (cv2.waitKey(1) & 0xFF) == 'q':
            break
    for _, cap in caps:
        cap.release()
    cv2.destroyWindow(window_name)


def run_live(config_path: str):
    dvrs = load_config(config_path)
    cams = expand_all(dvrs, use_substream=True)
    urls = [(d.name, live_url(d)) for d in cams]
    grid_play(urls)


def run_playback(config_path: str, ts: str, duration_minutes: int = 60):
    dvrs = load_config(config_path)
    cams = expand_all(dvrs, use_substream=True)
    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    urls = [(d.name, playback_url(d, dt, timedelta(minutes=duration_minutes))) for d in cams]
    grid_play(urls)


def run_list(config_path: str, use_substream: bool = True, max_channels: int = 16):
    """List only connected cameras by probing RTSP quickly."""
    dvrs = load_config(config_path)
    cams = expand_all(dvrs, use_substream=use_substream, max_channels=max_channels)
    connected = []
    for c in cams:
        url = live_url(c)
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        ok = False
        if cap.isOpened():
            # Try to read a few frames to ensure the stream is actually usable
            for _ in range(3):
                ret, frame = cap.read()
                if ret and frame is not None:
                    ok = True
                    break
        cap.release()
        if ok:
            connected.append(c)
    if not connected:
        print("No connected cameras detected.")
        return
    print("Connected cameras:")
    for idx, c in enumerate(connected, 1):
        print(f"{idx}. {c.name} ({c.ip})")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'live':
        run_live('dvr_config.json')
    elif len(sys.argv) > 2 and sys.argv[1] == 'timestamp':
        run_playback('dvr_config.json', sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == 'list':
        run_list('dvr_config.json')
    else:
        print("Usage:")
        print("  python scalable_player.py live")
        print("  python scalable_player.py timestamp 2025-10-10T10:00:00")
        print("  python scalable_player.py list  # list expanded camera channels")
