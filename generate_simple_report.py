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

def get_rich_context():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT jurisdiction, agenda_item_title, key_action, dollar_amount FROM processed_intent LIMIT 30")
    intent = c.fetchall()
    conn.close()

    conn_audit = sqlite3.connect(AUDIT_DB_PATH)
    c_audit = conn_audit.cursor()
    c_audit.execute("SELECT jurisdiction, summary FROM findings LIMIT 30")
    audits = c_audit.fetchall()
    conn_audit.close()
    return {"intent": intent, "audits": audits}

def generate_report():
    data = get_rich_context()
    headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
    
    prompt = f"""Write a professional report titled: 'THE ACCRETION TRAP'.
    Explain how new mandates and reporting requirements create permanent bureaucratic layers in local government.
    
    Use these data points:
    INTENT: {str(data['intent'])}
    AUDITS: {str(data['audits'])}
    
    Structure the report with these sections:
    1. Introduction: The Capacity Gap.
    2. Section A: The Admin Debt (Audit failures).
    3. Section B: Entrenched Overhead (Permanent roles).
    4. Conclusion: Legislative recommendations.
    
    The report should be blunt and detailed."""

    payload = {
        "model": "membrane-engagement-layer",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=240)
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            with open("ACCRETION_TRAP_REPORT.md", "w") as f:
                f.write(content)
            return content
        return f"Error: {resp.status_code}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    print(generate_report())
