import os
import csv
import urllib.parse
from urllib.request import urlopen, Request
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERIFIED_CSV = os.path.join(BASE_DIR, 'mapped_wa_universe_verified.csv')
OUTPUT_CSV = os.path.join(BASE_DIR, 'vendor_endpoints.csv')

def detect_vendor(url):
    if not url or str(url).strip() == "":
        return "Unknown", None
        
    url = str(url).strip()
    
    # Simple static checks based on known vendor patterns
    if "legistar.com" in url:
        # e.g., seattle.legistar.com
        client = url.split("://")[-1].split(".")[0]
        return "Legistar", f"https://webapi.legistar.com/v1/{client}/events"
        
    if "civicweb.net" in url:
        return "CivicWeb", url.rstrip('/') + "/Portal/"
        
    if "granicus.com" in url:
        return "Granicus", "Custom Granicus RSS/API"
        
    if "boarddocs.com" in url:
        return "BoardDocs", url
        
    if "municode.com" in url:
        return "MuniCode", url
        
    # If standard URL, we'd ideally probe standard endpoints (e.g. /agendas, /documents)
    # But for a quick heuristic table:
    return "Custom/Unknown", "Probe Required"

def process_file():
    results = []
    
    if not os.path.exists(VERIFIED_CSV):
        print("Verified CSV not found.")
        return
        
    with open(VERIFIED_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            vendor, endpoint = detect_vendor(row.get('Official_URL'))
            
            # Simple heuristic override for big cities if official URL is just the homepage
            name_lower = row.get('Name', '').lower()
            if vendor == "Custom/Unknown":
                if name_lower == "seattle":
                    vendor, endpoint = "Legistar", "https://webapi.legistar.com/v1/seattle/events"
                elif name_lower == "olympia":
                    vendor, endpoint = "Legistar", "https://webapi.legistar.com/v1/olympia/events"
                elif name_lower == "tacoma":
                    vendor, endpoint = "Legistar", "https://webapi.legistar.com/v1/cityoftacoma/events"
                elif name_lower == "bellevue":
                    vendor, endpoint = "Legistar", "https://webapi.legistar.com/v1/bellevue/events"
                    
            results.append({
                "Jurisdiction": row.get('Name'),
                "Type": row.get('Type'),
                "Official_URL": row.get('Official_URL'),
                "Detected_Vendor": vendor,
                "API_Endpoint": endpoint
            })
            
    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["Jurisdiction", "Type", "Official_URL", "Detected_Vendor", "API_Endpoint"])
        writer.writeheader()
        writer.writerows(results)
        
    print(f"Vendor mapping complete. Saved to {OUTPUT_CSV}")
    
    # Print summary of vendors
    vendor_counts = {}
    for r in results:
        v = r['Detected_Vendor']
        vendor_counts[v] = vendor_counts.get(v, 0) + 1
        
    print("\nVendor Summary:")
    for v, c in vendor_counts.items():
        print(f"  {v}: {c}")

if __name__ == "__main__":
    process_file()
