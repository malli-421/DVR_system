from dvr_api import DVRManager, MultiCameraPlayer
from datetime import datetime
import sys

# Example: timestamps from your model
model_timestamps = ["2025-01-11T10:15:00", "2025-01-11T10:20:00"]

def parse_timestamp(timestamp_str):
    """Parse timestamp string to datetime object"""
    try:
        # Handle ISO format with or without Z
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        return datetime.fromisoformat(timestamp_str)
    except ValueError:
        print(f"Invalid timestamp format: {timestamp_str}")
        print("Expected format: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM:SSZ")
        return None

def show_menu():
    print("\n" + "="*50)
    print("DVR Multi-Camera System")
    print("="*50)
    print("1. Play live stream from all cameras")
    print("2. Play recorded footage from all cameras at specific timestamp")
    print("3. Exit")
    print("="*50)

if __name__ == "__main__":
    manager = DVRManager("dvr_config.json")
    multi_player = MultiCameraPlayer(manager)
    
    print("Available DVRs:", manager.list_dvrs())
    multi_player.setup_cameras()
    
    # Command line mode
    if len(sys.argv) > 1:
        if sys.argv[1] == "live":
            print("Playing live stream from all cameras (grid)...")
            multi_player.play_all_cameras_grid()
        elif sys.argv[1] == "timestamp" and len(sys.argv) > 2:
            timestamp_str = sys.argv[2]
            start_time = parse_timestamp(timestamp_str)
            if start_time:
                print(f"Playing recorded footage from all cameras at {start_time} (grid)...")
                multi_player.play_all_cameras_grid(start_time)
        elif sys.argv[1] == "highlights" and len(sys.argv) > 2:
            date_str = sys.argv[2]
            multi_player.show_day_highlights(date_str)
        else:
            # Legacy single camera mode
            dvr_name = sys.argv[1]
            dvr = manager.get_dvr(dvr_name)
            if not dvr:
                print("DVR not found!")
                sys.exit(1)
            
            start_time = None
            if len(sys.argv) > 2:
                timestamp_str = sys.argv[2]
                start_time = parse_timestamp(timestamp_str)
                if start_time is None:
                    sys.exit(1)
            
            if start_time:
                print(f"Playing recorded footage for {dvr.name} from {start_time}")
            else:
                print(f"Playing live stream for {dvr.name}")
            
            dvr.play_stream(start_time)
    else:
        # Interactive mode
        while True:
            show_menu()
            choice = input("Enter your choice (1-3): ").strip()
            
            if choice == "1":
                print("Playing live stream from all cameras (grid)...")
                multi_player.play_all_cameras_grid()
                
            elif choice == "2":
                print("\nEnter timestamp for playback:")
                print("Format: YYYY-MM-DDTHH:MM:SS (e.g., 2025-01-11T10:15:00)")
                timestamp_input = input("Timestamp: ").strip()
                
                if timestamp_input:
                    start_time = parse_timestamp(timestamp_input)
                    if start_time:
                        print(f"Playing recorded footage from all cameras at {start_time} (grid)...")
                        multi_player.play_all_cameras_grid(start_time)
                else:
                    print("No timestamp provided!")
                    
            elif choice == "3":
                print("Exiting...")
                break
                
            else:
                print("Invalid choice! Please select 1-3.")
