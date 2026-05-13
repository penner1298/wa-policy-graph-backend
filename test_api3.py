import requests
import json

url = "https://portal.sao.wa.gov/ReportSearch/Home/SearchReports"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded"
}

# Add HasFindings=true because we specifically want findings!
payload = "pageSize=10&pageNumber=1&HasFindings=true&StateGovernment=false&LocalGovernment=true&PerformanceAudits=false&SpecialInvestigations=false&UseOfDeadlyForceInvestigation=false&PoliceCertificationAudit=false"

response = requests.post(url, headers=headers, data=payload)

if response.status_code == 200:
    try:
        data = response.json()
        print("Total reports:", data.get('total'))
        if data.get('data'):
            print("Sample:", json.dumps(data.get('data')[0], indent=2))
        else:
            print("No data")
    except Exception as e:
        print("Error parsing JSON:", e)
else:
    print("Failed", response.status_code, response.text[:200])
