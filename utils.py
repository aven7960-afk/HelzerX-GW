from __future__ import annotations

import re
import time
from datetime import datetime, timezone

DURATION_RE = re.compile(r"(?P<value>\d+)\s*(?P<unit>s|m|h|d|w)", re.I)
MULTIPLIERS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

def parse_duration(value: str) -> int:
    value = value.strip().lower()
    matches = list(DURATION_RE.finditer(value))
    if not matches or "".join(m.group(0) for m in matches).replace(" ", "") != value.replace(" ", ""):
        raise ValueError("Use durations like `30m`, `2h`, `3d`, or `1d12h`.")
    seconds = sum(int(m.group("value")) * MULTIPLIERS[m.group("unit")] for m in matches)
    if seconds <= 0:
        raise ValueError("Duration must be greater than zero.")
    return seconds

def discord_timestamp(unix: int, style: str = "R") -> str:
    return f"<t:{unix}:{style}>"

def now_ts() -> int:
    return int(time.time())

def utc_dt(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)
