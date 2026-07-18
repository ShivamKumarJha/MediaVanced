import re
import requests
import hashlib

API_KEY = "mptv_sk_a8f29c4e7b3d1f"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://mapple.rip/",
    "Origin": "https://mapple.rip",
}


def has_leading_zero_bits(digest, bits):
    full = bits // 8
    rem = bits % 8

    if digest[:full] != b"\x00" * full:
        return False

    if rem:
        mask = 0xff << (8 - rem)
        return (digest[full] & mask) == 0

    return True


def solve_pow(challenge, difficulty):
    nonce = 0

    while True:
        h = hashlib.sha256(
            (challenge + str(nonce)).encode()
        ).digest()

        if has_leading_zero_bits(h, difficulty):
            return str(nonce)

        nonce += 1


def get_stream(movie_id):
    s = requests.Session()
    s.headers.update(HEADERS)

    # Step 1
    html = s.get(
        f"https://mapple.rip/watch/movie/{movie_id}"
    ).text

    token = re.search(
        r'__REQUEST_TOKEN__\s*=\s*"([^"]+)"',
        html
    ).group(1)

    # Step 2
    body = {
        "mediaId": movie_id,
        "mediaType": "movie",
        "requestToken": token,
    }

    r = s.post(
        "https://mapple.rip/api/playback-init",
        json=body,
    ).json()

    # Step 3
    if r.get("requiresPow"):
        powinfo = r["pow"]

        nonce = solve_pow(
            powinfo["challenge"],
            powinfo["difficulty"],
        )

        body["pow"] = {
            "challengeId": powinfo["challengeId"],
            "nonce": nonce,
        }

        r = s.post(
            "https://mapple.rip/api/playback-init",
            json=body,
        ).json()

    stream_token = r["token"]

    params = {
        "mediaId": movie_id,
        "mediaType": "movie",
        "tv_slug": "",
        "source": "mapple",
        "apikey": API_KEY,
        "requestToken": token,
        "token": stream_token,
    }

    r = s.get(
        "https://mapple.rip/api/stream",
        params=params,
    ).json()

    return r["data"]["stream_url"]


if __name__ == "__main__":
    print(get_stream(278))
