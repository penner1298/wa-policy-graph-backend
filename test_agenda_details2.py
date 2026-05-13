import requests
import json
import os
import google.genai as genai
from pydantic import BaseModel, Field
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv("../contract-scanner-demo/backend/.env")
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

agenda_url = "https://legistar2.granicus.com/seattle/meetings/2026/1/6538_A_Public_Safety_Committee_26-01-13_Committee_Agenda.pdf"

class AgendaItem(BaseModel):
    description: str = Field(description="What is being discussed or voted on?")
    contractor_or_vendor: str = Field(description="Who is getting the money? Return 'None' if NA.")
    anticipated_cost: int = Field(description="The exact dollar amount requested or contracted. 0 if not mentioned.")

class DetailedAgenda(BaseModel):
    items: list[AgendaItem]

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
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": DetailedAgenda,
        },
    )
    
    print("\n--- EXTRACTED AGENDA FINANCIALS ---")
    data = json.loads(response.text)
    for item in data.get('items', []):
        print(f"Vendor/Contract: {item.get('contractor_or_vendor', 'None')}")
        print(f"Cost: ${item.get('anticipated_cost', 0):,}")
        print(f"Details: {item.get('description')}\n")
        
if __name__ == "__main__":
    main()
