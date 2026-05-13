import pandas as pd
import json

file_path = "/Users/thejoshpenner/.openclaw/media/inbound/ba66dee1-a545-4984-b36e-8fb08c08fcc7.xlsx"

try:
    df = pd.read_excel(file_path)
    print("Columns:", df.columns.tolist())
    print("Row count:", len(df))
    print("\nFirst 10 rows:")
    print(df.head(10).to_json(orient='records', indent=2))
except Exception as e:
    print(f"Error reading excel: {e}")
