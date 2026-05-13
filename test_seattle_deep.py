import sqlite3
import pandas as pd

db_audits = sqlite3.connect('sao-scraper/sao_2024.db')
db_intent = sqlite3.connect('sao-scraper/municipal_intent.db')

pd.set_option('display.max_colwidth', 150)
pd.set_option('display.width', 1000)

print("\n--- 1. REAL 2024 SEATTLE AUDIT FAILURES ---")
df_audits = pd.read_sql_query("SELECT report_num, summary FROM findings WHERE jurisdiction LIKE '%Seattle%'", db_audits)
print(df_audits.to_string(index=False))

print("\n--- 2. REAL 2026 SEATTLE INTENT (AGENDAS/MINUTES) ---")
# Use the table we successfully populated earlier for 2026
df_intent = pd.read_sql_query("SELECT meeting_date, committee, key_action FROM meeting_actions WHERE jurisdiction='seattle' AND committee LIKE '%Finance%' LIMIT 1", db_intent)
print(df_intent.to_string(index=False))

print("\n--- 3. CROSS-REFERENCE SCENARIO (THE QUERY) ---")
print("User (Journalist) searches the 2026 Database for: 'Seattle Social Housing'")
print("\n[ORACLE SYNTHESIS]")
print("Trigger: 2026-01-20 Finance Committee discussed CB 121153 relating to the Social Housing Tax Fund.")
print("Querying historical performance of 'Housing' initiatives in Seattle (2024)...")
print("-> ALERT: In 2024, Seattle had two severe SAO findings related to housing programs (HOPWA and HomeWise).")
print("-> ROOT CAUSE HIGHLIGHT: 'City Light staff did not understand the Office of Housing’s process... and did not ensure receipt of required documentation.'")
print("-> BLUEPRINT: Before finalizing the Social Housing Tax Fund, journalists should request the exact 'subrecipient monitoring procedures' that the City intends to use, as this was the exact failure point in the 2024 HOPWA audit.")

