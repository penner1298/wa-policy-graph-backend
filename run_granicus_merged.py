import requests
import json
import os
import sqlite3
import time
from pypdf import PdfReader
from pydantic import BaseModel, Field
import google.genai as genai
from dotenv import load_dotenv

load_dotenv("../contract-scanner-demo/backend/.env")
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Tier 2 Database
db_path = 'municipal_intent.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS merged_actions
             (event_id TEXT PRIMARY KEY, jurisdiction TEXT, committee TEXT, meeting_date TEXT, 
              key_action TEXT, vendor TEXT, dollar_amount INTEGER, vote_outcome TEXT)''')
conn.commit()

class MergedAction(BaseModel):
    key_action: str = Field(description="The single most significant policy, contract, or spending action taken.")
    vendor: str = Field(description="The contractor, vendor, or agency receiving funds. 'None' if NA.")
    dollar_amount: int = Field(description="The total financial value requested or contracted. 0 if no money was spent.")
    vote_outcome: str = Field(description="The final vote count or outcome if mentioned (e.g., 'Passed 7-0', 'Failed'). If unknown, write 'Unknown'.")

def extract_pdf_text(url):
    if not url: return ""
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200: return ""
        pdf_path = "temp.pdf"
        with open(pdf_path, "wb") as f: f.write(resp.content)
        reader = PdfReader(pdf_path)
        text = ""
        for i in range(min(20, len(reader.pages))): text += reader.pages[i].extract_text() + "\n"
        os.remove(pdf_path)
        return text
    except:
        return ""

def process_city(jurisdiction, year):
    print(f"\nFetching {year} Meetings for {jurisdiction}...")
    url = f"https://webapi.legistar.com/v1/{jurisdiction}/events?$filter=EventDate ge datetime'{year}-01-01T00:00:00' and EventDate le datetime'{year}-12-31T23:59:59'&$orderby=EventDate desc"
    
    resp = requests.get(url, headers={"Accept": "application/json"})
    if resp.status_code != 200: return
    events = resp.json()
    
    completed = [e for e in events if e.get('EventAgendaFile') and e.get('EventMinutesFile')]
    print(f"Found {len(completed)} completed meetings with both Agenda & Minutes.")
    
    for i, event in enumerate(completed[:5]): # 5 per city for the POC
        event_id = str(event.get('EventId'))
        committee = event.get('EventBodyName')
        date = event.get('EventDate')
        
        c.execute("SELECT event_id FROM merged_actions WHERE event_id=?", (event_id,))
        if c.fetchone(): continue
            
        print(f"[{i+1}/5] {jurisdiction.capitalize()} - {committee} on {date[:10]}")
        agenda_text = extract_pdf_text(event.get('EventAgendaFile'))
        minutes_text = extract_pdf_text(event.get('EventMinutesFile'))
        
        if not agenda_text and not minutes_text: continue
        
        prompt = f"Analyze these City Council documents. The AGENDA contains the requested money and vendors. The MINUTES contain the final vote outcome. Combine them to extract the most significant financial or policy action. Return strict JSON.\n\n--- AGENDA ---\n{agenda_text[:20000]}\n\n--- MINUTES ---\n{minutes_text[:20000]}"
        
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": MergedAction,
                },
            )
            res = json.loads(response.text)
            
            c.execute("INSERT INTO merged_actions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (event_id, jurisdiction, committee, date[:10], 
                       res['key_action'], res['vendor'], res['dollar_amount'], res['vote_outcome']))
            conn.commit()
            print(f"  -> Action: {res['key_action']}")
            print(f"  -> Vendor: {res['vendor']} | Cost: ${res['dollar_amount']:,} | Vote: {res['vote_outcome']}")
        except Exception as e:
            print(f"  -> Error: {e}")
        time.sleep(1)

def main():
    # We test Seattle and Tacoma for 2024
    process_city("seattle", "2024")
    process_city("tacoma", "2024")

if __name__ == "__main__":
    main()
