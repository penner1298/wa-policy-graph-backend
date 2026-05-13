import os
import sqlite3
import requests
import time
import logging

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_DIR = os.path.join(BASE_DIR, 'vault', 'meetings')
LOG_PATH = os.path.join(BASE_DIR, 'bulk_vault_downloader.log')

logging.basicConfig(filename=LOG_PATH, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def download_file(url, jurisdiction, date, event_id, doc_type):
    try:
        # Create jurisdiction directory
        save_dir = os.path.join(VAULT_DIR, jurisdiction)
        os.makedirs(save_dir, exist_ok=True)
        
        filename = f"{jurisdiction}_{date}_{event_id}_{doc_type}.pdf"
        pdf_path = os.path.join(save_dir, filename)
        
        # Skip if already exists
        if os.path.exists(pdf_path):
            return True
            
        print(f"  Downloading: {filename}")
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if resp.status_code == 200:
            with open(pdf_path, "wb") as f:
                f.write(resp.content)
            logging.info(f"Downloaded: {filename}")
            return True
        else:
            logging.error(f"Failed to download {filename}: HTTP {resp.status_code}")
            return False
    except Exception as e:
        logging.error(f"Download error {filename}: {e}")
        return False

def fetch_and_vault_jurisdiction(jurisdiction_id):
    print(f"Building Vault for {jurisdiction_id} (All Historical Meetings)...")
    # Fetching ALL meetings available via the API
    url = f"https://webapi.legistar.com/v1/{jurisdiction_id}/events"
    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code != 200:
            print(f"  [ERROR] Legistar API returned {resp.status_code}")
            return
        events = resp.json()
        print(f"  Found {len(events)} historical events.")
        
        count = 0
        for event in events:
            event_id = str(event.get('EventId'))
            meeting_date = (event.get('EventDate') or "0000-00-00")[:10]
            
            docs = [
                ('Agenda', event.get('EventAgendaFile')),
                ('Minutes', event.get('EventMinutesFile'))
            ]
            
            for doc_type, doc_url in docs:
                if not doc_url: continue
                if download_file(doc_url, jurisdiction_id, meeting_date, event_id, doc_type):
                    count += 1
            
            # Subtle delay to avoid rate limiting
            if count % 10 == 0:
                time.sleep(0.5)
        
        print(f"  [COMPLETED] Vaulted {count} documents for {jurisdiction_id}.")
    except Exception as e:
        print(f"Error fetching {jurisdiction_id}: {e}")

if __name__ == "__main__":
    # WA High-Priority List
    wa_targets = [
        "kingcounty", "olympia", "bellevue", "cityoftacoma", "snohomish",
        "redmond", "seattle", "douglascounty", "whatcom", "cityofdeerpark",
        "toledo", "cityoflacrosse", "cityofnorthport"
    ]
    
    os.makedirs(VAULT_DIR, exist_ok=True)
    
    for target in wa_targets:
        fetch_and_vault_jurisdiction(target)
        time.sleep(2) # Cooldown between jurisdictions
