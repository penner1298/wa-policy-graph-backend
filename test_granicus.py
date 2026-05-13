import requests
import json
from bs4 import BeautifulSoup

print("Testing Granicus/Legistar Web API (Seattle City Council as target)...")

# Many Granicus instances expose a relatively open REST API if you know the endpoints
# Let's check Seattle's public API
url = "https://webapi.legistar.com/v1/seattle/events"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json"
}

try:
    # Get the 3 most recent meetings
    resp = requests.get(url + "?$top=3&$orderby=EventDate desc", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print("\nSUCCESS! Successfully hit the Granicus/Legistar Backend API.")
        print(f"Found {len(data)} recent meetings for Seattle.")
        for event in data:
            print(f"\n--- Meeting: {event.get('EventBodyName', 'Unknown')} ---")
            print(f"Date: {event.get('EventDate')}")
            print(f"Time: {event.get('EventTime')}")
            print(f"Agenda URL: {event.get('EventAgendaFile')}")
            
            # If there's an agenda file, that's what we send to Membrane
            if event.get('EventAgendaFile'):
                print("-> Agenda PDF Available for Membrane Ingestion.")
    else:
        print(f"Failed to hit API. Status: {resp.status_code}")
except Exception as e:
    print(f"Error: {e}")
    
