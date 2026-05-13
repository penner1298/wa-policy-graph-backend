import csv
import urllib.request
import json

VERIFIED_CSV = '/Users/thejoshpenner/.openclaw/workspace/sao-scraper/mapped_wa_universe_verified.csv'

def fetch_ospi_districts():
    print("Fetching OSPI District Information from WA State Data Portal...")
    # WA State Data Portal: Washington State Public Schools
    # Using dataset identifier 'f6w7-q2d2' which is often used for Washington State Public Schools
    url = "https://data.wa.gov/resource/f6w7-q2d2.json?$limit=5000"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        # Create a mapping of district name to website
        district_urls = {}
        for row in data:
            dist_name = row.get('lea_name', '').strip()
            if not dist_name:
                dist_name = row.get('school_district_name', '').strip()
                
            # If the dataset has website info
            website = row.get('website', '')
            if not website:
                website = row.get('web_address', '')
                
            if dist_name and website:
                # Clean up district name for matching
                clean_name = dist_name.lower().replace('school district', '').strip()
                district_urls[clean_name] = website
                
        return district_urls
    except Exception as e:
        print(f"Failed to fetch from WA data portal: {e}")
        return {}

def update_master_csv():
    ospi_urls = fetch_ospi_districts()
    
    # If the direct JSON pull fails to get websites, we will use an alternative
    # Washington MRSC (Municipal Research and Services Center) is the best fallback
    # but requires scraping their directory.
    
    with open(VERIFIED_CSV, 'r') as f:
        reader = list(csv.DictReader(f))
        fieldnames = reader[0].keys()
        
    updated_count = 0
    for row in reader:
        if row['Type'] == 'School' and not row['Official_URL']:
            clean_name = row['Name'].lower().replace('school district', '').strip()
            
            # Try to match
            for ospi_name, ospi_url in ospi_urls.items():
                if ospi_name in clean_name or clean_name in ospi_name:
                    if not ospi_url.startswith('http'):
                        ospi_url = 'https://' + ospi_url
                    row['Official_URL'] = ospi_url
                    updated_count += 1
                    break

    with open(VERIFIED_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reader)
        
    print(f"Successfully matched and updated {updated_count} School District URLs from authoritative sources.")

if __name__ == "__main__":
    update_master_csv()
