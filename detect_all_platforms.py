import pandas as pd
import requests
import concurrent.futures
import re
import json

df = pd.read_csv("sao-scraper/wa_core_jurisdictions.csv")
jurisdictions = df['Name'].tolist()

results_db = []

def check_platforms(name):
    normalized = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    variants = [normalized]
    if "county" in normalized: variants.append(normalized.replace("county", ""))
    if "cityof" not in normalized: variants.append("cityof" + normalized)
    
    # 1. Check Legistar/Granicus WebAPI
    for v in variants:
        try:
            url = f"https://webapi.legistar.com/v1/{v}/events?$top=1"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                return {"Name": name, "Platform": "Granicus", "ID": v}
        except: pass
        
    # 2. Check CivicWeb (CivicPlus Legacy)
    # usually format: https://cityof[name].civicweb.net/Portal/
    for v in variants:
        try:
            url = f"https://{v}.civicweb.net/Portal/"
            r = requests.get(url, timeout=3)
            if r.status_code == 200 and "CivicWeb" in r.text:
                return {"Name": name, "Platform": "CivicWeb", "ID": v}
        except: pass
        
    return {"Name": name, "Platform": "Unknown", "ID": "N/A"}

print(f"Scanning all {len(jurisdictions)} WA jurisdictions across platforms...")
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    results = executor.map(check_platforms, jurisdictions)
    for r in results:
        results_db.append(r)
        if r['Platform'] != "Unknown":
            print(f"Found: {r['Name']} -> {r['Platform']} ({r['ID']})")

df_results = pd.DataFrame(results_db)
df_results.to_csv("sao-scraper/mapped_wa_universe.csv", index=False)
print(f"\nSaved mapping to mapped_wa_universe.csv")
print(df_results['Platform'].value_counts())

