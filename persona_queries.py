import sqlite3
import pandas as pd
conn = sqlite3.connect('sao-scraper/sao_audits.db')

print("=== PERSONA 1: The Journalist (Media API) ===")
print("Query: 'Show me all active misappropriations or major financial overspending events to build a story on local waste.'")
df1 = pd.read_sql_query("SELECT jurisdiction, dollar_impact, summary FROM findings WHERE category='Internal Controls' AND dollar_impact > 100000 ORDER BY dollar_impact DESC", conn)
print(df1.to_string(index=False))

print("\n=== PERSONA 2: The Think Tank Researcher (WA Policy Center) ===")
print("Query: 'Is there a systemic pattern of school districts lacking internal controls over physical assets?'")
df2 = pd.read_sql_query("SELECT jurisdiction, summary FROM findings WHERE jurisdiction LIKE '%School District%'", conn)
print(df2.to_string(index=False))

print("\n=== PERSONA 3: The Risk Underwriter (Municipal Bond Rater) ===")
print("Query: 'Which jurisdictions represent critical ongoing financial or legal liabilities that should affect their bond rating?'")
df3 = pd.read_sql_query("SELECT jurisdiction, type, root_cause FROM findings WHERE category IN ('Internal Controls', 'Procurement') AND dollar_impact = 0", conn)
print(df3.to_string(index=False))

