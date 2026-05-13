import requests
import json
import os
import time
import sqlite3
from pydantic import BaseModel, Field
from pypdf import PdfReader
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv("../contract-scanner-demo/backend/.env")

MEMBRANE_URL = "http://localhost:8000/api/chat"

db_path = 'sao_2024.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS findings
             (report_num TEXT PRIMARY KEY, jurisdiction TEXT, type TEXT, category TEXT, summary TEXT, root_cause TEXT, dollar_impact INTEGER)''')
conn.commit()

class Finding(BaseModel):
    category: str = Field(description="Broad category of finding (e.g., Procurement, Internal Controls, State Law Violation, Financial Statement Error, Misappropriation)")
    summary: str = Field(description="1-2 sentence description of the finding.")
    root_cause: str = Field(description="Why the issue occurred.")
    dollar_impact: int = Field(description="Financial impact in USD. 0 if none mentioned.")

schema_dict = Finding.model_json_schema()

def extract_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for i in range(min(15, len(reader.pages))): 
            text += reader.pages[i].extract_text() + "\n"
        return text
    except Exception as e:
        return ""

def fetch_list():
    url = "https://portal.sao.wa.gov/ReportSearch/Home/SearchReports"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = "pageSize=500&pageNumber=1&HasFindings=true&LocalGovernment=true&StateGovernment=false&PerformanceAudits=false&SpecialInvestigations=false&UseOfDeadlyForceInvestigation=false&PoliceCertificationAudit=false&StartDate=01/01/2024&EndDate=12/31/2024"
    resp = requests.post(url, headers=headers, data=payload)
    if resp.status_code == 200:
        return resp.json().get('data', [])
    return []

async def extract_via_membrane(client, rnum, pdf_path, title, rep_type):
    # Skip if already processed in the db
    c.execute("SELECT report_num FROM findings WHERE report_num=?", (rnum,))
    if c.fetchone():
        return -1.0 # signal already processed

    text = extract_text(pdf_path)
    if not text.strip(): return 0.0
    
    prompt = f"Analyze this Washington State Auditor report and extract the PRIMARY audit finding details. If there are multiple, pick the most severe one. Return strict JSON matching the schema.\n\nReport Text:\n{text[:40000]}"
    
    payload = {
        "prompt": prompt,
        "response_format": schema_dict,
        "use_global_cache": True
    }
    
    headers = {"Authorization": "Bearer test"}
    
    try:
        resp = await client.post(MEMBRANE_URL, headers=headers, json=payload, timeout=120.0)
        if resp.status_code == 200:
            data = resp.json()
            ans = json.loads(data.get('answer', '{}'))
            billed = data.get('billed_amount', 0.0)
            
            if ans and "category" in ans:
                c.execute("INSERT OR REPLACE INTO findings VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (rnum, title, rep_type, 
                           ans.get('category'), ans.get('summary'), ans.get('root_cause'), ans.get('dollar_impact')))
                conn.commit()
                return billed
    except Exception as e:
        print(f"Extraction Error on {rnum}: {e}")
    return 0.0

async def main():
    print("Initiating 2024 SAO Sweeper Full Run...")
    reports = fetch_list()
    total = len(reports)
    print(f"Total reports to process: {total}")
    
    os.makedirs("reports_2024", exist_ok=True)
    
    total_membrane_billed = 0.0
    processed_this_run = 0
    skipped = 0
    
    async with httpx.AsyncClient() as client:
        for i, r in enumerate(reports):
            rnum = r.get("AuditReportNumber")
            title = r.get("ReportTitle")
            rep_type = r.get("AuditTypeName", "Unknown")
            pdf_link = r.get("AuditReportLink")
            
            pdf_path = f"reports_2024/{rnum}.pdf"
            
            # Download if missing
            if not os.path.exists(pdf_path):
                print(f"[{i+1}/{total}] Downloading {rnum}...")
                pdf_resp = requests.get(pdf_link, headers={"User-Agent": "Mozilla/5.0"})
                if pdf_resp.status_code == 200:
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_resp.content)
                time.sleep(0.5)
            
            # Send to Membrane
            billed = await extract_via_membrane(client, rnum, pdf_path, title, rep_type)
            if billed == -1.0:
                skipped += 1
            elif billed > 0:
                print(f"[{i+1}/{total}] Successfully extracted {rnum} via Membrane.")
                total_membrane_billed += billed
                processed_this_run += 1
                
            await asyncio.sleep(0.5) # Rate limiting protection
            
    print("\n=========================================")
    print("2024 SWEEPER FULL RUN COMPLETE")
    print(f"Already in DB (Skipped): {skipped}")
    print(f"Successfully processed this run: {processed_this_run}")
    print(f"Actual Billed via Membrane API: ${total_membrane_billed:.4f}")
    print("=========================================")

if __name__ == "__main__":
    asyncio.run(main())
