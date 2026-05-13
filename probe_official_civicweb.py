import pandas as pd
import requests
from bs4 import BeautifulSoup
import concurrent.futures

df = pd.read_csv('sao-scraper/mapped_wa_universe_verified.csv')

def check_official_site(row):
    url = row['Official_URL']
    if not isinstance(url, str) or not url.startswith('http'):
        return None
        
    try:
        r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            # Look for links to civicweb or granicus
            cw_links = []
            granicus_links = []
            for a in soup.find_all('a', href=True):
                href = a['href'].lower()
                if 'civicweb.net' in href:
                    cw_links.append(a['href'])
                if 'legistar.com' in href or 'granicus.com' in href:
                    granicus_links.append(a['href'])
            
            return {
                "ID": row['ID'],
                "Name": row['Name'],
                "Official_URL": url,
                "CivicWeb_Links": list(set(cw_links)),
                "Granicus_Links": list(set(granicus_links))
            }
    except Exception as e:
        pass
    return None

print(f"Scanning {len(df)} official WA homepages for explicit CMS portals...")

with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    results = list(executor.map(check_official_site, [row for _, row in df.iterrows()]))

valid = [r for r in results if r is not None]

# Filter those that actually found links
cw_found = [r for r in valid if r['CivicWeb_Links']]
gran_found = [r for r in valid if r['Granicus_Links']]

print(f"\nFound {len(cw_found)} Explicit CivicWeb Links:")
for c in cw_found:
    print(f" - {c['Name']}: {c['CivicWeb_Links']}")

print(f"\nFound {len(gran_found)} Explicit Granicus/Legistar Links:")
for g in gran_found:
    print(f" - {g['Name']}: {g['Granicus_Links']}")

pd.DataFrame(valid).to_csv('sao-scraper/verified_cms_mappings.csv', index=False)
