import csv
import re
from bs4 import BeautifulSoup

VERIFIED_CSV = '/Users/thejoshpenner/.openclaw/workspace/sao-scraper/mapped_wa_universe_verified.csv'

def sync():
    districts = set()
    with open('/Users/thejoshpenner/.openclaw/workspace/sao-scraper/wiki_schools.html', 'r') as f:
        html = f.read()
        
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all('a'):
        text = a.text.strip()
        if 'School District' in text or 'Public Schools' in text:
            # remove numbers like "School District 5"
            text = re.sub(r'\s+\d+$', '', text)
            districts.add(text)
            
    print(f"Parsed {len(districts)} unique districts from HTML.")
    
    with open(VERIFIED_CSV, 'r') as f:
        reader = list(csv.DictReader(f))
        fieldnames = reader[0].keys()
        
    existing_schools = set(row['Name'].lower().replace('school district', '').replace('public schools', '').strip() for row in reader if row['Type'] == 'School')
    
    added = 0
    for ws in districts:
        clean_ws = ws.lower().replace('school district', '').replace('public schools', '').strip()
        
        found = False
        for es in existing_schools:
            if clean_ws == es or clean_ws in es or es in clean_ws:
                found = True
                break
                
        if not found:
            reader.append({
                'Name': ws,
                'Type': 'School',
                'County': 'Unknown',
                'Official_URL': '',
                'ID': ws.lower().replace(' ', '').replace(',', ''),
                'Vendor': 'Pending Probe',
                'API_Endpoint': '',
                'Scrape_Target': ''
            })
            added += 1
            existing_schools.add(clean_ws)

    with open(VERIFIED_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reader)
        
    print(f"Added {added} missing school districts. New total: {len([r for r in reader if r['Type'] == 'School'])}")

if __name__ == "__main__":
    sync()
