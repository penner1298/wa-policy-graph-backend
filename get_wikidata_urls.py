import requests
import pandas as pd
import time

url = 'https://query.wikidata.org/sparql'
headers = {
    'User-Agent': 'ThePolicyGraph/1.0 (Contact: admin@thepolicygraph.com)',
    'Accept': 'application/sparql-results+json'
}

# 1. Cities in WA
query_cities = """
SELECT ?itemLabel ?website WHERE {
  ?item wdt:P31/wdt:P279* wd:Q515.
  ?item wdt:P131+ wd:Q1223.
  OPTIONAL { ?item wdt:P856 ?website. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

# 2. Counties in WA
query_counties = """
SELECT ?itemLabel ?website WHERE {
  ?item wdt:P31 wd:Q47168.
  ?item wdt:P131 wd:Q1223.
  OPTIONAL { ?item wdt:P856 ?website. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

# 3. School Districts in WA
query_schools = """
SELECT ?itemLabel ?website WHERE {
  ?item wdt:P31/wdt:P279* wd:Q7432270.
  ?item wdt:P131+ wd:Q1223.
  OPTIONAL { ?item wdt:P856 ?website. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

url_mapping = {}

def fetch_urls(query, label):
    print(f"Fetching {label} URLs from Wikidata...")
    try:
        r = requests.get(url, headers=headers, params={'format': 'json', 'query': query})
        data = r.json()
        count = 0
        for item in data['results']['bindings']:
            name = item['itemLabel']['value']
            website = item.get('website', {}).get('value', None)
            if website and not name.startswith("Q"):
                url_mapping[name] = website
                count += 1
        print(f" -> Found official URLs for {count} {label}")
    except Exception as e:
        print(f"Error fetching {label}: {e}")
    time.sleep(1)

fetch_urls(query_cities, "Cities")
fetch_urls(query_counties, "Counties")
fetch_urls(query_schools, "School Districts")

# Now merge this with our mapped_wa_universe.csv
df = pd.read_csv('sao-scraper/mapped_wa_universe.csv')

# Wikidata often includes ", Washington" or "County". We need to fuzzy match.
def normalize(name):
    return name.lower().replace(' county', '').replace(' city', '').strip()

# Build a normalized lookup dict
normalized_urls = {normalize(k): v for k, v in url_mapping.items()}

def find_url(name):
    norm_name = normalize(name)
    if norm_name in normalized_urls:
        return normalized_urls[norm_name]
    # Try with " Washington" appended if it was in the wikidata label
    for k, v in normalized_urls.items():
        if norm_name in k:
            return v
    return None

df['Official_URL'] = df['Name'].apply(find_url)

found_count = df['Official_URL'].notna().sum()
print(f"\nSuccessfully matched {found_count} out of {len(df)} URLs from the global database.")

df.to_csv('sao-scraper/mapped_wa_universe_with_urls.csv', index=False)
