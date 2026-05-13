import os
import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

BASE_DIR = '/Users/thejoshpenner/.openclaw/workspace/sao-scraper'
VERIFIED_CSV = os.path.join(BASE_DIR, 'mapped_wa_universe_verified.csv')

def find_document_hub(base_url):
    """
    Attempts to figure out the actual taxonomy of a custom/unknown municipal site.
    Returns the exact URL where agendas/minutes are hosted.
    """
    if not base_url or not base_url.startswith('http'):
        return None
        
    try:
        # Step 1: Fetch the homepage
        resp = requests.get(base_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return None
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Step 2: Score all links based on municipal keywords
        target_keywords = ['agenda', 'minute', 'meeting', 'council', 'document', 'board', 'commission']
        best_links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.text.lower()
            
            # Skip obvious junk
            if 'facebook.com' in href or 'mailto:' in href or 'tel:' in href or 'javascript:' in href:
                continue
                
            score = 0
            for kw in target_keywords:
                if kw in href.lower() or kw in text:
                    score += 1
            
            if score > 0:
                full_url = urljoin(resp.url, href)
                # Keep it on the same domain if possible, unless it's a known doc host
                if urlparse(full_url).netloc == urlparse(resp.url).netloc:
                    best_links.append((score, full_url))
        
        # Step 3: Return the highest scoring link (the most likely document hub)
        if best_links:
            best_links.sort(key=lambda x: x[0], reverse=True)
            return best_links[0][1]
            
        return None
        
    except Exception as e:
        # If timeout or connection error
        return None

def discover_taxonomies():
    """
    Updates the master CSV with a new 'Scrape_Target' column.
    For standard APIs, it's just the API Endpoint.
    For Custom/Unknown, it's the discovered taxonomy URL.
    """
    print("Starting Taxonomy Discovery Engine...")
    
    with open(VERIFIED_CSV, 'r') as f:
        reader = list(csv.DictReader(f))
        
    if not reader:
        return
        
    fieldnames = list(reader[0].keys())
    if 'Scrape_Target' not in fieldnames:
        fieldnames.append('Scrape_Target')
        
    updated_rows = []
    
    for i, row in enumerate(reader):
        vendor = row.get('Vendor', '')
        api_endpoint = row.get('API_Endpoint', '')
        official_url = row.get('Official_URL', '')
        
        # If we have a known API, the scrape target is simply the API
        if vendor in ['Legistar', 'CivicPlus/CivicWeb', 'MuniCode', 'BoardDocs', 'Granicus', 'Granicus (IQM2)']:
            row['Scrape_Target'] = api_endpoint
        elif vendor == 'Custom/Unknown' and official_url:
            print(f"[{i+1}/{len(reader)}] Discovering taxonomy for: {row['Name']} ({official_url})")
            discovered_url = find_document_hub(official_url)
            if discovered_url:
                print(f"   -> Found Document Hub: {discovered_url}")
                row['Scrape_Target'] = discovered_url
            else:
                row['Scrape_Target'] = "Manual Review Required"
        else:
            row['Scrape_Target'] = "None"
            
        updated_rows.append(row)
        
    with open(VERIFIED_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
        
    print("\nTaxonomy Discovery Complete. Master CSV updated with 'Scrape_Target'.")

if __name__ == "__main__":
    discover_taxonomies()
