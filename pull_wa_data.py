import requests
import json
import pandas as pd

entities = []

print("Querying Wikidata for WA Cities, Counties, School Districts, and Ports...")

# Wikidata SPARQL endpoint
url = 'https://query.wikidata.org/sparql'
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'Accept': 'application/sparql-results+json'
}

# 1. Cities/Towns in Washington (State)
query_cities = """
SELECT ?itemLabel WHERE {
  ?item wdt:P31/wdt:P279* wd:Q515.
  ?item wdt:P131+ wd:Q1223.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

# 2. Counties in Washington
query_counties = """
SELECT ?itemLabel WHERE {
  ?item wdt:P31 wd:Q47168.
  ?item wdt:P131 wd:Q1223.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

def run_query(q, entity_type):
    try:
        r = requests.get(url, headers=headers, params={'format': 'json', 'query': q})
        data = r.json()
        for item in data['results']['bindings']:
            name = item['itemLabel']['value']
            if not name.startswith("Q") and len(name) > 2: # Filter out raw Q-ids
                entities.append({"Type": entity_type, "Name": name})
        print(f"Got {len(data['results']['bindings'])} {entity_type}s")
    except Exception as e:
        print(f"Error for {entity_type}: {e}")

run_query(query_cities, "City/Town")
run_query(query_counties, "County")

df = pd.DataFrame(entities)
if len(df) > 0:
    df = df.drop_duplicates()
    print(df['Type'].value_counts())
    df.to_csv("sao-scraper/wa_core_jurisdictions.csv", index=False)
