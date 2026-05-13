import requests
from bs4 import BeautifulSoup
import re

url = "https://portal.sao.wa.gov/ReportSearch/"
resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

soup = BeautifulSoup(resp.text, 'html.parser')
# Look for a select element or hidden JSON
select = soup.find('select', {'id': 'ClientId'})
if select:
    options = select.find_all('option')
    print(f"Found {len(options)} entities in dropdown.")
    print([o.text for o in options[1:6]])
else:
    print("No select dropdown found. Might be loaded via AJAX.")

# Check for javascript variables
scripts = soup.find_all('script')
for s in scripts:
    if s.string and 'ClientList' in s.string:
        print("Found ClientList in JS")
