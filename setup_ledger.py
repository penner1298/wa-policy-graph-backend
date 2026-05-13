import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'ingestion_ledger.db')

def setup_ledger():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS ingestion_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jurisdiction_name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            state TEXT DEFAULT 'WA',
            official_url TEXT,
            vendor TEXT, -- e.g., Legistar, CivicPlus, Granicus
            api_endpoint TEXT,
            target_start_date TEXT DEFAULT '2026-01-01',
            last_scrape_attempt DATETIME,
            last_scrape_status TEXT DEFAULT 'Pending',
            documents_vaulted INTEGER DEFAULT 0,
            notes TEXT
        )
    ''')
    
    # Create a unique index to prevent duplicates
    c.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_jurisdiction 
        ON ingestion_ledger(jurisdiction_name, entity_type)
    ''')
    
    conn.commit()
    conn.close()
    print(f"Ledger initialized at {DB_PATH}")

if __name__ == "__main__":
    setup_ledger()
