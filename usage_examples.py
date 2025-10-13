#!/usr/bin/env python3
"""
Usage examples for the DVR Multi-Camera System
"""

from dvr_api import DVRManager, MultiCameraPlayer
from datetime import datetime

def main():
    print("DVR Multi-Camera System - Usage Examples")
    print("="*50)
    
    # Initialize the system
    manager = DVRManager("dvr_config.json")
    multi_player = MultiCameraPlayer(manager)
    
    # Show available cameras
    print("Available cameras:")
    multi_player.setup_cameras()
    
    print("\nExample 1: Play live stream from all cameras")
    print("Command: python dvr_main.py live")
    print("Or use interactive mode and select option 1")
    
    print("\nExample 2: Play recorded footage from all cameras at specific timestamp")
    print("Command: python dvr_main.py timestamp 2025-01-11T10:15:00")
    print("Or use interactive mode and select option 2")
    
    print("\nExample 3: Show day highlights from all cameras")
    print("Command: python dvr_main.py highlights 2025-01-11")
    print("Or use interactive mode and select option 3")
    
    print("\nExample 4: Play single camera with timestamp")
    print("Command: python dvr_main.py Hikvision 2025-01-11T10:15:00")
    print("Or use interactive mode and select option 4")
    
    print("\n" + "="*50)
    print("Key Features:")
    print("- All cameras connect by default")
    print("- Shows all cameras simultaneously")
    print("- Timestamp-based playback from DVR hard disk")
    print("- Day highlights functionality")
    print("- Press 'q' in any window to quit all streams")
    print("="*50)

if __name__ == "__main__":
    main()
