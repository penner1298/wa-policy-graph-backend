from playwright.sync_api import sync_playwright
import time
import os
import requests

def scrape_civicweb(url):
    print(f"Brute forcing CivicWeb via Playwright: {url}")
    pdfs = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use a context to handle downloads
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        # We don't wait for networkidle because CivicWeb has slow trackers. We wait for DOM.
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Find meeting links
        links = page.locator("a[href*='MeetingInformation.aspx']").all()
        hrefs = [l.get_attribute('href') for l in links]
        
        # Format links
        formatted_links = []
        for h in hrefs:
            if h.startswith('/Portal/'):
                formatted_links.append(f"https://cityofharrington.civicweb.net{h}")
            elif h.startswith('MeetingInformation'):
                formatted_links.append(f"https://cityofharrington.civicweb.net/Portal/{h}")
                
        # Deduplicate
        formatted_links = list(set(formatted_links))
        print(f"Found {len(formatted_links)} unique meetings.")
        
        if not formatted_links:
            browser.close()
            return
            
        # Target the first meeting
        target = formatted_links[0]
        print(f"Navigating to {target}")
        page.goto(target, wait_until="domcontentloaded", timeout=60000)
        
        # CivicWeb usually lists documents like "Agenda - PDF" or just a PDF icon
        doc_links = page.locator("a").all()
        for doc in doc_links:
            text = doc.inner_text().strip().lower()
            href = doc.get_attribute('href')
            if href and ('document' in href.lower() or 'pdf' in href.lower() or 'filepro' in href.lower()):
                print(f"Found document link: {text} -> {href}")
                pdfs.append(href)
        
        browser.close()

scrape_civicweb("https://cityofharrington.civicweb.net/Portal/MeetingTypeList.aspx")
