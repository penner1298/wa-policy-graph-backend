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

async def extract_via_membrane(client, rnum, pdf_path, title, rep_type):
    text = extract_text(pdf_path)
    if not text.strip(): return None
    
    prompt = f"Analyze this Washington State Auditor report and extract the PRIMARY audit finding details. If there are multiple, pick the most severe one. Return strict JSON matching the schema.\n\nReport Text:\n{text[:40000]}"
    
    payload = {
        "prompt": prompt,
        "response_format": schema_dict,
        "use_global_cache": True
    }
    
    # We use "test" as the Bearer token for local gearbox.py
    headers = {"Authorization": "Bearer test"}
    
    try:
        # Time the request
        start_t = time.time()
        resp = await client.post(MEMBRANE_URL, headers=headers, json=payload, timeout=120.0)
        dur = time.time() - start_t
        
        if resp.status_code == 200:
            data = resp.json()
            ans = json.loads(data.get('answer', '{}'))
            
            # Print the exact Membrane economics tracking
            billed = data.get('billed_amount', 0.0)
            savings = data.get('savings_percent', 0.0)
            route = data.get('route_used', 'UNKNOWN')
            print(f"[Membrane] Route: {route} | Billed: ${billed:.4f} | Savings: {savings:.1f}% | Time: {dur:.1f}s")
            
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
    print("Connecting to local Membrane Engine (gearbox.py)...")
    
    files = [f for f in os.listdir("reports_2024") if f.endswith('.pdf')]
    print(f"Found {len(files)} PDFs downloaded.")
    
    total_membrane_billed = 0.0
    successful = 0
    
    async with httpx.AsyncClient() as client:
        # Process a small batch to get the economics read
        for i, fname in enumerate(files[:10]):
            rnum = fname.replace(".pdf", "")
            pdf_path = f"reports_2024/{fname}"
            
            print(f"[{i+1}/10] Sending {rnum} through Membrane API...")
            billed = await extract_via_membrane(client, rnum, pdf_path, "Unknown", "Unknown")
            if billed is not None:
                total_membrane_billed += billed
                successful += 1
            await asyncio.sleep(0.5)
            
    print("\n=========================================")
    print("MEMBRANE ACTUAL COST REPORT (10 Reports)")
    print(f"Successfully processed: {successful}")
    print(f"Actual Billed via Membrane API: ${total_membrane_billed:.4f}")
    print("=========================================")

if __name__ == "__main__":
    asyncio.run(main())
