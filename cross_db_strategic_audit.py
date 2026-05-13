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

def run_cross_db_analysis():
    print(f"--- Initiating Cross-Database Strategic Audit ---")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT jurisdiction, category, summary, dollar_impact FROM audit_findings")
    audits = c.fetchall()
    c.execute("SELECT jurisdiction, key_action, dollar_amount FROM processed_intent WHERE dollar_amount > 1000000 ORDER BY dollar_amount DESC LIMIT 5")
    spending = c.fetchall()
    conn.close()

    headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
    
    # Minimal string payload
    data_str = f"Historical Audits: {str(audits)}\nCurrent High Spending: {str(spending)}"
    
    payload = {
        "model": "membrane-engagement-layer",
        "messages": [
            {"role": "system", "content": "You are a municipal risk analyst. Identify if current high spending matches historical audit failure categories (Internal Controls, Financial, Procurement)."},
            {"role": "user", "content": data_str}
        ]
    }
    
    try:
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            print(f"\n[CROSS-DB AUDIT RESULT]\n")
            print(resp.json()['choices'][0]['message']['content'])
        else:
            print(f"Error: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_cross_db_analysis()
