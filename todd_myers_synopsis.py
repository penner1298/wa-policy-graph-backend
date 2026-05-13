import os
import sqlite3
import requests
import json
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "../contract-scanner-demo/backend/.env"))

MEMBRANE_API_KEY = os.environ.get("MEMBRANE_API_KEY")
MEMBRANE_URL = "https://membrane-api.com/v1/chat/completions"

def generate_todd_synopsis():
    # Context: A State Representative reaching out to a Policy Director at Washington Policy Center.
    # Focus: High-resolution data on municipal spending vs audit failures.
    
    prompt = """You are a Strategic Communications Director for a Washington State Representative.
    
    TASK:
    Write a 1-paragraph synopsis to Todd Myers (Washington Policy Center).
    
    KEY VALUE PROPOSITION:
    Explain that we have built an integrated intelligence engine that cross-references 100% of Washington State Auditor findings with real-time municipal meeting data. 
    Mention that we've identified the 'Accretion Trap'—where billions in state mandates (like CETA) are creating permanent bureaucratic layers and 'Admin Debt' in local governments that auditors are only catching years later.
    
    TONE: 
    Professional, data-dense, and focused on government accountability and fiscal transparency.
    
    Limit the response to exactly ONE paragraph."""

    headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "membrane-engagement-layer",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        return "Failed to generate synopsis."
    except:
        return "Connection failed."

if __name__ == "__main__":
    print(generate_todd_synopsis())
