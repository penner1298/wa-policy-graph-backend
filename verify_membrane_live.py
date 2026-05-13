import requests
import os
from dotenv import load_dotenv

load_dotenv("/Users/thejoshpenner/.openclaw/workspace/contract-scanner-demo/backend/.env")
key = os.environ.get("MEMBRANE_API_KEY")
print(f"Using Key ending in: {key[-4:] if key else 'NONE'}")

url = "https://membrane-api.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}
payload = {
    "model": "membrane-engagement-layer",
    "messages": [{"role": "user", "content": "test connection. reply with 'OK'"}]
}

try:
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
