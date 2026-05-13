import requests
import json
import os
import time
import sqlite3
import google.generativeai as genai
from pydantic import BaseModel, Field
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv("../contract-scanner-demo/backend/.env")

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

db_path = 'sao_2024.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

class Finding(BaseModel):
    category: str = Field(description="Broad category of finding (e.g., Procurement, Internal Controls, State Law Violation, Financial Statement Error, Misappropriation)")
    summary: str = Field(description="1-2 sentence description of the finding.")
    root_cause: str = Field(description="Why the issue occurred.")
    dollar_impact: int = Field(description="Financial impact in USD. 0 if none mentioned.")

def main():
    print("Gathering 2024 SAO Data from database to calculate total cost...")
    c.execute("SELECT count(*) FROM findings")
    count = c.fetchone()[0]
    
    # We processed ~44 reports today. Average tokens ~6k per report.
    estimated_tokens = count * 6000
    cost = (estimated_tokens / 1_000_000) * 0.075
    
    print("\n=========================================")
    print("2024 SWEEPER - EXPERIMENT RESULTS")
    print(f"Total WA Local Govt Reports processed: {count}")
    print(f"Total Tokens Processed (Estimate): {estimated_tokens:,}")
    print(f"Total Compute Cost (Gemini Flash): ${cost:.4f}")
    print("=========================================")

if __name__ == "__main__":
    main()
