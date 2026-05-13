import requests
from bs4 import BeautifulSoup
import pandas as pd

entities = []
headers = {'User-Agent': 'Mozilla/5.0'}

print("Scraping MRSC Cities...")
try:
    r = requests.get("https://mrsc.org/get-to-know-wa/cities-and-towns", headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    # MRSC lists cities in a table or list
    for a in soup.find_all('a'):
        text = a.text.strip()
        if "Profile" in a.get('title', '') or "city" in a.get('href', '').lower():
            # MRSC city links are like href="/get-to-know-wa/cities-and-towns/seattle"
            if "/get-to-know-wa/cities-and-towns/" in a.get('href', ''):
                if text and len(text) > 2 and text.lower() != "cities and towns":
                    entities.append({"Type": "City", "Name": text})
except Exception as e:
    print(e)

print("Scraping MRSC Counties...")
try:
    r = requests.get("https://mrsc.org/get-to-know-wa/counties", headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    for a in soup.find_all('a'):
        text = a.text.strip()
        if "/get-to-know-wa/counties/" in a.get('href', ''):
            if text and len(text) > 2 and text.lower() != "counties":
                entities.append({"Type": "County", "Name": text})
except Exception as e:
    print(e)

df = pd.DataFrame(entities)
if len(df) > 0:
    df = df.drop_duplicates()
    print(df['Type'].value_counts())
    print(df.head())
