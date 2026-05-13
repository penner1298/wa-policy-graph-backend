import requests
import json
import os
import sqlite3
import time
from pypdf import PdfReader
from pydantic import BaseModel, Field
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("../contract-scanner-demo/backend/.env")
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

# Set up the Tier 2 Database
db_path = 'municipal_intent.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS meeting_actions
             (event_id TEXT PRIMARY KEY, jurisdiction TEXT, committee TEXT, meeting_date TEXT, 
              key_action TEXT, dollar_amount INTEGER, vote_outcome TEXT)''')
conn.commit()

class MeetingAction(BaseModel):
    key_action: str = Field(description="The single most significant policy, contract, or spending action taken during this meeting. Keep it under 2 sentences.")
    dollar_amount: int = Field(description="The total financial value of the key action in USD. 0 if no money was spent.")
    vote_outcome: str = Field(description="The final vote count or outcome if mentioned (e.g., 'Passed 7-0', 'Failed 4-5', 'Approved'). If unknown, write 'Unknown'.")

def extract_pdf_text(url):
    try:
        # Download PDF
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200: return ""
        
        pdf_path = "temp_meeting.pdf"
        with open(pdf_path, "wb") as f:
            f.write(resp.content)
            
        reader = PdfReader(pdf_path)
        text = ""
        # Read up to first 20 pages of minutes to find actions
        for i in range(min(20, len(reader.pages))): 
            text += reader.pages[i].extract_text() + "\n"
            
        os.remove(pdf_path)
        return text
    except Exception as e:
        print(f"PDF Error: {e}")
        return ""

def main():
    jurisdiction = "seattle"
    print(f"Fetching 2026 Meetings for {jurisdiction.capitalize()}...")
    url = f"https://webapi.legistar.com/v1/{jurisdiction}/events?$filter=EventDate ge datetime'2026-01-01T00:00:00'&$orderby=EventDate asc"
    
    resp = requests.get(url, headers={"Accept": "application/json"})
    if resp.status_code != 200:
        print("Failed to hit Granicus API.")
        return
        
    events = resp.json()
    print(f"Found {len(events)} meetings.")
    
    # We only want meetings that have Minutes attached, because that's where the actual vote happens
    completed_meetings = [e for e in events if e.get('EventMinutesFile')]
    print(f"Found {len(completed_meetings)} completed meetings with Minutes.")
    
    for i, event in enumerate(completed_meetings[:10]): # Limit to 10 for rapid POC
        event_id = str(event.get('EventId'))
        committee = event.get('EventBodyName')
        date = event.get('EventDate')
        minutes_url = event.get('EventMinutesFile')
        
        # Check if already processed
        c.execute("SELECT event_id FROM meeting_actions WHERE event_id=?", (event_id,))
        if c.fetchone():
            continue
            
        print(f"[{i+1}/10] Processing {committee} on {date[:10]}...")
        text = extract_pdf_text(minutes_url)
        if not text.strip(): continue
        
        prompt = f"Analyze these City Council Meeting Minutes and extract the most significant policy action or financial expenditure that was voted on. Return strict JSON.\n\nMinutes Text:\n{text[:40000]}"
        
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=MeetingAction
                )
            )
            res = json.loads(response.text)
            
            c.execute("INSERT INTO meeting_actions VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (event_id, jurisdiction, committee, date[:10], 
                       res['key_action'], res['dollar_amount'], res['vote_outcome']))
            conn.commit()
            print(f"  -> Action: {res['key_action']}")
            print(f"  -> Cost: ${res['dollar_amount']} | Vote: {res['vote_outcome']}")
        except Exception as e:
            print(f"  -> Membrane Error: {e}")
            
        time.sleep(1)

if __name__ == "__main__":
    main()
