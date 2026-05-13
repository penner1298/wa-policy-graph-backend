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

# Check for LOCAL membrane first
MEMBRANE_URL = "http://localhost:8000/api/chat"
MEMBRANE_API_KEY = os.environ.get("MEMBRANE_API_KEY", "sk-test")
ARCHIVE_DIR = os.path.join(BASE_DIR, "assets", "permanent_archive")

# ==========================================
# DATABASE SETUP
# ==========================================
DB_PATH = os.path.join(BASE_DIR, 'municipal_intent.db')
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS processed_intent
             (file_id TEXT PRIMARY KEY, jurisdiction TEXT, meeting_date TEXT, 
              event_id TEXT, doc_type TEXT, key_action TEXT, vendor TEXT, 
              dollar_amount INTEGER, vote_outcome TEXT)''')
conn.commit()

class IntentExtraction(BaseModel):
    key_action: str = Field(description="The single most significant policy, contract, or spending action.")
    vendor: str = Field(description="Contractor or agency receiving funds. 'None' if NA.")
    dollar_amount: int = Field(description="Total financial value. 0 if none.")
    vote_outcome: str = Field(description="Final vote result (e.g., 'Passed 7-0', 'Failed'). 'Unknown' if not mentioned.")

# ==========================================
# LOGIC
# ==========================================

def call_membrane(prompt, schema):
    headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
    
    payload = {
        "model": "membrane-engagement-layer",
        "messages": [
            {"role": "system", "content": "You are a highly precise municipal document analyzer. Extract intent strictly and without fluff. Response must be in JSON format."},
            {"role": "user", "content": f"Extract the following data into a JSON object matching this schema: {json.dumps(schema.model_json_schema())}\n\nInput Text:\n{prompt}"}
        ],
        "max_tokens": 2048
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        else:
            print(f"DEBUG: API returned {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"DEBUG: Exception: {e}")
        return None

def extract_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for i in range(min(15, len(reader.pages))): 
            text += reader.pages[i].extract_text() + "\n"
        return text
    except: return ""

def process_archive():
    print(f"Scanning Archive: {ARCHIVE_DIR}")
    files = [f for f in os.listdir(ARCHIVE_DIR) if f.endswith('.pdf')]
    print(f"Found {len(files)} physical files.")

    for i, fname in enumerate(files):
        parts = fname.replace('.pdf', '').split('_')
        if len(parts) < 4: continue
        jurisdiction, date, event_id, doc_type = parts[0], parts[1], parts[2], parts[3]
        
        c.execute("SELECT file_id FROM processed_intent WHERE file_id=?", (fname,))
        if c.fetchone(): continue

        print(f"[{i+1}/{len(files)}] Processing: {fname}")
        text = extract_text(os.path.join(ARCHIVE_DIR, fname))
        if not text.strip(): continue

        prompt = f"Analyze this {jurisdiction} {doc_type} from {date}. Extract the core intent.\n\nTEXT:\n{text[:30000]}"
        res = call_membrane(prompt, IntentExtraction)
        
        if res:
            c.execute("INSERT INTO processed_intent VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (fname, jurisdiction, date, event_id, doc_type,
                       res['key_action'], res['vendor'], res['dollar_amount'], res['vote_outcome']))
            conn.commit()
            print(f"   -> Saved: {res['key_action'][:50]}... (${res['dollar_amount']})")
        else:
            print("   -> Failed to get response from Membrane.")
        
        time.sleep(1)

if __name__ == "__main__":
    process_archive()
