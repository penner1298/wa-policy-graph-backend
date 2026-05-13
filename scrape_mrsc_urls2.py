import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# MRSC changed their URL structure recently. Let's try to find the directory.
r = requests.get("https://mrsc.org/explore-topics/local-government", headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')
for a in soup.find_all('a'):
    if 'directory' in a.get('href', '').lower() or 'city' in a.get('href', '').lower():
        print(a.get('href'))
