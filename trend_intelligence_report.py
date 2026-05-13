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

def get_integrated_data():
    conn = sqlite3.connect(DB_PATH)
    # Get recent spending intent
    c = conn.cursor()
    c.execute("SELECT jurisdiction, agenda_item_title, key_action, vendor, dollar_amount FROM processed_intent WHERE dollar_amount > 0 ORDER BY dollar_amount DESC LIMIT 30")
    spending = [dict(zip(['city', 'item', 'action', 'vendor', 'amount'], row)) for row in c.fetchall()]
    conn.close()

    # Get historical findings for those cities
    cities = list(set([s['city'] for s in spending]))
    conn_audit = sqlite3.connect(AUDIT_DB_PATH)
    c_audit = conn_audit.cursor()
    placeholders = ', '.join(['?'] * len(cities))
    # Using LIKE to match variations of city names
    audit_findings = []
    for city in cities:
        c_audit.execute("SELECT jurisdiction, category, summary FROM findings WHERE jurisdiction LIKE ?", (f"%{city}%",))
        audit_findings.extend([dict(zip(['city', 'category', 'summary'], row)) for row in c_audit.fetchall()])
    conn_audit.close()

    return {"spending": spending, "audits": audit_findings}

def run_trend_report():
    print("--- GENERATING STRATEGIC TREND REPORT ---")
    data = get_integrated_data()
    
    headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
    
    prompt = f"""You are a Municipal Strategy Intelligence Agent. 
    Analyze the following integrated data of current spending intent and historical audit failures.
    
    DATA:
    {json.dumps(data, indent=2)}
    
    SURFACE 3 KEY TRENDS:
    1. 'The Accountability Gap': Where is money flowing despite proven control failures?
    2. 'Vendor Dominance': Are specific vendors appearing across multiple jurisdictions or large contracts?
    3. 'Policy Velocity': Identify the most aggressive infrastructure or social policy push currently happening.
    
    Be blunt, data-driven, and brief."""

    payload = {
        "model": "membrane-engagement-layer",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=90)
        print(f"DEBUG Status: {resp.status_code}")
        if resp.status_code == 200:
            print(resp.json()['choices'][0]['message']['content'])
        else:
            print(f"DEBUG Error: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_trend_report()
