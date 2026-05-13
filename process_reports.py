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
load_dotenv(os.path.join(BASE_DIR, "../contract-scanner-demo/backend/.env"))

MEMBRANE_API_KEY = os.environ.get("MEMBRANE_API_KEY")
MEMBRANE_URL = "https://membrane-api.com/v1/chat/completions" # Centralized Membrane endpoint

# DB Setup
DB_PATH = os.path.join(BASE_DIR, 'municipal_intent.db')
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Schema Setup
c.execute('''CREATE TABLE IF NOT EXISTS audit_findings
             (report_num TEXT PRIMARY KEY, jurisdiction TEXT, type TEXT, category TEXT, summary TEXT, root_cause TEXT, dollar_impact INTEGER)''')
conn.commit()

class AuditFinding(BaseModel):
    category: str = Field(description="Broad category (Procurement, Internal Controls, State Law, Financial, Misappropriation)")
    summary: str = Field(description="1-2 sentence blunt summary of the finding. No fluff.")
    root_cause: str = Field(description="The structural or administrative failure that caused the finding.")
    dollar_impact: int = Field(description="Total financial impact in USD. 0 if none.")

def extract_text(pdf_path, max_pages=20):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for i in range(min(max_pages, len(reader.pages))): 
            text += reader.pages[i].extract_text() + "\n"
        return text
    except Exception as e:
        print(f"  -> PDF Error: {e}")
        return ""

def call_membrane(prompt, schema):
    headers = {
        "Authorization": f"Bearer {MEMBRANE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "membrane-engagement-layer",
        "messages": [
            {"role": "system", "content": "You are a highly precise municipal audit analyzer. Extract data strictly and without conversational filler or fluff. Response must be in JSON format."},
            {"role": "user", "content": f"Extract the following data into a JSON object matching this schema: {json.dumps(schema.model_json_schema())}\n\nInput Text:\n{prompt}"}
        ],
        "max_tokens": 2048
    }

    try:
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            content = data['choices'][0]['message']['content']
            # Clean markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        else:
            print(f"  -> Membrane API Error: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"  -> System Error calling Membrane: {e}")
        return None

def process_audit_reports():
    print("\n--- Starting Membrane Ingestion: SAO Audit Reports ---")
    reports_dir = os.path.join(BASE_DIR, 'reports')
    if not os.path.exists(reports_dir):
        print(f"Error: Reports directory {reports_dir} not found.")
        return

    # Mock metadata mapping (real version should pull from SAO search API or a seed CSV)
    meta = {
        "1039605": {"jurisdiction": "Renton Housing Authority", "type": "Accountability"},
        "1039386": {"jurisdiction": "City of Granger", "type": "Accountability"},
        "1039553": {"jurisdiction": "City of Granger", "type": "Financial"},
        "1039484": {"jurisdiction": "City of Anacortes", "type": "Accountability"},
        "1039555": {"jurisdiction": "Centralia School District No 401", "type": "Financial"}
    }

    for fname in os.listdir(reports_dir):
        if not fname.endswith('.pdf'): continue
        rnum = fname.replace('.pdf', '')
        
        # Skip if already processed
        c.execute("SELECT report_num FROM audit_findings WHERE report_num=?", (rnum,))
        if c.fetchone():
            continue

        print(f"Processing Audit #{rnum}...")
        text = extract_text(os.path.join(reports_dir, fname))
        if not text.strip(): continue

        prompt = f"Analyze this Washington State Auditor report and extract the PRIMARY finding. High signal, zero fluff.\n\nReport Text:\n{text[:40000]}"
        
        res = call_membrane(prompt, AuditFinding)
        if res:
            jurisdiction = meta.get(rnum, {}).get("jurisdiction", "Unknown")
            rep_type = meta.get(rnum, {}).get("type", "Unknown")
            
            c.execute("INSERT OR REPLACE INTO audit_findings VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (rnum, jurisdiction, rep_type, 
                       res.get('category'), res.get('summary'), res.get('root_cause'), res.get('dollar_impact', 0)))
            conn.commit()
            print(f"  [SUCCESS] Category: {res.get('category')} | Impact: ${res.get('dollar_impact', 0)}")
        
        time.sleep(1) # Respect Membrane rate limits

if __name__ == "__main__":
    process_audit_reports()
