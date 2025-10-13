from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
import re

@dataclass
class DVRInfo:
    name: str
    ip: str
    username: str
    password: str
    rtsp_url: str

class DVRBrand:
    def expand_channels(self, dvr: DVRInfo, max_channels: int = 16, use_substream: bool = True) -> List[DVRInfo]:
        raise NotImplementedError

    def build_live_url(self, dvr: DVRInfo) -> str:
        raise NotImplementedError

    def build_playback_url(self, dvr: DVRInfo, start_time: datetime, duration: timedelta) -> str:
        raise NotImplementedError
