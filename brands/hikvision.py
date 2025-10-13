from datetime import datetime, timedelta
from typing import List
import re
try:
    from .base import DVRBrand, DVRInfo
except ImportError:
    # Fallback when executed directly without package context
    from brands.base import DVRBrand, DVRInfo

class HikvisionBrand(DVRBrand):
    def expand_channels(self, dvr: DVRInfo, max_channels: int = 16, use_substream: bool = True) -> List[DVRInfo]:
        m = re.search(r"Streaming/Channels/(\d+)", dvr.rtsp_url)
        if not m:
            return [dvr]
        chan_count = max_channels
        chan_ids = [(i * 100 + (2 if use_substream else 1)) for i in range(1, chan_count + 1)]
        out: List[DVRInfo] = []
        for cid in chan_ids:
            url = re.sub(r"Streaming/Channels/\d+", f"Streaming/Channels/{cid}", dvr.rtsp_url)
            out.append(DVRInfo(name=f"{dvr.name}-CH{cid//100}", ip=dvr.ip, username=dvr.username, password=dvr.password, rtsp_url=url))
        return out

    def build_live_url(self, dvr: DVRInfo) -> str:
        return dvr.rtsp_url

    def build_playback_url(self, dvr: DVRInfo, start_time: datetime, duration: timedelta) -> str:
        start = start_time.strftime('%Y%m%dT%H%M%SZ')
        end = (start_time + duration).strftime('%Y%m%dT%H%M%SZ')
        m = re.search(r"Streaming/Channels/(\d+)", dvr.rtsp_url)
        if not m:
            return dvr.rtsp_url
        chan = m.group(1)
        return re.sub(r"Streaming/Channels/\d+", f"Streaming/tracks/{chan}?starttime={start}&endtime={end}", dvr.rtsp_url)
