#!/usr/bin/env python3

import json
import os
import struct
import requests

from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA256
from Crypto.PublicKey import ECC


# ============================================================================
# Protocol constants
# ============================================================================

HEADER = b"lumen-gate-v2"
VERSION = 2

IV_LEN = 12
TAG_LEN = 16

MIN_CONTEXT = 44
OVERHEAD = 193

N = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551

# Generator point G on P-256
G_POINT = ECC.EccPoint(
    0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296,
    0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5,
    curve="p256",
)

PEER_PUBKEY = bytes.fromhex(
    "045c88a0ae33c683a4872590b04b22f4774a4fe1c6ecf74785c74a919a71207ca9"
    "4f9e6b5a7854c3aa3b44ee46bc444fea694b9f23bcd80f864ecbef48c1ef6e14"
)

LABEL_EPHEM = b"lumen-gate-v2|ephemeral|"
INFO_C2S = b"lumen-gate-v2|c2s"
INFO_S2C = b"lumen-gate-v2|s2c"

AAD_MIDDLE = b"\x00\x01" + bytes([VERSION])


# ============================================================================
# KDF & HKDF
# ============================================================================

def _hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    """RFC 5869 HKDF-Expand using PyCryptodome HMAC-SHA256."""
    out = bytearray()
    t = b""
    counter = 1

    while len(out) < length:
        t = HMAC.new(prk, t + info + bytes([counter]), digestmod=SHA256).digest()
        out.extend(t)
        counter += 1

    return bytes(out[:length])


def derive_keys(context: bytes):
    if len(context) < MIN_CONTEXT:
        raise ValueError("context must be >= 44 bytes")

    # Validate peer key using PyCryptodome's EccPoint (raises ValueError if not on curve)
    peer_x = int.from_bytes(PEER_PUBKEY[1:33], "big")
    peer_y = int.from_bytes(PEER_PUBKEY[33:65], "big")
    try:
        peer_point = ECC.EccPoint(peer_x, peer_y, curve="p256")
    except ValueError as exc:
        raise ValueError("recipient public key is not on P-256") from exc

    # 1. Deterministic ephemeral scalar
    counter = 0
    while True:
        digest = SHA256.new(
            LABEL_EPHEM + context[:32] + struct.pack(">I", counter)
        ).digest()
        sk_e = int.from_bytes(digest, "big")
        if 0 < sk_e < N:
            break
        counter += 1

    # 2. Ephemeral public key
    eph_point = G_POINT * sk_e
    if eph_point.is_point_at_infinity():
        raise ValueError("invalid ephemeral public key")

    eph_pub = (
        b"\x04"
        + int(eph_point.x).to_bytes(32, "big")
        + int(eph_point.y).to_bytes(32, "big")
    )

    # 3. ECDH
    shared_point = peer_point * sk_e
    if shared_point.is_point_at_infinity():
        raise ValueError("ECDH produced point at infinity")

    shared_x = int(shared_point.x).to_bytes(32, "big")

    # 4. Extract & Expand
    prk = HMAC.new(eph_pub, shared_x, digestmod=SHA256).digest()
    k_c2s = _hkdf_expand(prk, INFO_C2S, 32)
    k_s2c = _hkdf_expand(prk, INFO_S2C, 32)

    return sk_e, eph_pub, shared_x, prk, k_c2s, k_s2c


# ============================================================================
# Seal request & Response Decryption
# ============================================================================

def seal_request(plaintext: bytes, context: bytes) -> bytes:
    if len(context) < MIN_CONTEXT:
        raise ValueError("context must be >= 44 bytes")

    _, eph_pub, _, _, k_c2s, k_s2c = derive_keys(context)

    nonce = context[32:44]
    aad = HEADER + AAD_MIDDLE + eph_pub

    # AES-GCM via PyCryptodome
    cipher = AES.new(k_c2s, AES.MODE_GCM, nonce=nonce)
    cipher.update(aad)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    sealed = ciphertext + tag

    frame = (
        k_s2c
        + bytes([VERSION])
        + eph_pub
        + b"\x02"
        + bytes([VERSION])
        + eph_pub
        + nonce
        + sealed
    )

    expected_length = len(plaintext) + OVERHEAD
    if len(frame) != expected_length:
        raise ValueError(f"invalid frame length: {len(frame)} != {expected_length}")

    return frame


def seal_envelope(path: str, payload: dict) -> dict:
    plaintext = json.dumps(
        {"path": path, "payload": payload},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    context = os.urandom(44)
    frame = seal_request(plaintext, context)

    return {
        "responseKey": list(frame[0:32]),
        "keyId": frame[32],
        "ephemeralPublic": list(frame[33:98]),
        "body": list(frame[98:]),
    }


def decrypt_response(response_buffer: bytes | list[int], envelope: dict):
    response = bytes(response_buffer)

    if len(response) < IV_LEN + TAG_LEN:
        raise ValueError("Invalid response buffer length")

    nonce = response[:IV_LEN]
    ciphertext = response[IV_LEN:-TAG_LEN]
    tag = response[-TAG_LEN:]

    try:
        response_key = bytes(envelope["responseKey"])
        key_id = int(envelope["keyId"])
        ephemeral_public = bytes(envelope["ephemeralPublic"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid envelope") from exc

    if len(response_key) != 32 or len(ephemeral_public) != 65 or not 0 <= key_id <= 255:
        raise ValueError("Invalid envelope fields")

    aad = HEADER + bytes([0x00, 0x02, key_id]) + ephemeral_public

    # AES-GCM Decryption via PyCryptodome
    cipher = AES.new(response_key, AES.MODE_GCM, nonce=nonce)
    cipher.update(aad)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)

    return json.loads(plaintext.decode("utf-8"))


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    base_url = "https://cinejoy.pk"
    referrer_url = "https://cinejoy.pk/watch/tv/108978/4/2"
    url_api = "https://api.wing.st"

    path = "/Lisbon/series"
    payload = {
        "tmdb": "108978",
        "season": "4",
        "episode": "2",
        "imdb": "tt9288030",
        "year": "2022",
        "title": "Reacher",
    }

    envelope = seal_envelope(path, payload)
    body_bytes = bytes(envelope.get("body", []))

    upstream_headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Origin": base_url,
        "Referer": referrer_url,
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
        ),
    }

    upstream = requests.post(f"{url_api}/g", headers=upstream_headers, data=body_bytes)
    upstream.raise_for_status()

    decrypted = decrypt_response(upstream.content, envelope)
    print(json.dumps(decrypted, indent=2))
