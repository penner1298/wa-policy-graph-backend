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

def test_membrane():
    print(f"--- Membrane Connection Diagnostic ---")
    print(f"Target URL: {MEMBRANE_URL}")
    print(f"API Key Found: {'Yes (ends in ...' + MEMBRANE_API_KEY[-4:] + ')' if MEMBRANE_API_KEY else 'No'}")
    
    headers = {
        "Authorization": f"Bearer {MEMBRANE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "membrane-engagement-layer",
        "messages": [
            {"role": "user", "content": "Return the word 'CONNECTED' in a JSON object with the key 'status'."}
        ]
    }
    
    try:
        print("Sending request...")
        resp = requests.post(MEMBRANE_URL, headers=headers, json=payload, timeout=30)
        
        print(f"HTTP Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Response Data:")
            print(json.dumps(resp.json(), indent=2))
            return True
        else:
            print(f"Error Body: {resp.text}")
            return False
            
    except Exception as e:
        print(f"Connection Failed: {e}")
        return False

if __name__ == "__main__":
    test_membrane()
