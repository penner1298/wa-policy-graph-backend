from playwright.sync_api import sync_playwright
import time
import requests
import json
import sqlite3
import os
import google.genai as genai
from pydantic import BaseModel, Field
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv("../contract-scanner-demo/backend/.env")
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class MergedAction(BaseModel):
    key_action: str = Field(description="The single most significant policy, contract, or spending action taken.")
    vendor: str = Field(description="The contractor, vendor, or agency receiving funds. 'None' if NA.")
    dollar_amount: int = Field(description="The total financial value requested or contracted. 0 if no money was spent.")
    vote_outcome: str = Field(description="The final vote count or outcome if mentioned (e.g., 'Passed 7-0', 'Failed'). If unknown, write 'Unknown'.")

def extract_pdf_text(url):
    if not url: return ""
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code != 200: return ""
        pdf_path = "temp_lakewood.pdf"
        with open(pdf_path, "wb") as f: f.write(resp.content)
        reader = PdfReader(pdf_path)
        text = ""
        for i in range(min(20, len(reader.pages))): text += reader.pages[i].extract_text() + "\n"
        os.remove(pdf_path)
        return text
    except:
        return ""

def scrape_lakewood():
    print("Launching headless browser to scrape Lakewood (CivicWeb/CivicPlus)...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Don't wait for networkidle, just wait for the DOM. CivicWeb has incredibly slow tracking pixels that cause timeouts.
        page.goto("https://cityoflakewood.civicweb.net/Portal/MeetingTypeList.aspx", wait_until="domcontentloaded", timeout=60000)
        
        print("Page loaded. Extracting City Council meeting links...")
        
        links = page.locator("a[href*='MeetingInformation.aspx']").all()
        print(f"Found {len(links)} meeting instances on the portal index.")
        
        meeting_data = []
        for i, link in enumerate(links[:3]): # Top 3 for POC
            title = link.inner_text()
            href = link.get_attribute('href')
            # CivicWeb URLs often lack the prefix if relative
            if href.startswith('MeetingInformation'):
                full_url = f"https://cityoflakewood.civicweb.net/Portal/{href}"
            else:
                full_url = href if href.startswith('http') else f"https://cityoflakewood.civicweb.net{href}"
            meeting_data.append({"title": title, "url": full_url})
            
        print("Extracting PDF links from individual meeting pages...")
        for meeting in meeting_data:
            print(f"-> Accessing: {meeting['title']}")
            try:
                page.goto(meeting['url'], wait_until="domcontentloaded", timeout=30000)
                
                # In CivicWeb, the actual PDF links are usually inside an iframe or deep div.
                # Let's just grab all .pdf links on the page.
                pdf_links = page.locator("a[href*='.pdf']").all()
                agenda_url = ""
                minutes_url = ""
                
                for pdf in pdf_links:
                    href = pdf.get_attribute('href')
                    text = pdf.inner_text().lower()
                    if "agenda" in text: agenda_url = f"https://cityoflakewood.civicweb.net{href}" if href.startswith('/') else href
                    if "minute" in text: minutes_url = f"https://cityoflakewood.civicweb.net{href}" if href.startswith('/') else href
                
                # If the text isn't explicit, just grab the first two PDFs
                if not agenda_url and len(pdf_links) > 0:
                    href = pdf_links[0].get_attribute('href')
                    agenda_url = f"https://cityoflakewood.civicweb.net{href}" if href.startswith('/') else href
                if not minutes_url and len(pdf_links) > 1:
                    href = pdf_links[1].get_attribute('href')
                    minutes_url = f"https://cityoflakewood.civicweb.net{href}" if href.startswith('/') else href
                    
                meeting['agenda_url'] = agenda_url
                meeting['minutes_url'] = minutes_url
            except Exception as e:
                print(f"Failed to load meeting page: {e}")
            
        browser.close()
        return meeting_data

def process_lakewood_with_membrane(meeting_data):
    for i, meeting in enumerate(meeting_data):
        title = meeting['title']
        agenda_url = meeting.get('agenda_url')
        minutes_url = meeting.get('minutes_url')
        
        if not agenda_url:
            print(f"\nSkipping {title} - No documents found.")
            continue
            
        print(f"\nProcessing {title} through Membrane...")
        agenda_text = extract_pdf_text(agenda_url)
        minutes_text = extract_pdf_text(minutes_url) if minutes_url else ""
        
        prompt = f"Analyze these City Council documents. Combine the agenda and minutes to extract the most significant financial or policy action. Return strict JSON.\n\n--- AGENDA ---\n{agenda_text[:20000]}\n\n--- MINUTES ---\n{minutes_text[:20000]}"
        
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
            print(f"  -> Action: {res['key_action'][:100]}...")
            print(f"  -> Vendor: {res['vendor']} | Cost: ${res['dollar_amount']:,} | Vote: {res['vote_outcome']}")
        except Exception as e:
            print(f"  -> Error: {e}")

if __name__ == "__main__":
    meetings = scrape_lakewood()
    process_lakewood_with_membrane(meetings)
