import json
import csv
from duckduckgo_search import DDGS
import time

VERIFIED_CSV = '/Users/thejoshpenner/.openclaw/workspace/sao-scraper/mapped_wa_universe_verified.csv'

def precision_search_wa_schools():
    """
    Since the OSPI open data portal isn't yielding the web addresses cleanly via the Socrata API, 
    we will do a highly restricted, domain-locked search.
    We ONLY accept URLs ending in .wednet.edu, .org, or .edu.
    """
    with open(VERIFIED_CSV, 'r') as f:
        reader = list(csv.DictReader(f))
        fieldnames = reader[0].keys()

    updated_count = 0
    
    # Get all schools missing URLs
    targets = [row for row in reader if row['Type'] == 'School' and not row['Official_URL']]
    
    print(f"Executing precision domain-locked search for {len(targets)} School Districts...")
    
    for i, row in enumerate(targets):
        query = f'"{row["Name"]}" Washington site:wednet.edu OR site:org OR site:edu'
        print(f"[{i+1}/{len(targets)}] {query}")
        
        try:
            results = DDGS().text(query, max_results=3)
            for r in results:
                url = r['href'].lower()
                # Strict validation
                if ('.wednet.edu' in url or '.org' in url or '.edu' in url) and 'wikipedia' not in url and 'facebook' not in url:
                    # Strip to base domain
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    
                    row['Official_URL'] = base_url
                    row['Vendor'] = 'Pending Probe'
                    updated_count += 1
                    print(f"   -> Locked: {base_url}")
                    break
        except Exception as e:
            print(f"   -> Error: {e}")
            
        time.sleep(1) # Rate limit

    # Write back
    with open(VERIFIED_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reader)
        
    print(f"Successfully locked {updated_count} URLs with strict domain validation.")

if __name__ == "__main__":
    precision_search_wa_schools()
