import os
import json
import sqlite3
import time
import requests
from pypdf import PdfReader
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import logging

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, 'live_ingestion_2026.log')

logging.basicConfig(filename=LOG_PATH, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv(os.path.join(BASE_DIR, "../contract-scanner-demo/backend/.env"))

MEMBRANE_API_KEY = os.environ.get("MEMBRANE_API_KEY")
MEMBRANE_URL = "https://membrane-api.com/v1/chat/completions"

# DB Setup
DB_PATH = os.path.join(BASE_DIR, 'municipal_intent.db')
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Universal Item Schema
c.execute('''CREATE TABLE IF NOT EXISTS processed_intent
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              file_id TEXT, jurisdiction TEXT, meeting_date TEXT, 
              event_id TEXT, doc_type TEXT, 
              item_number TEXT, agenda_item_title TEXT, 
              key_action TEXT, vendor TEXT, 
              dollar_amount INTEGER, vote_outcome TEXT)''')
conn.commit()

class IntentItem(BaseModel):
    item_number: str
    agenda_item_title: str
    key_action: str
    vendor: str
    dollar_amount: int
    vote_outcome: str

def process_full_agenda_or_minutes(file_id, jurisdiction, date, event_id, doc_type, full_text):
    headers = {
        "Authorization": f"Bearer {MEMBRANE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "membrane-engagement-layer",
        "messages": [
            {"role": "system", "content": f"""You are a municipal document data entry specialist. 
            Extract EVERY single agenda item or minute entry from this {doc_type}. Do not skip items. 
            
            CRITICAL JURISDICTIONAL RULE:
            Identify the specific LEGAL ENTITY that is the subject of each item. 
            For example, distinguish between 'City of Bellevue' and 'Bellevue School District'. 
            They are separate taxing authorities. Do not mislabel School District items as City items.

            For EVERY item, provide:
            1. item_number
            2. primary_entity (e.g., 'Bellevue School District', 'City of Bellevue', 'Sound Transit')
            3. agenda_item_title
            4. key_action (1-2 sentence blunt summary)
            5. vendor (If funds are being paid, else 'None')
            6. dollar_amount (Integer, 0 if NA)
            7. vote_outcome

            Return a JSON object with a key 'items' containing an array of these entries."""},
            {"role": "user", "content": f"Extract all items from this {jurisdiction} {doc_type} ({date}):\n\n{prompt}"}
        ]
    }
    try:
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=240)
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            if "```json" in content: content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content: content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content).get('items', [])
        return []
    except Exception as e:
        logging.error(f"Membrane API Error: {e}")
        return []

def extract_pdf_text(url, doc_type, event_id, jurisdiction, date):
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if resp.status_code != 200: return ""
        
        # PERMANENT STORAGE: Save to vault/meetings/{jurisdiction}/
        save_dir = os.path.join(BASE_DIR, 'vault', 'meetings', jurisdiction)
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{jurisdiction}_{date}_{event_id}_{doc_type}.pdf"
        pdf_path = os.path.join(save_dir, filename)
        
        with open(pdf_path, "wb") as f: f.write(resp.content)
        
        reader = PdfReader(pdf_path)
        text = ""
        for i in range(min(50, len(reader.pages))): text += reader.pages[i].extract_text() + "\n"
        return text
    except Exception as e:
        logging.error(f"PDF Extraction Error: {e}")
        return ""

def process_legistar(jurisdiction_id):
    print(f"Fetching 2026 Meetings for {jurisdiction_id}...")
    url = f"https://webapi.legistar.com/v1/{jurisdiction_id}/events?$filter=EventDate ge datetime'2026-01-01T00:00:00'&$orderby=EventDate desc"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"  [ERROR] Legistar API returned {resp.status_code}")
            return
        events = resp.json()
        for event in events:
            event_id = str(event.get('EventId'))
            meeting_date = event.get('EventDate')[:10]
            
            docs = [
                ('Agenda', event.get('EventAgendaFile')),
                ('Minutes', event.get('EventMinutesFile'))
            ]
            
            for doc_type, doc_url in docs:
                if not doc_url: continue
                
                file_id = f"{jurisdiction_id}_{meeting_date}_{event_id}_{doc_type}.pdf"
                
                # Check if already processed
                c.execute("SELECT id FROM processed_intent WHERE file_id = ? LIMIT 1", (file_id,))
                if c.fetchone(): continue

                print(f"-> Processing {jurisdiction_id} {doc_type} ({meeting_date})...")
                text = extract_pdf_text(doc_url, doc_type, event_id, jurisdiction_id, meeting_date)
                if not text.strip(): continue
                
                items = call_membrane(text[:50000], doc_type, meeting_date, jurisdiction_id)
                if items:
                    for item in items:
                        c.execute("""INSERT INTO processed_intent 
                                     (file_id, jurisdiction, meeting_date, event_id, doc_type, 
                                      item_number, primary_entity, agenda_item_title, key_action, vendor, dollar_amount, vote_outcome)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                  (file_id, jurisdiction_id, meeting_date, event_id, doc_type,
                                   item.get('item_number'), item.get('primary_entity'), item.get('agenda_item_title'), item.get('key_action'), 
                                   item.get('vendor'), item.get('dollar_amount'), item.get('vote_outcome')))
                    conn.commit()
                    print(f"   [SUCCESS] Saved {len(items)} items.")
                time.sleep(1)
    except Exception as e:
        print(f"Error processing {jurisdiction_id}: {e}")

if __name__ == "__main__":
    targets = [
        "clark", "snohomish", "douglascounty", "whatcom", "kingcounty",
        "olympia", "camas", "cityoflacrosse", "longbeach", "cityofdeerpark",
        "cityoftacoma", "cityofnorthport", "redmond", "mesa", "cityofmalden",
        "blaine", "mansfield", "toledo", "bellevue", "seattle"
    ]
    for target in targets:
        if target == "clark": continue # Skipping NV-based Clark County
        process_legistar(target)
