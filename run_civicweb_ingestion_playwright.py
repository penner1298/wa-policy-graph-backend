import pandas as pd
import os
import sqlite3
import time
import requests
import json
from pypdf import PdfReader
import google.genai as genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import logging
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, 'ingestion_failures.log')

logging.basicConfig(filename=LOG_PATH, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv(os.path.join(BASE_DIR, "../contract-scanner-demo/backend/.env"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

db_path = os.path.join(BASE_DIR, 'municipal_intent.db')
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

def is_processed(event_id):
    c.execute("SELECT event_id FROM merged_actions WHERE event_id=?", (str(event_id),))
    return c.fetchone() is not None

def extract_pdf_text(url, doc_type, event_id, jurisdiction):
    if not url: return ""
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if resp.status_code != 200:
            logging.error(f"DOWNLOAD_FAIL: {jurisdiction} | Event {event_id} | {doc_type} returned status {resp.status_code}.")
            return ""
        pdf_path = os.path.join(BASE_DIR, f"temp_{doc_type}_{jurisdiction}.pdf")
        with open(pdf_path, "wb") as f: f.write(resp.content)
        
        reader = PdfReader(pdf_path)
        text = ""
        for i in range(min(15, len(reader.pages))): text += reader.pages[i].extract_text() + "\n"
        os.remove(pdf_path)
        return text
    except Exception as e:
        logging.error(f"EXTRACTION_FAIL: {jurisdiction} | Event {event_id} | {doc_type} failed to parse: {e}")
        return ""

def process_civicweb_playwright():
    df = pd.read_csv(os.path.join(BASE_DIR, "mapped_wa_universe.csv"))
    civicweb_targets = df[df['Platform'] == 'CivicWeb']
    
    print(f"Brute forcing {len(civicweb_targets)} CivicWeb jurisdictions via Playwright...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        for idx, row in civicweb_targets.iterrows():
            jurisdiction_id = row['ID']
            base_url = f"https://{jurisdiction_id}.civicweb.net/Portal/MeetingTypeList.aspx"
            print(f"\nScanning CivicWeb for {row['Name']}...")
            
            try:
                page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
                links = page.locator("a[href*='MeetingInformation.aspx']").all()
                hrefs = [l.get_attribute('href') for l in links]
                
                formatted_links = []
                for h in hrefs:
                    if h.startswith('/Portal/'): formatted_links.append(f"https://{jurisdiction_id}.civicweb.net{h}")
                    elif h.startswith('MeetingInformation'): formatted_links.append(f"https://{jurisdiction_id}.civicweb.net/Portal/{h}")
                formatted_links = list(set(formatted_links))
                
                print(f"Found {len(formatted_links)} total meetings. Processing top 5 for fast ingestion...")
                
                for meeting_url in formatted_links[:5]:
                    event_id = meeting_url.split('Id=')[-1] if 'Id=' in meeting_url else meeting_url.split('/')[-1]
                    event_id = f"cw_{jurisdiction_id}_{event_id}"
                    
                    if is_processed(event_id):
                        continue
                        
                    page.goto(meeting_url, wait_until="domcontentloaded", timeout=60000)
                    doc_links = page.locator("a").all()
                    
                    target_pdf_url = ""
                    for doc in doc_links:
                        href = doc.get_attribute('href')
                        if href and '/document/' in href.lower() and '.pdf' in href.lower():
                            if href.startswith('/'):
                                target_pdf_url = f"https://{jurisdiction_id}.civicweb.net{href}"
                            else:
                                target_pdf_url = href
                            break
                    
                    if not target_pdf_url:
                        logging.warning(f"MISSING_DOCS: {jurisdiction_id} | Event {event_id} | No explicit PDF found.")
                        continue
                        
                    print(f"-> Extracting: {target_pdf_url.split('/')[-1].split('?')[0]}")
                    
                    # For CivicWeb, Agenda and Minutes are often combined in one giant packet. 
                    # We pass the entire thing as the Agenda.
                    combined_text = extract_pdf_text(target_pdf_url, "Combined", event_id, jurisdiction_id)
                    
                    if not combined_text: continue
                    
                    prompt = f"Analyze this City Council document (which may contain both Agenda and Minutes). Extract the most significant financial or policy action. Return strict JSON.\n\n--- DOCUMENT ---\n{combined_text[:30000]}"
                    
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
                                  (event_id, jurisdiction_id, "City Council", "2026-XX-XX", 
                                   res['key_action'], res['vendor'], res['dollar_amount'], res['vote_outcome']))
                        conn.commit()
                        print(f"   [SUCCESS] Action: {res['key_action'][:60]} | Cost: ${res['dollar_amount']}")
                    except Exception as e:
                        logging.error(f"MEMBRANE_FAIL: {jurisdiction_id} | Event {event_id} | LLM Extraction failed: {e}")
            except Exception as e:
                logging.error(f"SYSTEM_FAIL: {jurisdiction_id} | {e}")
                
        browser.close()

if __name__ == "__main__":
    process_civicweb_playwright()

