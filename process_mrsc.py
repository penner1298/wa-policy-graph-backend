import json
import pandas as pd
import re

with open('mrsc.html', 'r') as f:
    html = f.read()

# The JSON array is passed to javascript. Let's find it.
match = re.search(r'\[{"CityID":.*?}\]', html)
if match:
    json_str = match.group(0)
    try:
        data = json.loads(json_str)
        cities = []
        for city in data:
            cities.append({
                'Name': city.get('CityName'),
                'Type': 'City',
                'County': city.get('County'),
                'Official_URL': city.get('Website')
            })
        df = pd.DataFrame(cities)
        df.to_csv('sao-scraper/verified_wa_cities.csv', index=False)
        print(f"Saved {len(df)} verified cities.")
    except Exception as e:
        print(f"JSON Error: {e}")
else:
    print("Could not find JSON array.")
