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
    # Capture items related to state-level interlocals, authority terminations, or state mandates
    c.execute("""SELECT jurisdiction, primary_entity, agenda_item_title, key_action, dollar_amount 
                 FROM processed_intent 
                 WHERE (agenda_item_title LIKE '%State%' OR agenda_item_title LIKE '%Interlocal%' OR agenda_item_title LIKE '%Terminate%' OR agenda_item_title LIKE '%RCW%')
                 AND primary_entity IS NOT NULL
                 ORDER BY id DESC LIMIT 50""")
    recent_items = [dict(zip(['city', 'entity', 'title', 'action', 'amount'], row)) for row in c.fetchall()]
    conn.close()

    conn_audit = sqlite3.connect(AUDIT_DB_PATH)
    c_audit = conn_audit.cursor()
    # Audit findings citing State Law Violations or Financial Condition (the "Why")
    c_audit.execute("SELECT jurisdiction, category, summary FROM findings WHERE category LIKE '%State Law%' OR category LIKE '%Financial Condition%'")
    audit_findings = [dict(zip(['entity', 'category', 'summary'], row)) for row in c_audit.fetchall()]
    conn_audit.close()

    return {"intent_data": recent_items, "audit_data": audit_findings}

def run_legislative_nexus_analysis():
    data = get_integrated_data()
    headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
    
    prompt = f"""You are a Strategic Policy Advisor for a Washington State Representative. 
    Analyze the nexus between historical SAO Audit findings (State Law Violations/Financial Condition) and current Municipal Meeting Intent (Interlocal terminations/State-linked spending).
    
    DATA:
    {json.dumps(data, indent=2)}
    
    TASK:
    Develop a 'Legislative Thesis' for a State Representative. 
    Focus on:
    1. Where is state-authorized 'Interlocal' architecture failing (e.g. Regional Homelessness Authority)?
    2. What current municipal actions signal a need for State-level oversight or legislative reform?
    3. How does 'Financial Condition' risk in cities (like Bellevue School District or King County entities) create a legislative liability for the State?
    
    Be blunt, analytical, and ready for speech/text delivery."""

    payload = {
        "model": "membrane-engagement-layer",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=90)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        return f"Analysis failed: {resp.status_code}"
    except Exception as e:
        return f"Analysis failed: {e}"

if __name__ == "__main__":
    print(run_legislative_nexus_analysis())
