import requests
import json
from bs4 import BeautifulSoup
import re

print("Exploring CivicPlus / CivicClerk architecture...\n")

# Lakewood URL
base_url = "https://cityoflakewood.civicweb.net/Portal/MeetingInformation.aspx?Id="

# We need to find how they expose their meetings list. Usually it's in a hidden API or a static document list.
portal_url = "https://cityoflakewood.civicweb.net/Portal/MeetingTypeList.aspx"
headers = {"User-Agent": "Mozilla/5.0"}

print("Attempting to hit Lakewood's MeetingTypeList...")
try:
    resp = requests.get(portal_url, headers=headers)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Look for meeting links
        links = soup.find_all('a', href=True)
        meeting_links = [l for l in links if 'MeetingInformation.aspx' in l['href']]
        print(f"Found {len(meeting_links)} meeting links on the portal page.")
        
        if meeting_links:
            print(f"Sample Link: {meeting_links[0]['href']}")
            
        # CivicPlus usually relies on heavy ASP.NET ViewState forms
        viewstate = soup.find("input", {"id": "__VIEWSTATE"})
        if viewstate:
            print("Detected ASP.NET __VIEWSTATE. This means the site relies on client-side state.")
            
    else:
        print(f"Failed. {resp.status_code}")
except Exception as e:
    print(e)
    
print("\nChecking for common CivicPlus REST API endpoints...")
api_endpoints = [
    "https://cityoflakewood.civicweb.net/api/meetings",
    "https://cityoflakewood.civicweb.net/Portal/api/meetings",
    "https://cityoflakewood.civicweb.net/document/api/search"
]

for ep in api_endpoints:
    try:
        r = requests.get(ep, headers=headers)
        print(f"{ep} -> Status: {r.status_code}")
    except:
        pass

