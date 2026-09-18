#!/usr/bin/env python3
import base64
import time
import requests

TMDB_ID = 108978
SEASON = 4
EPISODE = 1

BASE_URL = "https://spencerdevs.xyz/api/fbi-honeypot/tv"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
    ),
}
SERVERS = (1, 2, 3, 4, 5)
SERVER_NAMES = {1: "DCloud", 2: "TCloud", 3: "T3", 4: "TBackup", 5: "IPCloud"}

def make_token(minute: int) -> str:
    value = TMDB_ID * (minute**3 + minute**2 + minute)
    return base64.b64encode(str(value).encode("utf-8")).decode("ascii")

def resolve_stream() -> str | None:
    now_minute = int(time.time() * 1000) // 60_000
    offsets = [0, -1, 1, -2, 2]  # Tolerance for clock skew

    session = requests.Session()
    session.headers.update(HEADERS)

    for server in range(1, 6):
        for offset in offsets:
            token = make_token(now_minute + offset)
            url = f"{BASE_URL}/{token}/{SEASON}/{EPISODE}/{server}"
            try:
                resp = session.get(url, timeout=9.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict):
                        for val in data.values():
                            if isinstance(val, str) and ".m3u8" in val and "https://" in val:
                                return val
            except (requests.RequestException, ValueError):
                continue
    return None

if __name__ == "__main__":
    stream_url = resolve_stream()
    if stream_url:
        print(stream_url)
    else:
        print("Failed to resolve stream URL.")
