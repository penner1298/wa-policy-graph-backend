import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

entities = []

print("Scraping WA Counties...")
res = requests.get("https://en.wikipedia.org/wiki/List_of_counties_in_Washington")
soup = BeautifulSoup(res.text, 'html.parser')
tables = soup.find_all('table', {'class': 'wikitable'})
for table in tables:
    for row in table.find_all('tr')[1:]:
        cols = row.find_all(['th', 'td'])
        if cols:
            name = cols[0].text.strip()
            # clean up [a], etc.
            name = name.split('[')[0].strip()
            if "County" in name:
                entities.append({"Type": "County", "Name": name})

print("Scraping WA Cities...")
res = requests.get("https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Washington")
soup = BeautifulSoup(res.text, 'html.parser')
tables = soup.find_all('table', {'class': 'wikitable'})
for table in tables:
    for row in table.find_all('tr')[1:]:
        cols = row.find_all(['th', 'td'])
        if len(cols) > 1:
            name = cols[0].text.strip()
            name = name.replace("‡", "").replace("†", "").split('[')[0].strip()
            entities.append({"Type": "City/Town", "Name": name})

print("Scraping WA School Districts...")
res = requests.get("https://en.wikipedia.org/wiki/List_of_school_districts_in_Washington")
soup = BeautifulSoup(res.text, 'html.parser')
for li in soup.find_all('li'):
    text = li.text.strip()
    if "School District" in text:
        name = text.split('\n')[0].split('[')[0].strip()
        if "School District" in name and not name.startswith("List"):
            entities.append({"Type": "School District", "Name": name})

df = pd.DataFrame(entities)
# Drop duplicates just in case
df = df.drop_duplicates(subset=['Name'])
print(f"Total compiled: {len(df)}")
print(df['Type'].value_counts())
df.to_csv("sao-scraper/wa_core_jurisdictions.csv", index=False)
