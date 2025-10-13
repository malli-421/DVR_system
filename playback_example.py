#!/usr/bin/env python3
"""
Example script showing how to play recorded footage from DVR at specific timestamps
"""

from dvr_api import DVRManager
from datetime import datetime, timedelta

def main():
    # Initialize DVR manager
    manager = DVRManager("dvr_config.json")
    
    print("Available DVRs:", manager.list_dvrs())
    
    # Get the first DVR (Hikvision)
    dvr = manager.get_dvr("Hikvision")
    if not dvr:
        print("Hikvision DVR not found!")
        return
    
    print(f"Using DVR: {dvr.name} at IP: {dvr.ip}")
    
    # Example timestamps - you can modify these
    example_timestamps = [
        "2025-01-11T09:00:00",  # 9:00 AM today
        "2025-01-11T10:30:00",  # 10:30 AM today
        "2025-01-11T14:15:00",  # 2:15 PM today
    ]
    
    print("\nExample timestamps for playback:")
    for i, ts in enumerate(example_timestamps, 1):
        print(f"{i}. {ts}")
    
    print("\nChoose an option:")
    print("1. Play live stream")
    print("2. Play from specific timestamp")
    print("3. Play from example timestamps")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        print("Playing live stream...")
        dvr.play_stream()
        
    elif choice == "2":
        timestamp_str = input("Enter timestamp (YYYY-MM-DDTHH:MM:SS): ").strip()
        try:
            start_time = datetime.fromisoformat(timestamp_str)
            print(f"Playing recorded footage from {start_time}...")
            dvr.play_stream(start_time)
        except ValueError:
            print("Invalid timestamp format!")
            
    elif choice == "3":
        ts_choice = input("Enter example number (1-3): ").strip()
        try:
            ts_index = int(ts_choice) - 1
            if 0 <= ts_index < len(example_timestamps):
                timestamp_str = example_timestamps[ts_index]
                start_time = datetime.fromisoformat(timestamp_str)
                print(f"Playing recorded footage from {start_time}...")
                dvr.play_stream(start_time)
            else:
                print("Invalid choice!")
        except ValueError:
            print("Invalid choice!")
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()
