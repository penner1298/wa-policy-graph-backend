import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

r = requests.get("https://mrsc.org/Research-Tools/Washington-City-and-Town-Profiles", headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

tables = soup.find_all('table')
table = tables[0]

# MRSC probably renders the links via javascript or the table rows are structured differently
for row in table.find_all('tr')[1:5]:
    tds = row.find_all('td')
    if tds:
        print([td.text.strip() for td in tds])
        # Look for links in any column
        for td in tds:
            for a in td.find_all('a'):
                print(f"Link: {a.get('href')}")
