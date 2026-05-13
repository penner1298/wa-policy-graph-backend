import pandas as pd
import requests
import concurrent.futures

df = pd.read_csv('sao-scraper/mapped_wa_universe_verified.csv')
civicweb_urls = []

def check_url(row):
    # Try different ID patterns for CivicWeb
    patterns = [
        row['ID'], 
        row['ID'].replace('cityof', ''), 
        row['ID'].replace('county', '')
    ]
    
    for pattern in set(patterns):
        if not pattern: continue
        url = f"https://{pattern}.civicweb.net/Portal/MeetingTypeList.aspx"
        try:
            r = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200 and 'MeetingTypeList' in r.url:
                return {"ID": row['ID'], "Name": row['Name'], "CivicWeb_URL": url, "Prefix": pattern}
        except:
            pass
    return None

print(f"Probing {len(df)} verified jurisdictions for active CivicWeb portals...")

with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    results = list(executor.map(check_url, [row for _, row in df.iterrows()]))

valid = [r for r in results if r is not None]
valid_df = pd.DataFrame(valid)
valid_df.to_csv('sao-scraper/verified_civicweb_targets.csv', index=False)
print(f"Found {len(valid)} active CivicWeb portals from the verified WA list:")
print(valid_df.head(15))
