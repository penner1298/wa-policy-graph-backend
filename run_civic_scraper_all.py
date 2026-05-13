import pandas as pd
import subprocess
import os
import sqlite3
import json
import concurrent.futures

df = pd.read_csv("sao-scraper/mapped_wa_universe_with_urls.csv")

# Filter out the Granicus ones we already processed.
targets = df[(df['Official_URL'].notna()) & (df['Platform'] != 'Granicus')]

print(f"Executing `civic-scraper` library across {len(targets)} verified jurisdictions...")

def run_civic_scraper(row):
    name = row['Name']
    url = row['Official_URL']
    
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
        env['CIVIC_SCRAPER_DIR'] = asset_dir
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print(f" [SUCCESS] civic-scraper finished {name}")
        else:
            print(f" [FAILED] {name} - {result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'Unknown Error'}")
            
    except subprocess.TimeoutExpired:
        print(f" [TIMEOUT] {name} timed out after 2 minutes.")
    except Exception as e:
        print(f" [ERROR] {name}: {e}")

# Run concurrently
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(run_civic_scraper, [row for _, row in targets.iterrows()])

