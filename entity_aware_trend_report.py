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
    c = conn.cursor()
    # Focus on King County specific entities
    c.execute("SELECT primary_entity, agenda_item_title, key_action, dollar_amount FROM processed_intent WHERE primary_entity LIKE '%King County%' ORDER BY id DESC LIMIT 50")
    recent_items = [dict(zip(['entity', 'title', 'action', 'amount'], row)) for row in c.fetchall()]
    conn.close()

    conn_audit = sqlite3.connect(AUDIT_DB_PATH)
    c_audit = conn_audit.cursor()
    # Hard search for King County findings
    c_audit.execute("SELECT jurisdiction, category, summary FROM findings WHERE jurisdiction LIKE '%King County%' OR summary LIKE '%King County%'")
    audit_findings = [dict(zip(['entity', 'category', 'summary'], row)) for row in c_audit.fetchall()]
    conn_audit.close()

    return {"recent_items": recent_items, "historical_audits": audit_findings}

def run_entity_aware_report():
    data = get_integrated_data()
    headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
    
    prompt = f"""You are a senior Municipal Risk Auditor. 
    Analyze this integrated dataset of current King County actions and historical SAO findings.
    
    DATA:
    {json.dumps(data, indent=2)}
    
    TASK:
    Identify 'Accountability Gaps' for specific King County entities. 
    1. Specifically look for 'King County Flood Control District' or 'King County Transportation District' and the 'Regional Homelessness Authority'.
    2. Note if current legislative motions (like terminating interlocal agreements or imposing new sales taxes) overlap with historical failures in 'Internal Controls' or 'Financial Management'.
    
    Be blunt, brief, and mention the specific entity names."""

    payload = {
        "model": "membrane-engagement-layer",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=90)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        return f"Error: {resp.status_code}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    print(run_entity_aware_report())
