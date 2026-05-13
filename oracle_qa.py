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

def get_db_context():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM processed_intent")
    rows = c.fetchall()
    columns = [description[0] for description in c.description]
    data = [dict(zip(columns, row)) for row in rows]
    conn.close()
    return json.dumps(data, indent=2)

def ask_oracle(question):
    print(f"\n[ORACLE] Question: {question}")
    
    # NEW: First, ask Membrane to identify which jurisdictions are relevant to the question
    headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
    
    # Get list of unique jurisdictions in DB
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT jurisdiction FROM processed_intent")
    available_jurisdictions = [row[0] for row in cur.fetchall()]
    conn.close()

    routing_payload = {
        "model": "membrane-engagement-layer",
        "messages": [
            {"role": "system", "content": f"You are a data router. Given a question and a list of jurisdictions, return a comma-separated list of ONLY the jurisdictions that are relevant. Available: {', '.join(available_jurisdictions)}. If all or many are relevant, say 'all'."},
            {"role": "user", "content": question}
        ]
    }
    
    target_jurisdiction = "all"
    try:
        route_resp = requests.post(MEMBRANE_URL, headers=headers, json=routing_payload, timeout=30)
        if route_resp.status_code == 200:
            target_jurisdiction = route_resp.json()['choices'][0]['message']['content'].strip().lower()
    except: pass

    # Fetch ONLY the relevant rows
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if "all" in target_jurisdiction:
        c.execute("SELECT * FROM processed_intent")
    else:
        # Filter by identified jurisdiction
        juris_list = [j.strip() for j in target_jurisdiction.split(',')]
        placeholders = ', '.join(['?'] * len(juris_list))
        c.execute(f"SELECT * FROM processed_intent WHERE jurisdiction IN ({placeholders})", juris_list)
    
    rows = c.fetchall()
    columns = [description[0] for description in c.description]
    context = json.dumps([dict(zip(columns, row)) for row in rows], indent=2)
    conn.close()
    
    # Final answer call
    payload = {
        "model": "membrane-engagement-layer",
        "messages": [
            {"role": "system", "content": "You are a municipal data analyst. IMPORTANT: Your answer MUST specify which jurisdiction the data belongs to. Never mix them up. If multiple cities have similar projects, list them separately."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]
    }
    
    try:
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            print(f"[ORACLE] Answer: {resp.json()['choices'][0]['message']['content']}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    # Example Q&A set
    questions = [
        "What is the total dollar amount of all grants and contracts found in these 5 files?",
        "Who is 'Transpo Group USA, Inc.' and what project are they working on?",
        "Was any gas tax funding mentioned? If so, for what project and how much?",
        "Are there any items related to bike connections?"
    ]
    for q in questions:
        ask_oracle(q)
