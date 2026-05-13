import requests
import json

url = "https://webapi.legistar.com/v1/seattle/events/6509/EventItems"
headers = {"Accept": "application/json"}
resp = requests.get(url, headers=headers)

if resp.status_code == 200:
    items = resp.json()
    print(f"Found {len(items)} specific agenda items for this meeting.")
    if items:
        # Show first item
        print("Sample Item Data:")
        for k, v in items[10].items():
            print(f" - {k}: {str(v)[:100]}")
