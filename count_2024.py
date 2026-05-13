import requests

url = "https://portal.sao.wa.gov/ReportSearch/Home/SearchReports"
headers = {"User-Agent": "Mozilla/5.0"}
data = {
    "pageSize": 1,
    "pageNumber": 1,
    "HasFindings": "true",
    "LocalGovernment": "true",
    "StateGovernment": "false",
    "StartDate": "01/01/2024",
    "EndDate": "12/31/2024",
    "PoliceCertificationAudit": "false"
}

response = requests.post(url, headers=headers, data=data)
try:
    print(f"Total: {response.json().get('total')}")
except:
    print(response.status_code)
