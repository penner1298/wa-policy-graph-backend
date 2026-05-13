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

def get_temporal_context():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Current 2026 Actions
    c.execute("SELECT jurisdiction, agenda_item_title, meeting_date FROM processed_intent WHERE meeting_date LIKE '2026%' LIMIT 30")
    current_actions = c.fetchall()
    conn.close()

    conn_audit = sqlite3.connect(AUDIT_DB_PATH)
    c_audit = conn_audit.cursor()
    # Historical Findings (mostly 2022-2024 reporting years)
    c_audit.execute("SELECT jurisdiction, summary FROM findings LIMIT 30")
    historical_findings = c_audit.fetchall()
    conn_audit.close()

    return {"current_2026_actions": current_actions, "historical_audit_findings": historical_findings}

def run_legislative_analysis():
    data = get_temporal_context()
    headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
    
    prompt = f"""You are a Strategic Policy Advisor for a State Representative. 
    Review this temporal data:
    2026 ACTIONS: {str(data['current_2026_actions'])}
    HISTORICAL AUDIT FINDINGS (Prior 2-3 years): {str(data['historical_audit_findings'])}
    
    TASK:
    1. Confirm that we are seeing CURRENT (2026) legislative intent reacting to HISTORICAL (2023-2024) failures.
    2. Define the 'Legislative Cause': Why is this breakdown happening now?
    3. Define the 'Legislative Solution': What specific reform can the Representative propose to fix this cycle?
    
    Format as a blunt, analytical thesis for the Representative."""

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
    print(run_legislative_analysis())
