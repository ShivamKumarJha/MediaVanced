import os
import re
import json
import time
import base64
import requests

from Crypto.Cipher import AES

origin = "https://babastream.top"
anilist_id = 1735
episode_number = 10
embed_url = f"{origin}/embed/{anilist_id}/{episode_number}/sub"

session = requests.Session()

headers = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}

# Fetch embed page
html = session.get(embed_url, headers=headers).text

# Extract CFG
cfg = json.loads(
    re.search(r"var\s+CFG\s*=\s*(\{.*?\});", html, re.S).group(1)
)

sid = cfg["sid"]
pk = base64.b64decode(cfg["pk"])

# Build encrypted payload
iv = os.urandom(12)

plaintext = json.dumps(
    {"ts": int(time.time() * 1000)},
    separators=(",", ":")
).encode()

cipher = AES.new(pk, AES.MODE_GCM, nonce=iv)
ciphertext, tag = cipher.encrypt_and_digest(plaintext)

encrypted = base64.b64encode(iv + ciphertext + tag).decode()

body = {
    "s": sid,
    "d": encrypted,
}

api_headers = {
    **headers,
    "Origin": origin,
    "Referer": embed_url,
}

# ---------------- Resolve ----------------

resp = session.post(
    f"{origin}/api/resolve",
    json=body,
    headers=api_headers,
).json()

raw = base64.b64decode(resp["d"])

iv = raw[:12]
ciphertext = raw[12:-16]
tag = raw[-16:]

cipher = AES.new(pk, AES.MODE_GCM, nonce=iv)
plaintext = cipher.decrypt_and_verify(ciphertext, tag)

resolve = json.loads(plaintext.decode())

print("Resolve:")
print(json.dumps(resolve, indent=2))

# ---------------- Vidara ----------------

resp = session.post(
    f"{origin}/api/vidara",
    json=body,
    headers=api_headers,
).json()

raw = base64.b64decode(resp["d"])

iv = raw[:12]
ciphertext = raw[12:-16]
tag = raw[-16:]

cipher = AES.new(pk, AES.MODE_GCM, nonce=iv)
plaintext = cipher.decrypt_and_verify(ciphertext, tag)

vidara = json.loads(plaintext.decode())

print("\nVidara:")
print(json.dumps(vidara, indent=2))
