import os
import requests
import time
import csv

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_DIR = os.path.join(BASE_DIR, 'vault', 'meetings')
CSV_PATH = os.path.join(BASE_DIR, 'vault_accounting.csv')

def download_file(url, jurisdiction, date, event_id, doc_type):
    try:
        save_dir = os.path.join(VAULT_DIR, jurisdiction)
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{jurisdiction}_{date}_{event_id}_{doc_type}.pdf"
        pdf_path = os.path.join(save_dir, filename)
        if os.path.exists(pdf_path): return True
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if resp.status_code == 200:
            with open(pdf_path, "wb") as f: f.write(resp.content)
            return True
    except: pass
    return False

def update_csv_accounting():
    data = []
    if os.path.exists(VAULT_DIR):
        for jurisdiction in os.listdir(VAULT_DIR):
            jur_path = os.path.join(VAULT_DIR, jurisdiction)
            if os.path.isdir(jur_path):
                files = [f for f in os.listdir(jur_path) if "_2026" in f]
                if not files: continue
                data.append({
                    "jurisdiction": jurisdiction,
                    "total_2026_files": len(files),
                    "agendas": len([f for f in files if 'Agenda' in f]),
                    "minutes": len([f for f in files if 'Minutes' in f])
                })
    data.sort(key=lambda x: x['total_2026_files'], reverse=True)
    with open(CSV_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["jurisdiction", "total_2026_files", "agendas", "minutes"])
        writer.writeheader()
        writer.writerows(data)

def run_2026_wa_download():
    # 1. Broad Legistar Search
    try:
        resp = requests.get("https://webapi.legistar.com/v1/Client", timeout=20)
        instances = resp.json() if resp.status_code == 200 else []
    except: instances = []
    
    wa_keywords = [' wa', 'washington', 'seattle', 'tacoma', 'olympia', 'bellevue', 'snohomish', 'king county', 'spokane', 'pierce', 'whatcom', 'kitsap', 'thurston', 'yakima', 'clark', 'vancouver', 'bellingham', 'everett', 'renton', 'kent', 'federal way', 'spokane valley', 'kirkland', 'kennewick', 'pasco', 'richland', 'marysville', 'lakewood', 'shoreline', 'redmond', 'edmonds', 'puyallup', 'longview', 'lynnwood', 'washougal', 'wenatchee', 'mount vernon', 'wallawalla', 'pullman', 'des moines', 'sea-tac', 'burien', 'bothell', 'issaquah', 'maple valley', 'bremerton', 'oak harbor', 'kenmore', 'mukilteo', 'mountlake terrace', 'mercer island', 'lacey', 'port los angeles', 'pullman', 'puyallup', 'redmond', 'renton', 'richland', 'sea tac', 'seattle', 'shoreline', 'spokane', 'spokane valley', 'tacoma', 'tukwila', 'vancouver', 'walla walla', 'wenatchee', 'yakima']
    
    wa_clients = []
    for inst in instances:
        name = inst.get('ClientName', '').lower()
        if any(kw in name for kw in wa_keywords):
            wa_clients.append(inst.get('ClientShortName'))
    
    known_wa = ["seattle", "kingcounty", "olympia", "bellevue", "cityoftacoma", "snohomish", "redmond", "spokane", "pierce", "whatcom", "clark", "bellingham", "everett", "renton", "kent", "vancouver", "kitsap", "thurston", "yakima", "piercecounty", "cityofredmond", "shorelinewa", "cityoffederalway", "spokanecounty", "yakimacounty", "snohomishcounty", "kingcountywa"]
    wa_clients = list(set(wa_clients + known_wa))
    
    print(f"Verified {len(wa_clients)} potential WA Legistar Targets.")
    for lid in wa_clients:
        try:
            url = f"https://webapi.legistar.com/v1/{lid}/events?$filter=EventDate ge datetime'2026-01-01T00:00:00'"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                events = resp.json()
                for event in events:
                    event_id = str(event.get('EventId'))
                    date = (event.get('EventDate') or "2026-00-00")[:10]
                    for doc_type, doc_url in [('Agenda', event.get('EventAgendaFile')), ('Minutes', event.get('EventMinutesFile'))]:
                        if doc_url:
                            download_file(doc_url, lid, date, event_id, doc_type)
            update_csv_accounting()
            time.sleep(0.5)
        except: continue

    # 2. Add CivicPlus/Other system placeholders here if we have their APIs or standard URL patterns
    # (Future-proofing for the next turn)

if __name__ == "__main__":
    run_2026_wa_download()
