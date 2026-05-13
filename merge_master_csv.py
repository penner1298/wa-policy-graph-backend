import csv
import os

BASE_DIR = '/Users/thejoshpenner/.openclaw/workspace/sao-scraper'
VERIFIED_CSV = os.path.join(BASE_DIR, 'mapped_wa_universe_verified.csv')
VENDOR_CSV = os.path.join(BASE_DIR, 'vendor_endpoints.csv')

def update_master():
    if not os.path.exists(VENDOR_CSV):
        print("Vendor CSV not found.")
        return

    # Read vendor data
    vendor_data = {}
    with open(VENDOR_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            vendor_data[row['Jurisdiction']] = {
                'Vendor': row.get('Detected_Vendor', 'Unknown'),
                'API_Endpoint': row.get('API_Endpoint', '')
            }

    # Read Master CSV
    with open(VERIFIED_CSV, 'r') as f:
        reader = list(csv.DictReader(f))
        
    if not reader:
        print("Master CSV is empty.")
        return
        
    fieldnames = list(reader[0].keys())
    if 'Vendor' not in fieldnames:
        fieldnames.append('Vendor')
    if 'API_Endpoint' not in fieldnames:
        fieldnames.append('API_Endpoint')

    # Update rows
    for row in reader:
        name = row.get('Name')
        v_info = vendor_data.get(name, {})
        row['Vendor'] = v_info.get('Vendor', 'Unknown')
        row['API_Endpoint'] = v_info.get('API_Endpoint', '')

    # Write back to Master CSV
    with open(VERIFIED_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reader)

    print("Master CSV updated successfully.")
    
    # Clean up vestigial file
    os.remove(VENDOR_CSV)
    print("Cleaned up vendor_endpoints.csv.")

if __name__ == "__main__":
    update_master()
