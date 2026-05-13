import requests
from bs4 import BeautifulSoup
import pandas as pd
import concurrent.futures

entities = []
headers = {'User-Agent': 'Mozilla/5.0'}

print("Scraping MRSC Cities Directory...")
try:
    r = requests.get("https://mrsc.org/get-to-know-wa/cities-and-towns", headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # MRSC lists the cities. We need to extract the profile links, then visit them to get the official URL.
    profile_links = []
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if "/get-to-know-wa/cities-and-towns/" in href and len(a.text.strip()) > 2:
            full_url = f"https://mrsc.org{href}" if href.startswith('/') else href
            profile_links.append({"Name": a.text.strip(), "Profile": full_url})
            
    print(f"Found {len(profile_links)} City profiles on MRSC. Fetching official URLs...")
    
    def get_official_url(item):
        try:
            res = requests.get(item['Profile'], headers=headers, timeout=5)
            psoup = BeautifulSoup(res.text, 'html.parser')
            # Look for external links that aren't MRSC
            for a in psoup.find_all('a'):
                link = a.get('href', '')
                if link.startswith('http') and 'mrsc.org' not in link and 'google' not in link and 'facebook' not in link:
                    item['Official_URL'] = link
                    return item
        except:
            pass
        item['Official_URL'] = None
        return item

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(get_official_url, profile_links[:10]) # test 10
        for r in results:
            print(f"{r['Name']} -> {r['Official_URL']}")

except Exception as e:
    print(f"Error: {e}")
