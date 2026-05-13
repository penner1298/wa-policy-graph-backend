import os
import json
import sqlite3
import google.generativeai as genai
from pypdf import PdfReader
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import time

load_dotenv("../contract-scanner-demo/backend/.env")

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

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

def extract_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for i in range(min(15, len(reader.pages))): 
            text += reader.pages[i].extract_text() + "\n"
        return text
    except Exception as e:
        return ""

def main():
    print("Processing downloaded 2024 SAO Reports...")
    total_tokens = 0
    successful = 0
    
    files = [f for f in os.listdir("reports_2024") if f.endswith('.pdf')]
    print(f"Found {len(files)} PDFs downloaded.")
    
    for i, fname in enumerate(files):
        rnum = fname.replace(".pdf", "")
        pdf_path = f"reports_2024/{fname}"
        
        # Check if already in DB
        c.execute("SELECT report_num FROM findings WHERE report_num=?", (rnum,))
        if c.fetchone():
            print(f"[{i+1}/{len(files)}] {rnum} already in DB, skipping.")
            continue
            
        print(f"[{i+1}/{len(files)}] Processing {rnum}...")
        text = extract_text(pdf_path)
        if not text.strip(): continue
        
        prompt = f"Analyze this Washington State Auditor report and extract the PRIMARY audit finding details. If there are multiple, pick the most severe one. Return strict JSON matching the schema.\n\nReport Text:\n{text[:40000]}"
        
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=Finding
                )
            )
            
            tokens = len(text[:40000]) // 4
            total_tokens += tokens
            
            res = json.loads(response.text)
            
            # Since we downloaded asynchronously and lost the metadata dictionary, we'll just insert "Unknown" 
            # for jurisdiction and type for now, and rely on the finding payload to prove the economics.
            c.execute("INSERT OR REPLACE INTO findings VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (rnum, "Unknown (Batch Run)", "Unknown", 
                       res['category'], res['summary'], res['root_cause'], res['dollar_impact']))
            conn.commit()
            successful += 1
            print(f"  -> Extracted: {res['category']} - ${res['dollar_impact']} impact")
        except Exception as e:
            print(f"  -> Error: {e}")
            
        time.sleep(1) # Prevent rate limits
            
    cost = (total_tokens / 1_000_000) * 0.075
    print("\n=========================================")
    print("2024 SWEEPER BATCH COMPLETE")
    print(f"Successfully processed: {successful}")
    print(f"Estimated Tokens processed: {total_tokens}")
    print(f"Estimated API Cost (Flash): ${cost:.4f}")
    print("=========================================")

if __name__ == "__main__":
    main()
