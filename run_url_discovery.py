import pandas as pd
import requests
import concurrent.futures
import time
from bs4 import BeautifulSoup
import re

df = pd.read_csv("sao-scraper/wa_core_jurisdictions.csv")
jurisdictions = df['Name'].tolist()

# The user wants to map jurisdictions to their Granicus/CivicPlus portals.
# A simple way to do this is to construct likely URLs for Granicus, or use a search API, but let's just 
# write the scaffolding that tests the direct webapi.legistar endpoint since we know how Granicus works.

legistar_found = []

def check_legistar(name):
    # Legistar uses normalized names: Seattle -> seattle, King County -> kingcounty
    normalized = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    # Try with and without 'county' for counties, etc.
    variants = [normalized]
    if "county" in normalized:
        variants.append(normalized.replace("county", ""))
    if "cityof" not in normalized:
        variants.append("cityof" + normalized)
        
    for v in variants:
        try:
            url = f"https://webapi.legistar.com/v1/{v}/events?$top=1"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                return {"Name": name, "Legistar_ID": v, "Platform": "Granicus"}
        except:
            pass
    return None

print(f"Scanning {len(jurisdictions)} WA jurisdictions for Granicus/Legistar APIs...")
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    results = executor.map(check_legistar, jurisdictions)
    for r in results:
        if r:
            legistar_found.append(r)
            print(f"Found: {r['Name']} -> {r['Legistar_ID']}")

print(f"Total Granicus APIs found: {len(legistar_found)}")
