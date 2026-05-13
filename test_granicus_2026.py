import requests
import json

url = "https://webapi.legistar.com/v1/seattle/events?$filter=EventDate ge datetime'2026-01-01T00:00:00'&$top=5"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Accept": "application/json"
}

resp = requests.get(url, headers=headers)
if resp.status_code == 200:
    data = resp.json()
    if data:
        print("SUCCESS! Pulled 2026 events.\n")
        print("Available metadata fields for an event:")
        event = data[0]
        for key, value in event.items():
            # truncate long strings for display
            val_str = str(value)
            if len(val_str) > 80:
                val_str = val_str[:80] + "..."
            print(f" - {key}: {val_str}")
            
        print("\nChecking specifically for documents/media...")
        for e in data:
            print(f"\n{e.get('EventBodyName')} on {e.get('EventDate')}")
            print(f"  Agenda: {e.get('EventAgendaFile')}")
            print(f"  Minutes: {e.get('EventMinutesFile')}")
            print(f"  Video: {e.get('EventVideoPath')}")
            print(f"  Audio: {e.get('EventAudioPath')}")
    else:
        print("No data returned for 2026 yet.")
else:
    print(f"Failed. {resp.status_code}: {resp.text}")
