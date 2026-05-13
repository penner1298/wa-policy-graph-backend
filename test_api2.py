import requests
import json

url = "https://portal.sao.wa.gov/ReportSearch/Home/SearchReports?page=1&pageSize=10&take=10&skip=0"
headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
response = requests.get(url, headers=headers)

if response.status_code == 200:
    try:
        data = response.json()
        print("Total reports:", data.get('Total'))
        if data.get('Data'):
            print("Sample:", json.dumps(data.get('Data')[0], indent=2))
        else:
            print("No data")
    except Exception as e:
        print("Error parsing JSON:", e)
else:
    print("Failed", response.status_code, response.text[:200])
