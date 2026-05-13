import requests
import json
import os
import google.generativeai as genai
from pydantic import BaseModel, Field
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv("../contract-scanner-demo/backend/.env")
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

# 1. Look up a specific agenda from Seattle that might have money attached
# We'll grab the City Council meeting on 2026-01-06 Agenda PDF instead of Minutes
agenda_url = "https://legistar2.granicus.com/seattle/meetings/2026/1/6509_A_City_Council_26-01-06_Full_Council_Meeting_Agenda.pdf"

class DetailedAgenda(BaseModel):
    items: list[dict] = Field(description="A list of all significant financial or contract items on the agenda.")
    
    # We define the schema for each item explicitly to catch money
    class Config:
        json_schema_extra = {
            "properties": {
                "items": {
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string", "description": "What is being voted on?"},
                            "contractor_or_vendor": {"type": "string", "description": "Who is getting the money?"},
                            "anticipated_cost": {"type": "integer", "description": "The exact dollar amount requested or contracted. 0 if not mentioned."}
                        },
                        "required": ["description", "anticipated_cost"]
                    }
                }
            }
        }

def main():
    print("Downloading Agenda PDF...")
    resp = requests.get(agenda_url, headers={"User-Agent": "Mozilla/5.0"})
    with open("temp_agenda.pdf", "wb") as f:
        f.write(resp.content)
        
    reader = PdfReader("temp_agenda.pdf")
    text = ""
    for i in range(len(reader.pages)): 
        text += reader.pages[i].extract_text() + "\n"
        
    print("Extracting financial details via Membrane...")
    prompt = f"Extract all contract approvals, funding requests, and financial allocations from this agenda. Ignore roll calls, adoptions of past minutes, and procedural votes. Return strict JSON.\n\nAgenda:\n{text}"
    
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=DetailedAgenda
        )
    )
    
    print("\n--- EXTRACTED AGENDA FINANCIALS ---")
    data = json.loads(response.text)
    for item in data.get('items', []):
        print(f"Vendor/Contract: {item.get('contractor_or_vendor', 'None')}")
        print(f"Cost: ${item.get('anticipated_cost', 0):,}")
        print(f"Details: {item.get('description')}\n")
        
if __name__ == "__main__":
    main()
