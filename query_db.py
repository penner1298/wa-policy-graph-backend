import sqlite3
import pandas as pd

conn = sqlite3.connect('sao-scraper/sao_audits.db')

print("\n--- Washington Policy Graph: SAO Audit Database ---")
print("Query: Show all local government audit findings in the database.\n")

query = "SELECT jurisdiction, type, category, dollar_impact, summary FROM findings"
df = pd.read_sql_query(query, conn)

# Set pandas display options for better terminal reading
pd.set_option('display.max_colwidth', 80)
pd.set_option('display.width', 1000)

print(df.to_string(index=False))

print("\n--- Summary by Category ---")
summary = pd.read_sql_query("SELECT category, count(*) as count, sum(dollar_impact) as total_impact_usd FROM findings GROUP BY category", conn)
print(summary.to_string(index=False))

print("\n--- Cross-Domain Alert ---")
print("Notice: Multiple jurisdictions flagged for the same finding categories.")

