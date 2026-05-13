import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

r = requests.get("https://mrsc.org/Research-Tools/Washington-City-and-Town-Profiles", headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

print(f"Status: {r.status_code}")

# Let's see if the data is in a table
tables = soup.find_all('table')
print(f"Found {len(tables)} tables on the page.")

if len(tables) > 0:
    for row in tables[0].find_all('tr')[:5]:
        print([td.text.strip() for td in row.find_all(['th', 'td'])])

# Alternatively, it might be in a select dropdown
selects = soup.find_all('select')
for s in selects:
    if 'city' in s.get('id', '').lower() or 'county' in s.get('id', '').lower():
        print(f"Found select dropdown: {s.get('id')}")
        options = s.find_all('option')
        print(f"Contains {len(options)} options.")
