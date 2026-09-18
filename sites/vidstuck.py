#!/usr/bin/env python3
import base64
import hashlib
import requests
from urllib.parse import urlencode
from Crypto.Cipher import AES

# --------------------------------------------------------------------------- #
# Hardcoded Parameters & Configuration
# --------------------------------------------------------------------------- #
TMDB_ID = 108978
MEDIA_TYPE = "tv"
SEASON = 4
EPISODE = 4
SERVER = "andromeda"  # Default server from list

BASE = "https://vidstuck.xyz"
TMDB_API_KEY = "06f10fc8741a672af455421c239a1ffc"
TMDB_BASE = "https://api.themoviedb.org/3"

AES_PASSPHRASE = b"7f4c9e2a81d63b05c4f7a9e8126d3b50e1a8c7f23d9465ab0c6e9f1d4a7b832c"

FIELD_MAP = {
    "id": "a7f39c821d604e5b9c7143f36e1547b",
    "ts": "61d9a5274c8e3b29af75d6384c291e6",
    "token": "c492f7a183d6502b1e7436c538a716d",
    "title": "5e28c9147a306d531e829f3674b392a1",
    "year": "b731e6c94f082a169d725f8341c306e",
    "season": "d8427b59ce30684a2f957c3613e85b",
    "episode": "91c6e4a728bd503d1f785c92346b713d",
    "imdbId": "f35a8c19d674b3265e871c4933a725f",
    "path": "6b491e7253ad8f14d392e7561a9384c",
    "mediaType": "c285f91ab306d281e947a35632e816b",
    "date": "e164932c50216ad739e5814b3027",
    "latestDate": "e16932c54356416ad739e5814b3027",
}

SERVERS = [
    {
        "name": "Andromeda",
        "status": "queue",
        "server": "andromeda",
        "desc": "Smooth Playback & HD",
        "dubSupport": False,
    },
    {
        "name": "Centaurus",
        "status": "queue",
        "server": "centaurus",
        "desc": "Multi Audio Support",
        "dubSupport": True,
    },
    {
        "name": "Atlas",
        "status": "queue",
        "server": "atlas",
        "desc": "Alternative",
        "dubSupport": False,
    },
    {
        "name": "Milky Way",
        "status": "queue",
        "server": "milkyway",
        "desc": "Alternative",
        "dubSupport": False,
    },
]

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": BASE,
    "Referer": f"{BASE}/player/{MEDIA_TYPE}/{TMDB_ID}",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

# --------------------------------------------------------------------------- #
# Decryption Logic
# --------------------------------------------------------------------------- #
def evp_bytes_to_key(password: bytes, salt: bytes, key_len: int = 32, iv_len: int = 16):
    material, prev = b"", b""
    while len(material) < key_len + iv_len:
        prev = hashlib.md5(prev + password + salt).digest()
        material += prev
    return material[:key_len], material[key_len : key_len + iv_len]


def decrypt_link(blob: str) -> str:
    raw = base64.b64decode(blob)
    salt, ct = (raw[8:16], raw[16:]) if raw.startswith(b"Salted__") else (b"", raw)
    key, iv = evp_bytes_to_key(AES_PASSPHRASE, salt)

    cipher = AES.new(key, AES.MODE_CBC, iv)
    pt = cipher.decrypt(ct)

    pad = pt[-1]
    return pt[:-pad].decode("utf-8", "replace")


# --------------------------------------------------------------------------- #
# Resolve Stream
# --------------------------------------------------------------------------- #
def main():
    sess = requests.Session()
    print("[INFO] Fetching metadata and resolving stream...")

    # 1. Fetch TMDB Metadata
    details = sess.get(f"{TMDB_BASE}/tv/{TMDB_ID}", params={"api_key": TMDB_API_KEY}).json()
    try:
        ext = sess.get(f"{TMDB_BASE}/tv/{TMDB_ID}/external_ids", params={"api_key": TMDB_API_KEY}).json()
        imdb_id = ext.get("imdb_id", "")
    except Exception:
        imdb_id = ""

    title = details.get("name") or details.get("original_name", "")
    date = details.get("first_air_date", "")
    latest_date = details.get("last_air_date", "")

    # 2. Handshake / Token POST
    token_body = {
        FIELD_MAP["id"]: str(TMDB_ID),
        FIELD_MAP["mediaType"]: MEDIA_TYPE,
        FIELD_MAP["path"]: SERVER,
        FIELD_MAP["season"]: str(SEASON),
        FIELD_MAP["episode"]: str(EPISODE),
    }
    tok_res = sess.post(f"{BASE}/backend/npminstall", json=token_body, headers=HEADERS).json()

    # 3. Request Sources
    query = {
        FIELD_MAP["id"]: str(TMDB_ID),
        FIELD_MAP["path"]: SERVER,
        FIELD_MAP["mediaType"]: MEDIA_TYPE,
        FIELD_MAP["ts"]: str(tok_res["ts"]),
        FIELD_MAP["token"]: tok_res["token"],
        FIELD_MAP["title"]: title,
        FIELD_MAP["year"]: date[:4] if date else "",
        FIELD_MAP["date"]: date,
        FIELD_MAP["season"]: str(SEASON),
        FIELD_MAP["episode"]: str(EPISODE),
    }
    if latest_date:
        query[FIELD_MAP["latestDate"]] = latest_date
    if imdb_id:
        query[FIELD_MAP["imdbId"]] = imdb_id

    sources = sess.get(f"{BASE}/backend/servers/{SERVER}?{urlencode(query)}", headers=HEADERS).json()

    # 4. Decrypt and Print Links
    for item in sources.get("links", []):
        if "link" in item:
            decrypted = decrypt_link(item['link'])

            # Format base URL if link is relative
            if decrypted.startswith("/"):
                final_link = f"{BASE}{decrypted}"
            else:
                final_link = decrypted

            res = item.get('resolution', 'Unknown')
            print(f"[SUCCESS] Decrypted Link ({res}): {final_link}")

    # 5. Print Origin and Referer
    print("\n[INFO] Request Configuration:")
    print(f"[INFO] Origin:  {HEADERS['Origin']}")
    print(f"[INFO] Referer: {HEADERS['Referer']}")

if __name__ == "__main__":
    main()
