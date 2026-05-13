import os
import sqlite3
import requests
import json
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "../contract-scanner-demo/backend/.env"))

MEMBRANE_API_KEY = os.environ.get("MEMBRANE_API_KEY")
MEMBRANE_URL = "https://membrane-api.com/v1/chat/completions"
DB_PATH = os.path.join(BASE_DIR, 'municipal_intent.db')
AUDIT_DB_PATH = os.path.join(BASE_DIR, 'sao_2024.db')

def get_discovery_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT jurisdiction, primary_entity, agenda_item_title, key_action FROM processed_intent ORDER BY id DESC LIMIT 50")
    intent = c.fetchall()
    conn.close()

    conn_audit = sqlite3.connect(AUDIT_DB_PATH)
    c_audit = conn_audit.cursor()
    c_audit.execute("SELECT jurisdiction, category, summary FROM findings LIMIT 50")
    audits = c_audit.fetchall()
    conn_audit.close()

    return f"INTENT: {str(intent)}\n\nAUDITS: {str(audits)}"

def run_commonalities_discovery():
    data_str = get_discovery_data()
    headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
    
    prompt = f"Analyze these municipal datasets:\n{data_str}\n\nSurface 3 'HIDDEN' COMMONALITIES related to administrative debt (reporting failures), resource competition, and the conversion of 'pilot' projects into permanent payroll. Be extremely blunt and analytical."

    payload = {
        "model": "membrane-engagement-layer",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        return f"Discovery failed: {resp.status_code}"
    except Exception as e:
        return f"Discovery failed: {e}"

if __name__ == "__main__":
    print(run_commonalities_discovery())
