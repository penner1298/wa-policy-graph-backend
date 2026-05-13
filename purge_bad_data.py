import sqlite3
import pandas as pd

# Load verified IDs
df = pd.read_csv('sao-scraper/mapped_wa_universe_verified.csv')
verified_ids = set(df['ID'].tolist())

# Add some known manual mappings if any Granicus ones didn't match perfectly, but let's check first.
# Connect to DB
conn = sqlite3.connect('sao-scraper/municipal_intent.db')
c = conn.cursor()

c.execute("SELECT DISTINCT jurisdiction FROM merged_actions")
current_jurisdictions = [row[0] for row in c.fetchall()]

bad_jurisdictions = []
good_jurisdictions = []

for j in current_jurisdictions:
    # simple matching or exact matching
    if j in verified_ids:
        good_jurisdictions.append(j)
    else:
        # Check if 'cityof' + j is in verified, or if it matches some common patterns
        if j.replace('cityof', '') in verified_ids or j.replace('county', '') in verified_ids:
             good_jurisdictions.append(j)
        else:
            bad_jurisdictions.append(j)

print("Good (Verified):", good_jurisdictions)
print("Bad (Unverified):", bad_jurisdictions)

for bad in bad_jurisdictions:
    print(f"Deleting bad jurisdiction: {bad}")
    c.execute("DELETE FROM merged_actions WHERE jurisdiction=?", (bad,))

conn.commit()
conn.close()
print("Purge complete.")
