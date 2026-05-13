import json
import pandas as pd
import re

with open('sao-scraper/mrsc_counties.html', 'r') as f:
    html = f.read()

match = re.search(r'\[{"CountyID":.*?}\]', html)
if match:
    json_str = match.group(0)
    try:
        data = json.loads(json_str)
        counties = []
        for county in data:
            counties.append({
                'Name': county.get('CountyName'),
                'Type': 'County',
                'County': county.get('CountyName'),
                'Official_URL': county.get('Website')
            })
        df = pd.DataFrame(counties)
        df.to_csv('sao-scraper/verified_wa_counties.csv', index=False)
        print(f"Saved {len(df)} verified counties.")
    except Exception as e:
        print(f"JSON Error: {e}")
else:
    print("Could not find JSON array.")
