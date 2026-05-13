import csv
import re

VERIFIED_CSV = '/Users/thejoshpenner/.openclaw/workspace/sao-scraper/mapped_wa_universe_verified.csv'
TEMP_CSV = '/Users/thejoshpenner/.openclaw/workspace/sao-scraper/mapped_wa_universe_verified_tmp.csv'

def clean_ports():
    with open(VERIFIED_CSV, 'r') as f:
        reader = list(csv.DictReader(f))
        fieldnames = reader[0].keys()

    for row in reader:
        name = row['Name']
        if row['Type'] == 'Port' and ('voted in on' in name or 'voted in in' in name or re.match(r'^\d+\.', name)):
            # Regex to capture just "Port of X"
            # e.g., "70. Port of Wahkiakum County No. 2, voted in on November 8, 1966" -> "Port of Wahkiakum County No. 2"
            # e.g., "16. Port of Illahee (Kitsap County), voted in on May 20, 1922" -> "Port of Illahee"
            
            clean_name = name
            # Remove leading numbers and dot: "70. "
            clean_name = re.sub(r'^\d+\.\s*', '', clean_name)
            # Remove anything from ", voted in" onwards
            clean_name = re.sub(r',?\s*voted in.*$', '', clean_name)
            # Remove parenthetical county names if they exist "Port of Illahee (Kitsap County)"
            
            match = re.search(r'\(([^)]+? County)\)', clean_name)
            if match:
                county = match.group(1).replace(' County', '')
                if row.get('County', 'Unknown') == 'Unknown':
                    row['County'] = county
            
            clean_name = re.sub(r'\s*\([^)]+ County\)', '', clean_name)
            
            row['Name'] = clean_name.strip()
            
            # Fix ID
            row['ID'] = row['Name'].lower().replace(" ", "").replace(".", "").replace(",", "")

    with open(TEMP_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reader)

    import os
    os.replace(TEMP_CSV, VERIFIED_CSV)
    print("Ports cleaned successfully.")

if __name__ == "__main__":
    clean_ports()
