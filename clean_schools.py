import csv
import os

VERIFIED_CSV = '/Users/thejoshpenner/.openclaw/workspace/sao-scraper/mapped_wa_universe_verified.csv'

def strip_bad_urls():
    with open(VERIFIED_CSV, 'r') as f:
        reader = list(csv.DictReader(f))
        fieldnames = reader[0].keys()

    bad_domains = ['wikipedia.org', 'facebook.com', 'linkedin.com', 'sao.wa.gov', 'niche.com', 'usnews.com', 'greatschools.org', 'publicschoolreview.com']
    
    cleared = 0
    for row in reader:
        if row['Type'] == 'School':
            url = row.get('Official_URL', '').lower()
            if any(bd in url for bd in bad_domains) or 'washington' in url and '.gov' not in url and '.org' not in url and '.edu' not in url and '.us' not in url and '.net' not in url:
                # If it doesn't look like a real district site, blank it for re-mapping
                # Also if duckduckgo gave us random news sites
                row['Official_URL'] = ''
                row['Scrape_Target'] = 'Manual Review Required'
                cleared += 1

    with open(VERIFIED_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reader)
        
    print(f"Cleared {cleared} garbage URLs from School Districts.")

if __name__ == "__main__":
    strip_bad_urls()
