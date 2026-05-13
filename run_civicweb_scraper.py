import pandas as pd
import subprocess
import os
import concurrent.futures

df = pd.read_csv("sao-scraper/mapped_wa_universe.csv")
targets = df[df['Platform'] == 'CivicWeb']

print(f"Executing `civic-scraper` across {len(targets)} CivicWeb jurisdictions...")

def run_civic_scraper(row):
    name = row['Name']
    portal_id = row['ID']
    url = f"https://{portal_id}.civicweb.net/Portal"
    
    print(f"Initiating civic-scraper for {name} ({url})")
    try:
        asset_dir = f"sao-scraper/assets/{name.replace(' ', '_')}"
        os.makedirs(asset_dir, exist_ok=True)
        
        cmd = [
            "civic-scraper", "scrape", 
            "--url", url, 
            "--start-date", "2026-01-01", 
            "--download"
        ]
        
        env = os.environ.copy()
        env['CIVIC_SCRAPER_DIR'] = os.path.abspath(asset_dir)
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f" [SUCCESS] civic-scraper finished {name}")
        else:
            err_line = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'Unknown Error'
            print(f" [FAILED] {name} - {err_line}")
            
    except subprocess.TimeoutExpired:
        print(f" [TIMEOUT] {name} timed out after 5 minutes.")
    except Exception as e:
        print(f" [ERROR] {name}: {e}")

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    executor.map(run_civic_scraper, [row for _, row in targets.iterrows()])

