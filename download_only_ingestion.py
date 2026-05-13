import os
import requests
import logging
import csv
import time
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = os.path.join(BASE_DIR, "assets/permanent_archive")
LOG_PATH = os.path.join(BASE_DIR, 'download_ingestion.log')
CSV_PATH = os.path.join(BASE_DIR, 'mapped_wa_universe_verified.csv')

logging.basicConfig(filename=LOG_PATH, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Robust session handling with retries
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))

def verify_jurisdiction(jurisdiction_id, expected_name):
    url = f"https://webapi.legistar.com/v1/{jurisdiction_id}/"
    try:
        # User-agent rotation/consistency
        resp = session.get(url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code == 200:
            client_name = resp.json().get('ClientName', '').lower()
            if expected_name.lower() in client_name and ("wa" in client_name or "washington" in client_name):
                return True
            else:
                logging.warning(f"VERIFICATION_FAIL: {jurisdiction_id} | Expected '{expected_name}', got '{client_name}'")
                return False
        return False
    except Exception as e:
        logging.error(f"VERIFICATION_ERROR: {jurisdiction_id} | {e}")
        return False

def download_pdf(url, jurisdiction, event_id, doc_type, date):
    if not url:
        return
    
    safe_date = date[:10]
    filename = f"{jurisdiction}_{safe_date}_{event_id}_{doc_type}.pdf"
    file_path = os.path.join(ARCHIVE_DIR, filename)
    
    if os.path.exists(file_path):
        return

    try:
        resp = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if resp.status_code == 200:
            with open(file_path, "wb") as f: 
                f.write(resp.content)
            print(f"   [DOWNLOADED] {filename}")
        else:
            logging.error(f"DOWNLOAD_FAIL: {jurisdiction} | {event_id} | {doc_type} | Status: {resp.status_code}")
    except Exception as e:
        logging.error(f"DOWNLOAD_FAIL: {jurisdiction} | {event_id} | {doc_type} | Error: {e}")

def process_jurisdiction(jurisdiction_id, expected_name):
    if not jurisdiction_id or jurisdiction_id.strip() == "":
        return
    
    if not verify_jurisdiction(jurisdiction_id, expected_name):
        return

    print(f"\nProcessing {expected_name} ({jurisdiction_id})...")
    url = f"https://webapi.legistar.com/v1/{jurisdiction_id}/events?$filter=EventDate ge datetime'2026-01-01T00:00:00' and EventDate le datetime'2026-12-31T23:59:59'&$orderby=EventDate desc"
    try:
        resp = session.get(url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code != 200:
            return
            
        events = resp.json()
        for event in events:
            event_id = str(event.get('EventId'))
            date = event.get('EventDate', 'unknown')
            download_pdf(event.get('EventAgendaFile'), jurisdiction_id, event_id, "Agenda", date)
            download_pdf(event.get('EventMinutesFile'), jurisdiction_id, event_id, "Minutes", date)
            # Gentle pacing: 2 second delay between docs
            time.sleep(2)
        # Gentle pacing: 5 second delay between jurisdictions
        time.sleep(5)
    except Exception as e:
        logging.error(f"SYSTEM_FAIL: {jurisdiction_id} | {e}")

if __name__ == "__main__":
    if not os.path.exists(CSV_PATH):
        exit(1)
        
    with open(CSV_PATH, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            jurisdiction = row.get('ID')
            name = row.get('Name')
            if jurisdiction:
                process_jurisdiction(jurisdiction, name)
