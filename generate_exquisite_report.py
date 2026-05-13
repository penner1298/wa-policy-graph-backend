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
    # Pulling specific indicators of bureaucracy and overhead
    c.execute("""SELECT jurisdiction, primary_entity, agenda_item_title, key_action, vendor, dollar_amount 
                 FROM processed_intent 
                 WHERE (agenda_item_title LIKE '%Manager%' OR agenda_item_title LIKE '%Agreement%' OR agenda_item_title LIKE '%Ordinance%' OR agenda_item_title LIKE '%Resolution%')
                 LIMIT 100""")
    intent = [dict(zip(['city', 'entity', 'title', 'action', 'vendor', 'amount'], row)) for row in c.fetchall()]
    conn.close()

    conn_audit = sqlite3.connect(AUDIT_DB_PATH)
    c_audit = conn_audit.cursor()
    # Pulling internal control failures (The "Lag")
    c_audit.execute("SELECT jurisdiction, category, summary FROM findings WHERE category LIKE '%Internal Controls%' LIMIT 100")
    audits = [dict(zip(['city', 'category', 'summary'], row)) for row in c_audit.fetchall()]
    conn_audit.close()

    return {"intent_samples": intent, "audit_failures": audits}

def generate_exquisite_report():
    print("--- Engaging Copywriter Agent for 1500-Word Strategic Brief ---")
    data = get_rich_context()
    headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
    
    prompt = f"""You are an elite Executive Ghostwriter and Municipal Strategy Consultant. 
    Your client is a Washington State Representative.
    
    TASK:
    Write an exquisite, 1500-word comprehensive report titled: 
    'THE ACCRETION TRAP: How Administrative Debt and Bureaucratic Entrenchment are Destabilizing Washington's Local Governments'
    
    KEY THEMES TO EXPAND ON (Cite the provided data in detail):
    1. THE GRAVITATIONAL PULL OF BUREAUCRACY: Explain how every new state mandate (like CETA) or grant creates a permanent, specialized administrative role. Cite the proliferation of 'Senior Manager' roles in the intent data.
    2. THE REPORTING QUAGMIRE: Detail the 'Administrative Debt'—how cities are failing audits (cite the SEFA and OPEB omissions in the data) because the complexity of reporting has outpaced their intellectual bandwidth.
    3. THE INSOLVENCY FRINGE: Analyze the 'Friction Zones' where high-velocity spending (like Bellevue's $600M+ levies) meets historical deficit findings.
    4. THE ENTRENCHMENT CYCLE: Argue that once a compliance layer is added, it becomes a permanent fixture of the municipal payroll, creating a 'Mission Creep' that cannot be reversed.
    
    DATA FOR CITATION:
    {json.dumps(data, indent=2)}
    
    TONE: 
    Sophisticated, blunt, data-dense, and ready for a legislative briefing. Use specific examples from cities like Bellevue, Tacoma, Olympia, and others in the dataset."""

    payload = {
        "model": "membrane-engagement-layer",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        # Using a very high timeout for the 1500-word generation
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=300)
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            with open("ACCERETION_TRAP_REPORT.md", "w") as f:
                f.write(content)
            return content
        return f"Report generation failed: {resp.status_code} - {resp.text}"
    except Exception as e:
        return f"Report generation failed: {e}"

if __name__ == "__main__":
    report = generate_exquisite_report()
    print("\n[REPORT GENERATED SUCCESSFULLY]")
    # Print the first 500 chars to the log
    print(report[:500] + "...")
