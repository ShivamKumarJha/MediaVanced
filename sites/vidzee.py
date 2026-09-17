import base64
import json
import requests

KEY: bytes = bytes.fromhex(
    "e4f9b27d8c1a6ef5037db98ac54e21f0b9d6c3a781fe42ad65c0e9b73f148a2d"
)
DISCARD: int = 2048


def ksa(key: bytes = KEY) -> bytearray:
    assert len(key) == 32, "the wasm hard-codes `i % 32`"
    s = bytearray(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) & 0xFF
        s[i], s[j] = s[j], s[i]
    return s


def keystream(length: int, discard: int = DISCARD) -> bytes:
    """First `length` output bytes of RC4-drop-N under the embedded key."""
    s = ksa()
    i = j = 0

    # warm-up: advance the state `discard` times, throwing the output away
    for _ in range(discard):
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        s[i], s[j] = s[j], s[i]

    out = bytearray()
    for _ in range(length):
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        s[i], s[j] = s[j], s[i]
        out.append(s[(s[i] + s[j]) & 0xFF])   # classic RC4 output byte
    return bytes(out)


def decrypt(ciphertext: bytes) -> bytes:
    ks = keystream(len(ciphertext))
    return bytes(c ^ k for c, k in zip(ciphertext, ks))


url = "https://core.vidzee.wtf/streams/movie/155"

params = {
    "s": "v4:Hindi",
    "e": "1"
}

headers = {
    "Origin": "https://player.vidzee.wtf",
    "Referer": "https://player.vidzee.wtf/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    arg = data.get("c")
    raw = base64.b64decode(arg)
    out = decrypt(raw)
    text = out.decode("utf-8", "replace")
    try:
        print(json.dumps(json.loads(text), indent=2)[:4000])
    except json.JSONDecodeError:
        print(text[:4000])
else:
    print(f"Failed with status code {response.status_code}:")
    print(response.text)
