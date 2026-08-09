import base64
import json
import requests

headers = {
    "accept": "*/*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "origin": "https://player.videasy.to",
    "priority": "u=1, i",
    "referer": "https://player.videasy.to/",
    "sec-ch-ua": '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
}

# 1. Get seed
seed_url = "https://api.speedracelight.com/seed"

seed_response = requests.get(
    seed_url,
    params={"mediaId": 299534},
    headers=headers,
)

seed_response.raise_for_status()

seed_data = seed_response.json()
seed = seed_data["seed"]

print("Seed:", seed)
print("TTL:", seed_data.get("ttlMs"))


# 2. Get sources
sources_url = "https://api.speedracelight.com/cdn/sources-with-title"

params = {
    "title": "Avengers: Endgame",
    "mediaType": "movie",
    "year": 2019,
    "episodeId": 1,
    "seasonId": 1,
    "tmdbId": 299534,
    "imdbId": "tt4154796",
    "enc": 2,
    "seed": seed,
}

sources_response = requests.get(
    sources_url,
    params=params,
    headers=headers,
)

sources_response.raise_for_status()

print("Response:")
print(sources_response.text)

# ------------------------------------------------------------
# Hardcoded inputs
# ------------------------------------------------------------

ENCRYPTED = sources_response.text
SEED = seed
MEDIA_ID = 299534


MASK32 = 0xFFFFFFFF

# The constants called `f` in the JavaScript.
F = [
    1116352408, 1899447441, 3049323471, 3921009573,
    961987163, 1508970993, 2453635748, 2870763221,
    3624381080, 310598401, 607225278, 1426881987,
    1925078388, 2162078206, 2614888103, 3248222580,
]


# ------------------------------------------------------------
# JavaScript-compatible 32-bit operations
# ------------------------------------------------------------

def imul(a, b):
    """Equivalent to JavaScript Math.imul(a, b), keeping low 32 bits."""
    return (a * b) & MASK32


def rotl(value, bits):
    """32-bit left rotate."""
    value &= MASK32
    bits &= 31

    if bits == 0:
        return value

    return ((value << bits) | (value >> (32 - bits))) & MASK32


def mix(value):
    """
    JavaScript function:

        w(e) {
            e >>>= 0
            e ^= e >>> 16
            e = Math.imul(e, 2246822507) >>> 0
            e ^= e >>> 13
            e = Math.imul(e, 3266489909) >>> 0
            e ^= e >>> 16
            return e >>> 0
        }
    """

    value &= MASK32

    value ^= value >> 16
    value = imul(value, 2246822507)

    value ^= value >> 13
    value = imul(value, 3266489909)

    value ^= value >> 16

    return value & MASK32


# ------------------------------------------------------------
# Initial state generation
# ------------------------------------------------------------

def initialize(seed, media_id):
    """
    Equivalent to the inner:

        (function(e, t) { ... })(seed, mediaId)

    from the JavaScript.
    """

    # JavaScript starts with:
    #
    # let t = 2166136261
    #
    # followed by:
    #
    # t = Math.imul(t ^ charCode, 16777619)

    h = 2166136261

    for char in seed:
        h = imul(h ^ ord(char), 16777619)

    h = mix(h)

    # Equivalent to:
    #
    # w(
    #   fnv(seed) ^
    #   w((mediaId >>> 0) ^ 2654435769)
    # )

    accumulator = mix(
        h ^ mix((media_id & MASK32) ^ 2654435769)
    )

    # JavaScript's:
    #
    # let S = Array(61)
    #
    # is important. Initially, these are HOLES.
    #
    # Python therefore tracks whether a slot exists separately.

    state = [0] * 61
    present = [False] * 61

    for i in range(8):

        # b(i) is always true because i * (i + 1)
        # is always even.

        position = accumulator % 61

        accumulator = rotl(
            accumulator + 2654435769,
            7 + (7 & i)
        )

        state[position] = (
            accumulator ^ mix(accumulator)
        ) & MASK32

        present[position] = True

        accumulator = mix(
            accumulator + position
        )

    accumulator = mix(
        2779096485 ^ accumulator
    )

    return state, present, accumulator


# ------------------------------------------------------------
# Generate one 32-bit keystream word
# ------------------------------------------------------------

def generate_word(state, present, accumulator, counter):

    # JavaScript:
    #
    # let n = o % 61
    n = accumulator % 61

    # JavaScript:
    #
    # let i = 0 - Number(n in r)
    #
    # `n in r` is TRUE only if that array slot exists.
    #
    # This is why `present[]` matters.

    flag = MASK32 if present[n] else 0

    # JavaScript:
    #
    # let d = r[n] >>> 0
    #
    # Reading an uninitialized array slot gives undefined,
    # which becomes 0 under >>> 0.

    d = state[n] if present[n] else 0

    a = (
        d ^ imul(2654435769, counter + 1)
    ) & MASK32

    # Equivalent to:
    #
    # l =
    #   (
    #     (o ^ a) |
    #     (o & a & i)
    #   ) >>> 0

    l = (
        (accumulator ^ a) |
        (accumulator & a & flag)
    ) & MASK32

    # Equivalent to:
    #
    # l =
    #   v(l + o, 31 & n) ^
    #   v(o, 31 & Math.imul(n, 7))

    l = (
        rotl(l + accumulator, n) ^
        rotl(
            accumulator,
            imul(n, 7)
        )
    ) & MASK32

    # Update accumulator.

    accumulator = mix(
        l + 2654435769
    )

    # Store the new value into the selected slot.

    state[n] = accumulator
    present[n] = True

    return accumulator


# ------------------------------------------------------------
# Decrypt
# ------------------------------------------------------------

def decrypt(encrypted, seed, media_id):

    # Convert Base64URL → normal Base64.

    encrypted = encrypted.replace("-", "+")
    encrypted = encrypted.replace("_", "/")

    # Restore Base64 padding.

    encrypted += "=" * (
        (-len(encrypted)) % 4
    )

    ciphertext = base64.b64decode(encrypted)

    state, present, accumulator = initialize(
        seed,
        media_id
    )

    plaintext = bytearray(len(ciphertext))

    offset = 0
    counter = 0

    while offset < len(ciphertext):

        # Generate 32 bits / 4 bytes of keystream.

        word = generate_word(
            state,
            present,
            accumulator,
            counter
        )

        accumulator = word

        # JavaScript emits the word little-endian:
        #
        # r[e++] = 255 & t
        # r[e++] = (t >>> 8) & 255
        # r[e++] = (t >>> 16) & 255
        # r[e++] = (t >>> 24) & 255

        for shift in (0, 8, 16, 24):

            if offset >= len(ciphertext):
                break

            keystream_byte = (
                word >> shift
            ) & 0xFF

            plaintext[offset] = (
                ciphertext[offset]
                ^ keystream_byte
            )

            offset += 1

        counter += 1

    return bytes(plaintext)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

plaintext = decrypt(
    ENCRYPTED,
    SEED,
    MEDIA_ID
)

print("First 4 bytes:", plaintext[:4])
print("Header:", plaintext[:4].decode("ascii"))

if plaintext[:4] != b"mvm1":
    raise RuntimeError(
        "Decryption failed: bad seed/media ID/ciphertext"
    )

# Remove the 4-byte "mvm1" header.

payload = plaintext[4:].decode("utf-8")

print()
print("Decrypted payload:")
print(payload)

# It should be JSON.

data = json.loads(payload)

print()
print("Sources:", len(data.get("sources", [])))
print("Subtitles:", len(data.get("subtitles", [])))
print(f"Referer: {headers['referer']}\n")
