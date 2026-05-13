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

def get_lean_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT primary_entity, key_action, dollar_amount FROM processed_intent WHERE primary_entity IS NOT NULL ORDER BY id DESC LIMIT 20")
    items = c.fetchall()
    conn.close()
    return items

def run_short_report():
    data = get_lean_data()
    prompt = f"Entities and Spending: {str(data)}\n\nIdentify the highest spending entity in this list and summarize their risk based on having multiple taxing authorities in one meeting."
    
    headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "membrane-engagement-layer",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        return "Analysis failed due to API status."
    except:
        return "Analysis failed due to connection."

if __name__ == "__main__":
    print(run_short_report())
