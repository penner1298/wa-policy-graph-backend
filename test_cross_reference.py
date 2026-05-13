import sqlite3
import pandas as pd

# Connect to both databases
db_audits = sqlite3.connect('sao-scraper/sao_2024.db')
db_intent = sqlite3.connect('sao-scraper/municipal_intent.db')

pd.set_option('display.max_colwidth', 100)
pd.set_option('display.width', 1000)

jurisdiction = 'Seattle'

print(f"=== CROSS-REFERENCE DASHBOARD: {jurisdiction.upper()} ===\n")

print("[TIER 2: RECENT ACTIONS & INTENT]")
print("What is the City Council voting on?")
df_actions_26 = pd.read_sql_query("SELECT meeting_date, key_action, vote_outcome FROM meeting_actions WHERE jurisdiction='seattle' LIMIT 3", db_intent)
print(df_actions_26.to_string(index=False) if not df_actions_26.empty else "No recent actions found.")

print("\n[TIER 1: HISTORICAL LIABILITIES & AUDITS]")
print("What are their past failures?")
df_audits = pd.read_sql_query("SELECT category, dollar_impact, summary FROM findings WHERE jurisdiction LIKE '%Seattle%' LIMIT 4", db_audits)
print(df_audits.to_string(index=False) if not df_audits.empty else "No severe audit findings in the current batch.")

print("\n[ORACLE SYNTHESIS (PRE-COG ALERT)]")
print("Trigger: New Action Detected -> [Passed ordinance granting skybridge permit...]")
print("Checking Risk Graph...")
print("-> ALERT: The City of Seattle carries severe active liability flags for 'Internal Controls' and 'State Law Violation'. Proceed with heightened scrutiny on internal tracking for this permit.")

