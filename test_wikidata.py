import requests

query = """
SELECT ?website WHERE {
  ?item rdfs:label "Seattle"@en.
  ?item wdt:P131+ wd:Q1223.
  ?item wdt:P856 ?website.
} LIMIT 1
"""
url = 'https://query.wikidata.org/sparql'
headers = {'User-Agent': 'ThePolicyGraph/1.0', 'Accept': 'application/sparql-results+json'}
r = requests.get(url, headers=headers, params={'query': query})
print(r.status_code)
print(r.text)
