import os
import json
import sqlite3
import time
import requests
from pypdf import PdfReader
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# ==========================================
# CONFIGURATION
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "../contract-scanner-demo/backend/.env"))

MEMBRANE_API_KEY = os.environ.get("MEMBRANE_API_KEY")
MEMBRANE_URL = "https://membrane-api.com/v1/chat/completions"
ARCHIVE_DIR = os.path.join(BASE_DIR, "assets", "permanent_archive")

# ==========================================
# DATABASE SETUP
# ==========================================
DB_PATH = os.path.join(BASE_DIR, 'municipal_intent.db')
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# ==========================================
# LOGIC
# ==========================================

def is_file_processed(file_id):
    c.execute("SELECT id FROM processed_intent WHERE file_id = ? LIMIT 1", (file_id,))
    return c.fetchone() is not None

def extract_raw_text(pdf_path, max_pages=100):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for i in range(min(max_pages, len(reader.pages))):
            page_text = reader.pages[i].extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        print(f"  -> PDF Error: {e}")
        return ""

def process_full_agenda_or_minutes(file_id, jurisdiction, date, event_id, doc_type, full_text):
    headers = {
        "Authorization": f"Bearer {MEMBRANE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "membrane-engagement-layer",
        "messages": [
            {"role": "system", "content": f"""You are a municipal document data entry specialist. 
            Extract EVERY single agenda item or minute entry. Do not skip items.
            
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
            {"role": "user", "content": f"Extract all items from this {jurisdiction} {doc_type} ({date}):\n\n{full_text}"}
        ]
    }

    try:
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=240)
        if resp.status_code == 200:
            data = resp.json()
            content = data['choices'][0]['message']['content']
            if "```json" in content: content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content: content = content.split("```")[1].split("```")[0].strip()
            
            # Print billing info for tracking
            meta = data.get('membrane_metadata', {})
            print(f"     [BILLING] Billed: ${meta.get('billed_amount', 0):.4f} | Status: {meta.get('status')}")
            
            return json.loads(content).get('items', [])
        else:
            print(f"  -> API Error: {resp.status_code}")
            return []
    except Exception as e:
        print(f"  -> System Error: {e}")
        return []

def run_full_archive_sweep():
    print(f"--- Membrane FULL ARCHIVE SWEEP (Key: ...{MEMBRANE_API_KEY[-4:]}) ---")
    files = sorted([f for f in os.listdir(ARCHIVE_DIR) if f.endswith('.pdf')])
    total = len(files)
    processed_count = 0
    skipped_count = 0
    
    for i, fname in enumerate(files):
        if is_file_processed(fname):
            skipped_count += 1
            continue
            
        parts = fname.replace('.pdf', '').split('_')
        if len(parts) < 4: continue
        jurisdiction, date, event_id, doc_type = parts[0], parts[1], parts[2], parts[3]
        
        print(f"[{i+1}/{total}] Processing: {fname}")
        full_text = extract_raw_text(os.path.join(ARCHIVE_DIR, fname))
        items = process_full_agenda_or_minutes(fname, jurisdiction, date, event_id, doc_type, full_text)
        
        if items:
            for item in items:
                c.execute("""INSERT INTO processed_intent 
                             (file_id, jurisdiction, meeting_date, event_id, doc_type, 
                              item_number, primary_entity, agenda_item_title, key_action, vendor, dollar_amount, vote_outcome)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                          (fname, jurisdiction, date, event_id, doc_type,
                           item.get('item_number'), item.get('primary_entity'), item.get('agenda_item_title'), item.get('key_action'), 
                           item.get('vendor'), item.get('dollar_amount'), item.get('vote_outcome')))
            conn.commit()
            processed_count += 1
            print(f"     [SUCCESS] Saved {len(items)} items.")
        
        time.sleep(1) # Rate limit protection

    print("\n=========================================")
    print("FULL ARCHIVE SWEEP COMPLETE")
    print(f"Total Files in Archive: {total}")
    print(f"Newly Processed: {processed_count}")
    print(f"Skipped (Already in DB): {skipped_count}")
    print("=========================================")

if __name__ == "__main__":
    run_full_archive_sweep()
