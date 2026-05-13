import requests
from bs4 import BeautifulSoup
import pandas as pd
import concurrent.futures

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

print("Scraping MRSC City Profiles...")
r = requests.get("https://mrsc.org/Research-Tools/Washington-City-and-Town-Profiles", headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

profile_links = []
for a in soup.find_all('a'):
    href = a.get('href', '')
    if '/Washington-City-and-Town-Profiles/' in href and len(a.text.strip()) > 2:
        full_url = f"https://mrsc.org{href}" if href.startswith('/') else href
        profile_links.append({"Name": a.text.strip(), "Profile": full_url})

# Deduplicate
unique_profiles = []
seen = set()
for p in profile_links:
    if p['Name'] not in seen:
        seen.add(p['Name'])
        unique_profiles.append(p)

print(f"Found {len(unique_profiles)} unique City profiles on MRSC.")

urls_found = {}

def get_official_url(item):
    try:
        res = requests.get(item['Profile'], headers=headers, timeout=5)
        psoup = BeautifulSoup(res.text, 'html.parser')
        
        # MRSC puts the website link usually near the top with text "Website" or just the raw URL
        for a in psoup.find_all('a'):
            text = a.text.strip().lower()
            href = a.get('href', '')
            if 'http' in href and ('mrsc.org' not in href) and ('google' not in href):
                if 'website' in text or 'cityof' in href.lower() or '.gov' in href.lower() or '.us' in href.lower():
                    return {"Name": item['Name'], "Official_URL": href}
    except Exception as e:
        pass
    return {"Name": item['Name'], "Official_URL": None}

print("Extracting exact domains from MRSC profiles...")
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = executor.map(get_official_url, unique_profiles)
    count = 0
    for r in results:
        if r['Official_URL']:
            urls_found[r['Name']] = r['Official_URL']
            count += 1

print(f"Successfully extracted {count} official URLs from MRSC.")

# Save to CSV
df_urls = pd.DataFrame(list(urls_found.items()), columns=['Name', 'Official_URL'])
df_urls.to_csv("sao-scraper/mrsc_extracted_urls.csv", index=False)
