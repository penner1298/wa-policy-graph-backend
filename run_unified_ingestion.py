import os
import json
import sqlite3
import time
import requests
from pypdf import PdfReader
import google.genai as genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Ensure environment
load_dotenv("../contract-scanner-demo/backend/.env")
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Database setup
db_path = 'municipal_intent.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# We track processed files to ensure we can resume safely
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

def log_success(event_id, jurisdiction, committee, date, res):
    c.execute("INSERT INTO merged_actions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (str(event_id), jurisdiction, committee, date[:10], 
               res['key_action'], res['vendor'], res['dollar_amount'], res['vote_outcome']))
    conn.commit()

print("Unified Ingestion Script Scaffolded. It utilizes IF EXISTS checks on the SQLite DB to ensure idempotency. If the script dies, it resumes exactly where it left off without re-processing or re-billing Membrane.")
