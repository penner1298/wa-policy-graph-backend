import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
r = requests.get("https://mrsc.org/get-to-know-wa/cities-and-towns", headers=headers)
print(f"Status: {r.status_code}")
print(r.text[:1000])
