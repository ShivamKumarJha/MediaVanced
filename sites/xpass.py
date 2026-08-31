import base64
import hashlib
import json
import re
import requests
from urllib.parse import urlparse, parse_qs

BASE_URL = "https://play.xpass.top"
BUILD = "spv3-build-1787821613-50e5fc97c9dce367"
EMBED_URL = f"{BASE_URL}/e/movie/278"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://play.xpass.top/",
}

def get_data_url():
    try:
        response = requests.get(EMBED_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()

        # Regex to extract the string inside var dataUrl="..."
        match = re.search(r'var\s+dataUrl\s*=\s*["\']([^"\']+)["\']', response.text)

        if match:
            data_url_path = match.group(1)
            full_data_url = f"https://play.xpass.top{data_url_path}"

            print(f"[+] Relative Path: {data_url_path}")
            print(f"[+] Full URL:       {full_data_url}")
            return full_data_url
        else:
            print("[-] Could not find 'dataUrl' pattern in the response HTML.")
            return None

    except requests.RequestException as e:
        print(f"[-] Request failed: {e}")
        return None

def derive_key(data_url: str) -> bytes:
    parsed = urlparse(data_url)

    pathname = parsed.path

    params = parse_qs(parsed.query)
    token = params.get("token", [None])[0]

    if not pathname.startswith("/data/"):
        raise ValueError(f"Invalid pathname: {pathname}")

    if token is None:
        raise ValueError("Missing token")

    parts = token.split(".")

    if len(parts) != 2:
        raise ValueError("Token must contain exactly one '.'")

    if len(parts[1]) != 64:
        raise ValueError("Token suffix must be 64 hex characters")

    try:
        bytes.fromhex(parts[1])
    except ValueError:
        raise ValueError("Token suffix is not hexadecimal")

    material = (
        "spv3-data-response|"
        + BUILD
        + "|"
        + pathname
        + "|"
        + token
    )

    print("\n[+] Key derivation material:")
    print(material)

    key = hashlib.sha256(material.encode("utf-8")).digest()

    print("\n[+] AES-256 key:")
    print(key.hex())

    return key


def decrypt_response(response_text: str, key: bytes):
    # Equivalent to the JS:
    #
    # value.replace(/-/g, "+").replace(/_/g, "/")
    # + Base64 padding

    value = response_text.strip()

    value += "=" * ((4 - len(value) % 4) % 4)

    encrypted = base64.urlsafe_b64decode(value)

    print(f"\n[+] Encrypted payload: {len(encrypted)} bytes")

    if len(encrypted) <= 12:
        raise ValueError("Encrypted response is too short")

    iv = encrypted[:12]
    ciphertext_and_tag = encrypted[12:]

    print("[+] IV:")
    print(iv.hex())

    print(f"[+] Ciphertext + GCM tag: {len(ciphertext_and_tag)} bytes")

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    aes = AESGCM(key)

    plaintext = aes.decrypt(
        iv,
        ciphertext_and_tag,
        None,
    )

    print(f"[+] Plaintext: {len(plaintext)} bytes")

    return json.loads(plaintext.decode("utf-8"))


def main():
    data_url = get_data_url()
    key = derive_key(data_url)

    print("\n[+] Requesting:")
    print(data_url)

    response = requests.get(
        data_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/139.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
        },
        timeout=20,
    )

    print(f"\n[+] HTTP {response.status_code}")

    if not response.ok:
        print(response.text[:1000])
        response.raise_for_status()

    decrypted = decrypt_response(response.text, key)

    print("\n========== DECRYPTED DATA ==========")
    print(json.dumps(decrypted, indent=2, ensure_ascii=False))

    server = decrypted[0]
    server_url = server.get("url")
    playlist_url = f"{BASE_URL}{server_url}"
    print(f"\n[+] Playlist URL {playlist_url}")

    playlist = requests.get(
        playlist_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/139.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
        },
        timeout=20,
    ).json()

    print("\n========== Playlist response ==========")
    print(json.dumps(playlist, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
