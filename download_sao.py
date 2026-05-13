import requests
import json
import os
import time

url = "https://portal.sao.wa.gov/ReportSearch/Home/SearchReports"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded"
}
# Only local gov, has findings. 
payload = "pageSize=5&pageNumber=1&HasFindings=true&StateGovernment=false&LocalGovernment=true&PerformanceAudits=false&SpecialInvestigations=false&UseOfDeadlyForceInvestigation=false&PoliceCertificationAudit=false"

def main():
    print("Fetching WA SAO Audit Reports...")
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code != 200:
        print("Failed to fetch API")
        return
        
    data = response.json()
    reports = data.get('data', [])
    print(f"Found {data.get('total')} total reports. Downloading top 5...")
    
    os.makedirs("reports", exist_ok=True)
    
    for r in reports:
        report_num = r.get("AuditReportNumber")
        title = r.get("ReportTitle")
        pdf_link = r.get("AuditReportLink")
        
        print(f"-> Downloading {title} (Report {report_num})...")
        pdf_resp = requests.get(pdf_link, headers={"User-Agent": "Mozilla/5.0"})
        if pdf_resp.status_code == 200:
            pdf_path = f"reports/{report_num}.pdf"
            with open(pdf_path, "wb") as f:
                f.write(pdf_resp.content)
            print(f"   Saved to {pdf_path}")
        else:
            print(f"   Failed to download PDF.")
        time.sleep(1)

if __name__ == "__main__":
    main()
