import csv
import os

VERIFIED_CSV = '/Users/thejoshpenner/.openclaw/workspace/sao-scraper/mapped_wa_universe_verified.csv'

def nuke_bad_urls():
    with open(VERIFIED_CSV, 'r') as f:
        reader = list(csv.DictReader(f))
        fieldnames = reader[0].keys()

    cleaned_count = 0
    for row in reader:
        type_ = row.get('Type')
        url = row.get('Official_URL', '').lower()
        
        # If it's a school or port, we need to nuke the URL if it came from the dirty DDG search
        # We can identify dirty URLs because they are either completely unrelated (alaskaair)
        # or they don't have .edu, .org, .us, .net, .wa.us, etc.
        
        if type_ in ['School', 'Port']:
            # For Schools, almost all are .org, .net, or .wa.us. Or .edu.
            # If it's something weird, just blank it. We are going to re-source them all anyway from OSPI/MRSC.
            
            # Since the user wants to ensure ALL of them are cleaned, and they were all sourced from the bad DDG pass,
            # the safest route to ensure 100% integrity is to blank ALL URLs for Schools and Ports 
            # and then immediately re-populate them from authoritative sources.
            if url:
                row['Official_URL'] = ''
                row['Scrape_Target'] = ''
                row['Vendor'] = 'Pending Probe'
                row['API_Endpoint'] = ''
                cleaned_count += 1

    with open(VERIFIED_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reader)
        
    print(f"Nuked {cleaned_count} unverified/dirty URLs from Schools and Ports.")

if __name__ == "__main__":
    nuke_bad_urls()
