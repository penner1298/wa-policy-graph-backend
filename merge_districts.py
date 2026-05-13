import csv
import os

BASE_DIR = '/Users/thejoshpenner/.openclaw/workspace/sao-scraper'
VERIFIED_CSV = os.path.join(BASE_DIR, 'mapped_wa_universe_verified.csv')
NEW_MAPPED_CSV = os.path.join(BASE_DIR, 'new_mapped_districts.csv')

def append_new_districts():
    if not os.path.exists(NEW_MAPPED_CSV):
        print("New mapped districts CSV not found.")
        return

    # Read existing master list to prevent duplicates
    existing_ids = set()
    with open(VERIFIED_CSV, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            existing_ids.add(row.get('ID'))

    # Append new entries
    added_count = 0
    with open(NEW_MAPPED_CSV, 'r') as f:
        reader = csv.DictReader(f)
        
        with open(VERIFIED_CSV, 'a', newline='') as out_f:
            writer = csv.DictWriter(out_f, fieldnames=fieldnames)
            
            for row in reader:
                # Basic dedup
                if row.get('ID') not in existing_ids:
                    # Pad missing columns
                    new_row = {
                        'Name': row.get('Name'),
                        'Type': row.get('Type'),
                        'County': row.get('County'),
                        'Official_URL': row.get('Official_URL'),
                        'ID': row.get('ID'),
                        'Vendor': 'Pending Probe',
                        'API_Endpoint': ''
                    }
                    writer.writerow(new_row)
                    existing_ids.add(row.get('ID'))
                    added_count += 1

    print(f"Appended {added_count} new entries to the master file.")

if __name__ == "__main__":
    append_new_districts()
