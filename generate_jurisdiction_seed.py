import sqlite3
import pandas as pd
import re

db = sqlite3.connect('sao-scraper/sao_2024.db')
df = pd.read_sql_query("SELECT DISTINCT jurisdiction FROM findings;", db)

def clean_name(name):
    # Remove "- Compliance...", ": Report...", etc.
    name = re.sub(r'\s*[-:].*$', '', name)
    return name.strip()

df['cleaned'] = df['jurisdiction'].apply(clean_name)
unique_clean = df['cleaned'].drop_duplicates().sort_values()
unique_clean.to_csv('sao-scraper/wa_jurisdictions_seed.csv', index=False, header=['jurisdiction'])

print(f"Exported {len(unique_clean)} unique WA jurisdictions.")
schools = unique_clean[unique_clean.str.contains("School District", case=False)].head(3).tolist()
ports = unique_clean[unique_clean.str.contains("Port of", case=False)].head(3).tolist()
print(f"Schools: {schools}")
print(f"Ports: {ports}")
