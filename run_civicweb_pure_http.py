import pandas as pd
import os
import sqlite3
import time
import requests
from bs4 import BeautifulSoup
import json
from pypdf import PdfReader
import google.genai as genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "../contract-scanner-demo/backend/.env"))

# Using gemini-2.5-flash for ingestion
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

db_path = os.path.join(BASE_DIR, 'municipal_intent.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

class MergedAction(BaseModel):
    key_action: str = Field(description="The single most significant policy, contract, or spending action taken.")
    vendor: str = Field(description="The contractor, vendor, or agency receiving funds. 'None' if NA.")
    dollar_amount: int = Field(description="The total financial value requested or contracted. 0 if no money was spent.")
    vote_outcome: str = Field(description="The final vote count or outcome if mentioned (e.g., 'Passed 7-0', 'Failed'). If unknown, write 'Unknown'.")

def is_processed(event_id):
    c.execute("SELECT event_id FROM merged_actions WHERE event_id=?", (str(event_id),))
    return c.fetchone() is not None

def extract_pdf_text(url):
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if resp.status_code != 200: return ""
        pdf_path = os.path.join(BASE_DIR, "temp_civicweb.pdf")
        with open(pdf_path, "wb") as f: f.write(resp.content)
        
        reader = PdfReader(pdf_path)
        text = ""
        for i in range(min(15, len(reader.pages))): text += reader.pages[i].extract_text() + "\n"
        os.remove(pdf_path)
        return text
    except:
        return ""

def process_civicweb_pure():
    targets = [
        {"ID": "clydehill", "URL": "https://clydehill.civicweb.net/portal/"},
        {"ID": "desmoines", "URL": "https://desmoines.civicweb.net/Portal/CitizenEngagement.aspx"},
        {"ID": "dupont", "URL": "https://dupont.civicweb.net/portal/"},
        {"ID": "everson", "URL": "https://cieversonwa.civicweb.net/Portal/"},
        {"ID": "ferndale", "URL": "https://ferndale.civicweb.net/portal/"},
        {"ID": "lacenter", "URL": "https://lacenter.civicweb.net/Portal/"},
        {"ID": "monroe", "URL": "https://monroewa.civicweb.net/Portal/"},
        {"ID": "newcastle", "URL": "https://newcastle.civicweb.net/portal/"},
        {"ID": "normandypark", "URL": "https://normandypark.civicweb.net/portal/"},
        {"ID": "oceanshores", "URL": "https://oceanshores.civicweb.net/portal/"},
        {"ID": "pasco", "URL": "https://pasco.civicweb.net/Portal"},
        {"ID": "cityofprosser", "URL": "https://cityofprosser.civicweb.net/Portal/"},
        {"ID": "quincy", "URL": "https://quincy.civicweb.net/portal/"},
        {"ID": "sammamish", "URL": "https://sammamishwa.civicweb.net/portal/"}
    ]
    
    print(f"Executing PURE HTTP scrape (NO headless browser) across {len(targets)} VERIFIED WA CivicWeb portals...")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for t in targets:
        jurisdiction_id = t['ID']
        # Normalize to MeetingTypeList.aspx for consistent scraping
        base = t['URL'].split('/Portal')[0] if '/portal' in t['URL'].lower() else t['URL']
        portal_url = f"{base}/Portal/MeetingTypeList.aspx"
        print(f"\nScanning: {jurisdiction_id}")
        
        try:
            r = requests.get(portal_url, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            meeting_links = []
            for a in soup.find_all('a'):
                href = a.get('href', '')
                if 'MeetingInformation.aspx' in href:
                    if href.startswith('/'):
                        meeting_links.append(f"{base}{href}")
                    else:
                        meeting_links.append(f"{base}/Portal/{href}")
            
            meeting_links = list(set(meeting_links))
            print(f"Found {len(meeting_links)} meetings.")
            
            for meeting_url in meeting_links[:5]:
                event_id = meeting_url.split('Id=')[-1] if 'Id=' in meeting_url else meeting_url.split('/')[-1]
                event_id = f"cw_{jurisdiction_id}_{event_id}"
                
                if is_processed(event_id): continue
                
                r2 = requests.get(meeting_url, headers=headers, timeout=10)
                soup2 = BeautifulSoup(r2.text, 'html.parser')
                
                target_pdf = ""
                for a in soup2.find_all('a'):
                    href = a.get('href', '')
                    if '.pdf' in href.lower() or '/document/' in href.lower():
                        if href.startswith('/'):
                            target_pdf = f"{base}{href}"
                        else:
                            target_pdf = href
                        break
                        
                if not target_pdf: continue
                print(f"-> Found PDF: {target_pdf.split('/')[-1][:30]}")
                
                text = extract_pdf_text(target_pdf)
                if not text: continue
                
                prompt = f"Analyze this City Council document. Extract the most significant financial or policy action. Return strict JSON.\n\n--- DOCUMENT ---\n{text[:30000]}"
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config={"response_mime_type": "application/json", "response_schema": MergedAction},
                    )
                    res = json.loads(response.text)
                    c.execute("INSERT INTO merged_actions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (event_id, jurisdiction_id, "City Council", "2026-05-11", 
                               res['key_action'], res['vendor'], res['dollar_amount'], res['vote_outcome']))
                    conn.commit()
                    print(f"   [SUCCESS] {res['key_action'][:60]}")
                except Exception as e:
                    pass
        except Exception as e:
            print(f"Failed {jurisdiction_id}: {e}")

if __name__ == "__main__":
    process_civicweb_pure()
