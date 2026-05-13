import requests
from bs4 import BeautifulSoup
import pandas as pd
import concurrent.futures
import time

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

print("Scraping MRSC City Profiles...")
r = requests.get("https://mrsc.org/Research-Tools/Washington-City-and-Town-Profiles", headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

tables = soup.find_all('table')
if not tables:
    print("No tables found.")
    exit()

table = tables[0]
profile_links = []
for row in table.find_all('tr')[1:]:
    tds = row.find_all('td')
    if len(tds) > 0:
        a_tag = tds[0].find('a')
        if a_tag:
            name = a_tag.text.strip()
            href = a_tag.get('href', '')
            full_url = f"https://mrsc.org{href}" if href.startswith('/') else href
            profile_links.append({"Name": name, "Profile": full_url})

print(f"Found {len(profile_links)} City profiles on MRSC.")

urls_found = {}

def get_official_url(item):
    try:
        res = requests.get(item['Profile'], headers=headers, timeout=5)
        psoup = BeautifulSoup(res.text, 'html.parser')
        
        # Look through all links
        for a in psoup.find_all('a'):
            href = a.get('href', '')
            # If the link text is the URL itself or contains "Website"
            if 'http' in href and 'mrsc.org' not in href and 'wa.gov' not in href and 'facebook' not in href:
                if 'website' in a.text.lower() or href.startswith('http'):
                    # To be safe, look for a div or dt that says "Website"
                    return {"Name": item['Name'], "Official_URL": href}
    except Exception as e:
        pass
    return {"Name": item['Name'], "Official_URL": None}

print("Extracting exact domains from MRSC profiles...")
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    results = executor.map(get_official_url, profile_links)
    count = 0
    for r in results:
        if r['Official_URL']:
            urls_found[r['Name']] = r['Official_URL']
            print(f"Found: {r['Name']} -> {r['Official_URL']}")
            count += 1
        time.sleep(0.1)

print(f"Successfully extracted {count} official URLs from MRSC.")

# Merge with our main universe
df = pd.read_csv("sao-scraper/mapped_wa_universe.csv")
df['Official_URL'] = df['Name'].map(urls_found)
df.to_csv("sao-scraper/mapped_wa_universe.csv", index=False)
