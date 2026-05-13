import requests
import os
from dotenv import load_dotenv

load_dotenv("/Users/thejoshpenner/.openclaw/workspace/contract-scanner-demo/backend/.env")
key = os.environ.get("MEMBRANE_API_KEY")

# Test Public
print("Testing Public URL: https://membrane-api.com/v1/chat/completions")
resp = requests.post("https://membrane-api.com/v1/chat/completions", 
                     headers={"Authorization": f"Bearer {key}"}, 
                     json={"model": "membrane-engagement-layer", "messages": [{"role": "user", "content": "test"}]})
print(f"Public Status: {resp.status_code}")

# Test Render
print("\nTesting Render URL: https://membrane-wh1g.onrender.com/v1/chat/completions")
resp2 = requests.post("https://membrane-wh1g.onrender.com/v1/chat/completions", 
                      headers={"Authorization": f"Bearer {key}"}, 
                      json={"model": "membrane-engagement-layer", "messages": [{"role": "user", "content": "test"}]})
print(f"Render Status: {resp2.status_code}")
