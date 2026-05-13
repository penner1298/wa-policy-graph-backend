import os
import requests
import json
from dotenv import load_dotenv

# Load credentials from the project .env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, "../contract-scanner-demo/backend/.env")
load_dotenv(ENV_PATH)

MEMBRANE_API_KEY = os.environ.get("MEMBRANE_API_KEY")
MEMBRANE_URL = "https://membrane-api.com/v1/chat/completions"

def test_connection():
    print(f"--- Membrane Key Verification ---")
    print(f"Using Key ending in: ...{MEMBRANE_API_KEY[-4:] if MEMBRANE_API_KEY else 'NONE'}")
    
    headers = {
        "Authorization": f"Bearer {MEMBRANE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "membrane-engagement-layer",
        "messages": [
            {"role": "user", "content": "Confirm connection. Respond with 'KEY_VERIFIED'."}
        ]
    }
    
    try:
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=20)
        print(f"HTTP Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Response:", resp.json()['choices'][0]['message']['content'])
            return True
        else:
            print(f"Error: {resp.text}")
            return False
    except Exception as e:
        print(f"Failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
