import requests
import os
from dotenv import load_dotenv
load_dotenv("/Users/thejoshpenner/.openclaw/workspace/contract-scanner-demo/backend/.env")
key = os.environ.get("MEMBRANE_API_KEY")
print(requests.get("https://membrane-wh1g.onrender.com/v1/models", headers={"Authorization": f"Bearer {key}"}).text)
