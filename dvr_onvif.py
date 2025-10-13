from onvif import ONVIFCamera
import datetime
import cv2

class DVR_ONVIF:
    def __init__(self, ip, port, username, password):
        self.camera = ONVIFCamera(ip, port, username, password)
        self.media_service = self.camera.create_media_service()
        self.replay_service = self.camera.create_replay_service()
        self.search_service = self.camera.create_search_service()

    def get_playback_uri(self, channel=1, start_time=None):
        # This is a simplified example. Actual ONVIF search may require more parameters.
        # start_time should be a datetime object
        if start_time is None:
            start_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        # Search for recordings
        # You may need to use search_service.FindRecordings and search_service.GetRecordingInformation
        # For demo, we use media_service.GetStreamUri (usually for live)
        profiles = self.media_service.GetProfiles()
        profile_token = profiles[channel-1].token
        stream_setup = {
            'Stream': 'RTP-Unicast',
            'Transport': {'Protocol': 'RTSP'}
        }
        uri = self.media_service.GetStreamUri({'StreamSetup': stream_setup, 'ProfileToken': profile_token})
        return uri.Uri

    def play_from_timestamp(self, start_time):
        uri = self.get_playback_uri(start_time=start_time)
        print(f"Playback URI: {uri}")
        cap = cv2.VideoCapture(uri)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow("DVR Playback", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()


# Example usage: List number of cameras (profiles)
if __name__ == "__main__":
    ip = "172.16.0.95"
    port = 80
    username = "admin"
    password = "SemiCore@2025"
    dvr = DVR_ONVIF(ip, port, username, password)
    profiles = dvr.media_service.GetProfiles()
    print(f"Number of cameras (profiles) connected: {len(profiles)}")
    for idx, profile in enumerate(profiles, 1):
        print(f"Camera {idx}: Profile Name = {profile.Name}, Token = {profile.token}")

    # Play from 10:00 AM today (optional)
    # start_time = datetime.datetime.combine(datetime.date.today(), datetime.time(10, 0, 0))
    # dvr.play_from_timestamp(start_time)
