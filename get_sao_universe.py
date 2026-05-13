import requests
import json

# The SAO portal has a master list of all entities it audits.
# Let's try to hit the endpoint that populates the "Entity Name" dropdown.
url = "https://portal.sao.wa.gov/ReportSearch/Home/GetClientList"

try:
    resp = requests.post(url, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}, json={"searchTerm": ""})
    if resp.status_code == 200:
        data = resp.json()
        print(f"Success! Pulled {len(data)} entities from SAO master list.")
        # print first 5
        for i in range(5):
            print(data[i])
    else:
        print(f"Failed. Status: {resp.status_code}")
except Exception as e:
    print(f"Error: {e}")

