import requests
import json

url = "https://cityofharrington.civicweb.net/Portal/api/meetings"
headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

r = requests.get(url, headers=headers)
print(r.text[:500])
