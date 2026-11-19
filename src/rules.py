"""The distance rules from the Quest, in one place."""
from zoneinfo import ZoneInfo

PING_INTERVAL_S = 10
MAX_OFFROAD_M = 100        # ping more than 100 m off the road path is GPS noise
MAX_SPEED_KMH = 150        # ping implying more than 150 km/h is GPS noise
LOCAL_TZ = ZoneInfo("Asia/Tokyo")  # UTC+9, no daylight saving; daily report cut at 00:00 local
# Zone rule interpretation (written down in intent.md):
# a segment between two consecutive valid pings counts only if BOTH pings are inside the zone.
