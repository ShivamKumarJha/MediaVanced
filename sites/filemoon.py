import re
import json
import base64
import requests
from Crypto.Cipher import AES
from urllib.parse import urlparse


'''
Supports:
https://filemoon.to/
'''

# ⚠️ Uses reference from https://github.com/Gujal00/ResolveURL
# Credits to original author — please support them ⭐


class Colors:
    header = '\033[95m'
    okblue = '\033[94m'
    okcyan = '\033[96m'
    okgreen = '\033[92m'
    warning = '\033[93m'
    fail = '\033[91m'
    endc = '\033[0m'
    bold = '\033[1m'
    underline = '\033[4m'

# Constants
base_url = "https://filemoon.to/e/obj59dnrqu8x/_Toonworld4all__Spy_x_Family_S01E01_1080p_x265_10bit_BDRip_Multi_Audio_ESub"
user_agent = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36"
parsed_url = urlparse(base_url)
default_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
headers = {
    "Accept": "*/*",
    "Referer": default_domain,
    "X-Embed-Parent": base_url,
    "User-Agent": user_agent
}

# Utility Functions
''' Pad and decode URL-safe Base64 '''
def b64_url_decode(v):
    v = v.replace('-', '+').replace('_', '/')
    return base64.b64decode(v + '=' * (-len(v) % 4))

# Fetch and parse the iframe URL
code = re.search(r'\/e\/(.*?)\/', base_url).group(1)
response = requests.get(f'{default_domain}/api/videos/{code}/embed/details', headers=headers).json()

# Get embed iframe URL
embed_url = response.get('embed_frame_url')
parsed_url = urlparse(embed_url)
domain = f'https://{parsed_url.netloc}'

# Get encrypted streaming data
response = requests.get(f'{domain}/api/videos/{code}/embed/playback', headers=headers).json()

# Get encryption params
encryption_info = response.get('playback')
ciphertext_b64 = encryption_info.get('payload')
key_parts = encryption_info.get('key_parts')
iv_b64 = encryption_info.get('iv')

# Convert encryption params to bytes
ciphertext = b64_url_decode(ciphertext_b64)
key = b''.join(b64_url_decode(p) for p in key_parts)
iv = b64_url_decode(iv_b64)

# Parse auth tag and ciphertext
ciphertext_data = ciphertext[:-16]
tag = ciphertext[-16:]

# Decrypt streaming data
cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
plaintext = cipher.decrypt_and_verify(ciphertext_data, tag)

# Get streaming info as json
streaming_info = json.loads(plaintext)
sources = streaming_info.get('sources')

# Get Video URL
video_url = sources[0].get('url')

# Print Results
print("\n" + "#"*25 + "\n" + "#"*25)
print(f"Captured URL: {Colors.okgreen}{video_url}{Colors.endc}")
print("#"*25 + "\n" + "#"*25)
print(f"{Colors.warning}### Use these headers to access the URL")
print(f"{Colors.okcyan}Referer:{Colors.endc} {domain}")
print(f"{Colors.okcyan}User-Agent:{Colors.endc} {user_agent}")
print("\n")
