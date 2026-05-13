import requests
import json
import csv
import os
import concurrent.futures

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERIFIED_CSV = os.path.join(BASE_DIR, 'mapped_wa_universe_verified.csv')
OUTPUT_CSV = os.path.join(BASE_DIR, 'vendor_endpoints.csv')

def get_legistar_clients():
    try:
        resp = requests.get("https://webapi.legistar.com/v1/Client", timeout=10)
        return resp.json() if resp.status_code == 200 else []
    except: return []

def probe_url(jurisdiction, base_url):
    # This probes the actual URL to see if there's a redirect to CivicPlus, Granicus, etc.
    if not base_url or str(base_url).strip() == "":
        return "Unknown", "None"
        
    base_url = str(base_url).strip()
    if not base_url.startswith('http'):
        base_url = "https://" + base_url
        
    try:
        # Check standard paths
        resp = requests.get(base_url, timeout=5, allow_redirects=True)
        final_url = resp.url.lower()
        html = resp.text.lower()
        
        if 'civicplus.com' in html or 'civicweb.net' in final_url or 'civicplus' in final_url:
            return "CivicPlus/CivicWeb", final_url
        if 'granicus.com' in html or 'granicus' in final_url:
            return "Granicus", final_url
        if 'boarddocs.com' in html or 'boarddocs' in final_url:
            return "BoardDocs", final_url
        if 'municode.com' in html or 'municode' in final_url:
            return "MuniCode", final_url
        if 'iqm2.com' in html or 'iqm2' in final_url: # Granicus legacy
            return "Granicus (IQM2)", final_url
            
        return "Custom/Unknown", base_url
    except:
        return "Unreachable", base_url

def process():
    legistar_clients = get_legistar_clients()
    results = []
    
    with open(VERIFIED_CSV, 'r') as f:
        reader = list(csv.DictReader(f))
        
    print(f"Probing {len(reader)} jurisdictions...")
    
    # We will do a quick thread pool to speed up the probe
    def check_row(row):
        name = row.get('Name', '').lower()
        url = row.get('Official_URL', '')
        
        # 1. Check Legistar strictly by name
        for lc in legistar_clients:
            cname = lc.get('ClientName', '').lower()
            if (name in cname and 'wa' in cname) or lc.get('ClientShortName', '').lower() == name.replace(" ", ""):
                return {
                    "Jurisdiction": row.get('Name'),
                    "Type": row.get('Type'),
                    "Official_URL": url,
                    "Detected_Vendor": "Legistar",
                    "API_Endpoint": f"https://webapi.legistar.com/v1/{lc.get('ClientShortName')}/events"
                }
                
        # 2. Hardcoded Overrides for the Big Ones
        known_map = {
            "seattle": "seattle", "tacoma": "cityoftacoma", "olympia": "olympia", "bellevue": "bellevue",
            "snohomish": "snohomish", "redmond": "redmond"
        }
        if name in known_map:
            return {
                "Jurisdiction": row.get('Name'),
                "Type": row.get('Type'),
                "Official_URL": url,
                "Detected_Vendor": "Legistar",
                "API_Endpoint": f"https://webapi.legistar.com/v1/{known_map[name]}/events"
            }
            
        # 3. HTTP Probe
        vendor, endpoint = probe_url(name, url)
        return {
            "Jurisdiction": row.get('Name'),
            "Type": row.get('Type'),
            "Official_URL": url,
            "Detected_Vendor": vendor,
            "API_Endpoint": endpoint
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(check_row, reader))
        
    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["Jurisdiction", "Type", "Official_URL", "Detected_Vendor", "API_Endpoint"])
        writer.writeheader()
        writer.writerows(results)
        
    # Summarize
    vc = {}
    for r in results:
        v = r['Detected_Vendor']
        vc[v] = vc.get(v, 0) + 1
        
    print("\n--- Discovery Complete ---")
    for v, c in vc.items():
        print(f"{v}: {c}")

if __name__ == "__main__":
    process()
