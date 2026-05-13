import requests
import json

url = "https://portal.sao.wa.gov/ReportSearch/Home/SearchReports"
headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
response = requests.post(url, headers=headers, data={
    "take": 10,
    "skip": 0,
    "page": 1,
    "pageSize": 10
})

if response.status_code == 200:
    try:
        data = response.json()
        print("Total reports:", data.get('Total'))
        print("Sample:", json.dumps(data.get('Data', [])[0], indent=2))
    except Exception as e:
        print("Error parsing JSON:", e)
else:
    print("Failed", response.status_code, response.text[:200])
