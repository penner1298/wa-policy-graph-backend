import sqlite3
import pandas as pd

conn = sqlite3.connect('sao-scraper/municipal_intent.db')

print("--- TIER 2: THE INTENT GRAPH (Meeting Actions) ---\n")

query = "SELECT jurisdiction, committee, meeting_date, vote_outcome, key_action FROM meeting_actions"
df = pd.read_sql_query(query, conn)

pd.set_option('display.max_colwidth', 80)
pd.set_option('display.width', 1000)

print(df.to_string(index=False))
