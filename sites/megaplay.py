import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse


'''
Supports:
https://megaplay.buzz/
'''


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
base_url = 'https://megaplay.buzz/stream/s-2/168904/sub'
user_agent = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36"
parsed_url = urlparse(base_url)
default_domain = f"{parsed_url.scheme}://{parsed_url.netloc}/"
headers = {
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": default_domain,
    "User-Agent": user_agent
}

# Fetch initial response
response = requests.get(base_url, headers=headers).text
soup = BeautifulSoup(response, 'html.parser')

# Get episode ID and nonce
video_tag = soup.select_one('#megaplay-player')
episode_id = video_tag.get('data-ep-id')

# Get media type
match = re.search(r"type:\s+\'(.*?)\'", response)
media_type = match.group(1)

# Get servers html
response = requests.get(f'https://nine.mewcdn.online/ajax/episode/servers?episodeId={episode_id}&type={media_type}', headers=headers).json()
servers_html = response.get('html')
soup = BeautifulSoup(servers_html, "html.parser")

# Get streaming servers
data = soup.find(attrs={"data-id": True})
source_id = data.attrs.get('data-id')
response = requests.get(f'https://nine.mewcdn.online/ajax/episode/sources?id={source_id}&type={type}').json()

# Get streaming data
file_id = urlparse(response.get('link')).path.split("/")[-1]
response = requests.get(f"https://rapid-cloud.co/embed-2/v2/e-1/getSources?id={file_id}").json()

# Extract video URL
video_url = response.get('sources')[0].get('file')

# Print results
print("\n" + "#" * 25 + "\n" + "#" * 25)
print(f"Captured URL: {Colors.okgreen}{video_url}{Colors.endc}")
print("#" * 25 + "\n" + "#" * 25)
print(f"{Colors.warning}### Use these headers to access the URL")
print(f"{Colors.okcyan}Referer:{Colors.endc} {default_domain}")
print("\n")
