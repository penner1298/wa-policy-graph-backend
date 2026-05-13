import requests
import re
import pandas as pd

entities = []
headers = {'User-Agent': 'Mozilla/5.0'}

# Counties
r = requests.get("https://en.wikipedia.org/wiki/List_of_counties_in_Washington", headers=headers)
counties = re.findall(r'title="([^"]+ County, Washington)"', r.text)
for c in set(counties):
    entities.append({"Type": "County", "Name": c.split(',')[0].strip()})

# Cities
r = requests.get("https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Washington", headers=headers)
cities = re.findall(r'title="([^"]+), Washington"', r.text)
# Filter out some generic ones
for c in set(cities):
    if "Washington" not in c and "List of" not in c and "County" not in c:
        entities.append({"Type": "City", "Name": c})

# School Districts
r = requests.get("https://en.wikipedia.org/wiki/List_of_school_districts_in_Washington", headers=headers)
schools = re.findall(r'title="([^"]+ School District)"', r.text)
for s in set(schools):
    entities.append({"Type": "School District", "Name": s})

# Ports
r = requests.get("https://en.wikipedia.org/wiki/Washington_Public_Ports_Association", headers=headers)
ports = re.findall(r'title="(Port of [^"]+)"', r.text)
for p in set(ports):
    entities.append({"Type": "Port", "Name": p})

df = pd.DataFrame(entities).drop_duplicates()
print(f"Total compiled: {len(df)}")
print(df['Type'].value_counts())
df.to_csv("sao-scraper/wa_core_jurisdictions.csv", index=False)
