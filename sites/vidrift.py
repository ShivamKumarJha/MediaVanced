import requests
import time
import hashlib

timestamp = int(time.time())
salt = "vr_sec_kd8s_7f92n3m1p4q0"
hash_value = 0
hash_input = f"{timestamp}:{salt}"

for char in hash_input:
	hash_value = ((hash_value << 5) - hash_value) + ord(char)
	hash_value = hash_value & 0xFFFFFFFF

hash_str = format(abs(hash_value), 'x').zfill(8)
token = f"{timestamp}-{hash_str}"
tmdb_id = 278
source="embed"
url = f"https://vidrift.in/api/source/movie/{tmdb_id}"
params = {
    "source": source,
    "_t": token
}
headers = {
    "Referer": f"https://vidrift.in/embed/movie/{tmdb_id}",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}
response = requests.get(url, params=params, headers=headers)
data = response.json()

if data.get("success"):
    print(f"✅ Stream found for: {data.get('tmdbId')}")
    print(f"   Server: {data.get('source')}")
    print(f"   Type: {data.get('sourceType')}")

    for stream in data.get("streams", []):
        print(f"\n   Stream {stream.get('index')}:")
        print(f"   • Direct URL: {stream.get('url')}")
        print(f"   • Proxy URL: {stream.get('proxyUrl', 'N/A')}")

    print(f"\n   Available servers: {', '.join([s['label'] for s in data.get('servers', [])])}")
else:
    print(f"❌ Failed: {data}")
