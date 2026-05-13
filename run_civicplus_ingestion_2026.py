import os
import json
import sqlite3
import time
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
import google.genai as genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import logging
import pandas as pd

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

def process_civicweb(jurisdiction_id, base_url):
    print(f"\nScanning CivicWeb for {jurisdiction_id} at {base_url}...")
    try:
        r = requests.get(base_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            logging.error(f"CIVICWEB_FAIL: {jurisdiction_id} returned {r.status_code}")
            return
            
        soup = BeautifulSoup(r.text, 'html.parser')
        meeting_links = []
        for a in soup.find_all('a'):
            href = a.get('href', '')
            if 'MeetingInformation.aspx' in href:
                meeting_links.append(href)
                
        # Deduplicate
        meeting_links = list(set(meeting_links))
        print(f"Found {len(meeting_links)} meeting links.")
        
        # We will stop here for the quick POC as CivicWeb requires Playwright for deep extraction 
        # (which we established earlier timed out on the first pass).
        logging.info(f"CIVICWEB_FOUND: {jurisdiction_id} has {len(meeting_links)} meetings, but requires Playwright deep extraction.")
            
    except Exception as e:
        logging.error(f"CIVICWEB_FAIL: {jurisdiction_id} - {e}")

if __name__ == "__main__":
    df = pd.read_csv(os.path.join(BASE_DIR, "mapped_wa_universe.csv"))
    civicweb_targets = df[df['Platform'] == 'CivicWeb']
    
    print(f"Initiating ingestion for {len(civicweb_targets)} CivicWeb jurisdictions.")
    for idx, row in civicweb_targets.iterrows():
        # URL is usually https://cityof[name].civicweb.net/Portal/
        url = f"https://{row['ID']}.civicweb.net/Portal/MeetingTypeList.aspx"
        process_civicweb(row['Name'], url)
