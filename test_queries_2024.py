import sqlite3
import pandas as pd

# We use the bigger offline database (43 reports) to test the personas
conn = sqlite3.connect('sao-scraper/sao_2024.db')

pd.set_option('display.max_colwidth', 100)
pd.set_option('display.width', 1000)

print("=== PERSONA 1: The Journalist (Media API) ===")
print("Query: 'Show me the biggest financial impacts over $500,000 to build a story on local waste.'")
df1 = pd.read_sql_query("SELECT report_num, dollar_impact, category, summary FROM findings WHERE dollar_impact > 500000 ORDER BY dollar_impact DESC", conn)
print(df1.to_string(index=False) if not df1.empty else "No major findings > $500k in this batch.")

print("\n=== PERSONA 2: The Think Tank Researcher (WA Policy Center) ===")
print("Query: 'Are there any findings specifically related to State Law Violations?'")
df2 = pd.read_sql_query("SELECT report_num, category, root_cause FROM findings WHERE category LIKE '%State Law%' OR category LIKE '%Compliance%'", conn)
print(df2.to_string(index=False) if not df2.empty else "No strict State Law violations found.")

print("\n=== PERSONA 3: The Risk Underwriter (Municipal Bond Rater) ===")
print("Query: 'Show me Procurement failures. These are massive hidden liabilities for federal clawbacks.'")
df3 = pd.read_sql_query("SELECT report_num, root_cause, summary FROM findings WHERE category='Procurement'", conn)
print(df3.to_string(index=False) if not df3.empty else "No Procurement failures found.")

print("\n=== TOTAL CATEGORY BREAKDOWN ===")
summary = pd.read_sql_query("SELECT category, count(*) as count, sum(dollar_impact) as total_impact_usd FROM findings GROUP BY category ORDER BY count DESC", conn)
print(summary.to_string(index=False))

