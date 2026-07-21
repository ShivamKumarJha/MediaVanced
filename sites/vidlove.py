import base64
import hashlib
import json
import random
import requests
from Crypto.Cipher import AES
from dataclasses import dataclass
from typing import List, Optional


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

SECRET = "Sn00pD0g#RESP_B4SE_K3y_2026!"
API = "https://momlover.notyourtype.dad"
SERVERS = [
    {"label": "Fifa", "slug": "fabric", "country": "Original", "quality": "HD"},
    {"label": "Dark", "slug": "moviebox", "country": "Original", "quality": "4K"},
    {"label": "4k", "slug": "4K", "country": "Original", "quality": "4K"},
    {"label": "Png", "slug": "png", "country": "Original", "quality": "HD"},
    {"label": "Feta", "slug": "cline", "country": "Original", "quality": "HD"},
    {"label": "Youtube", "slug": "flax", "country": "Original", "quality": "HD"},
    {"label": "Roko", "slug": "Tulnex1", "country": "Original", "quality": "HD"},
    {"label": "Yulnex", "slug": "zebra", "country": "Original", "quality": "HD"},
]


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------

@dataclass
class Source:
    url: str
    quality: str
    type: str


@dataclass
class Response:
    title: str
    sources: List[Source]


# ------------------------------------------------------------------
# Crypto
# ------------------------------------------------------------------

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def decrypt_response(payload: str, secret: str) -> dict:
    raw = base64.b64decode(payload)

    salt = raw[:16]
    iv = raw[16:28]
    ciphertext = raw[28:-16]
    tag = raw[-16:]

    key = sha256(secret.encode() + salt)

    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)

    return json.loads(plaintext.decode())


# ------------------------------------------------------------------
# API
# ------------------------------------------------------------------

def generate_token(referrer: str) -> str:
    headers = {
        "Referer": referrer,
    }

    r = requests.post(
        f"{API}/auth/generate-token",
        headers=headers,
        json={"clientData": {}},
    )
    r.raise_for_status()

    return r.json()["token"]


def build_media_url(
    media_id: str,
    is_movie: bool,
    server: dict,
    season: Optional[str] = None,
    episode: Optional[str] = None,
) -> str:

    url = f"{API}/{server['slug']}"

    if is_movie:
        url += f"/movie/{media_id}"
    else:
        url += f"/tv/{media_id}/{season}/{episode}"

    return url


def fetch_sources(
    url: str,
    referrer: str,
) -> dict:

    token = generate_token(referrer)

    headers = {
        "Referer": referrer,
        "x-request-token": token,
        "x-response-encryption": "aes-gcm",
    }

    r = requests.get(url, headers=headers)
    r.raise_for_status()

    encrypted = r.json()

    return decrypt_response(
        encrypted["payload"],
        SECRET,
    )


# ------------------------------------------------------------------
# URL parsing
# ------------------------------------------------------------------

def parse_vidlove_url(url: str):
    if "/movie/" in url:
        media_id = url.rstrip("/").split("/")[-1]

        return {
            "is_movie": True,
            "id": media_id,
            "season": None,
            "episode": None,
        }

    part = url.split("/tv/")[1]

    pieces = part.strip("/").split("/")

    return {
        "is_movie": False,
        "id": pieces[0],
        "season": pieces[1],
        "episode": pieces[2],
    }


# ------------------------------------------------------------------
# Main extractor
# ------------------------------------------------------------------

def extract(url: str):
    server = SERVERS[0]

    info = parse_vidlove_url(url)

    api_url = build_media_url(
        media_id=info["id"],
        is_movie=info["is_movie"],
        season=info["season"],
        episode=info["episode"],
        server=server,
    )

    response = fetch_sources(api_url, referrer=url)

    media = []

    for source in response["sources"]:
        media.append({
            "url": source["url"],
            "quality": source["quality"],
            "type": source["type"],
            "server": server["label"],
            "description": (
                f"{server['label']} - "
                f"{server['country']} - "
                f"{server['quality']} - "
                f"{source['quality']}"
            ),
        })

    return media


# ------------------------------------------------------------------
# Example
# ------------------------------------------------------------------

if __name__ == "__main__":
    test = "https://player.vidlove.cc/embed/tv/1396/1/1" #"https://player.vidlove.cc/embed/movie/155"

    for item in extract(test):
        print(item)
