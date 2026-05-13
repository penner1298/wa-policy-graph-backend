import os
import csv
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_DIR = os.path.join(BASE_DIR, 'vault', 'meetings')
CSV_PATH = os.path.join(BASE_DIR, 'vault_accounting.csv')

def generate_accounting():
    data = []
    if not os.path.exists(VAULT_DIR):
        return "Vault directory does not exist."

    # Walk the vault and count files per jurisdiction
    for jurisdiction in os.listdir(VAULT_DIR):
        jur_path = os.path.join(VAULT_DIR, jurisdiction)
        if os.path.isdir(jur_path):
            files = os.listdir(jur_path)
            agendas = len([f for f in files if 'Agenda' in f])
            minutes = len([f for f in files if 'Minutes' in f])
            total = len(files)
            data.append({
                "jurisdiction": jurisdiction,
                "total_files": total,
                "agendas": agendas,
                "minutes": minutes
            })
    
    # Sort by total files descending
    data.sort(key=lambda x: x['total_files'], reverse=True)
    
    with open(CSV_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["jurisdiction", "total_files", "agendas", "minutes"])
        writer.writeheader()
        writer.writerows(data)
    
    return CSV_PATH

if __name__ == "__main__":
    path = generate_accounting()
    print(f"Accounting generated at: {path}")
