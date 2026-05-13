import requests
from bs4 import BeautifulSoup
import pandas as pd

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

print("1. Scraping OSPI School Districts...")
r_schools = requests.get("https://ospi.k12.wa.us/about-ospi/about-school-districts/websites-and-contact-info", headers=headers)
soup_schools = BeautifulSoup(r_schools.text, 'html.parser')
schools = []
# OSPI usually has a table or a list of links
for a in soup_schools.find_all('a'):
    href = a.get('href', '')
    text = a.text.strip()
    if 'school district' in text.lower() and href.startswith('http'):
        schools.append({"Name": text, "Official_URL": href, "Type": "School District"})

print(f"Found {len(schools)} School District URLs.")

print("2. Scraping Washington Courts County/City Directory...")
r_courts = requests.get("https://www.courts.wa.gov/court_dir/?fa=court_dir.countycityref", headers=headers)
soup_courts = BeautifulSoup(r_courts.text, 'html.parser')
courts = []
# This page likely just lists counties and cities. Let's see if it has URLs.
table = soup_courts.find('table')
if table:
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) > 0:
            for a in cols[0].find_all('a'):
                href = a.get('href', '')
                if href.startswith('http'):
                    courts.append({"Name": a.text.strip(), "Official_URL": href, "Type": "City/County"})
print(f"Found {len(courts)} City/County URLs from Courts directory.")

print("3. Scraping Ports Directory...")
r_ports = requests.get("https://www.washingtonports.org/business-directory/", headers=headers)
soup_ports = BeautifulSoup(r_ports.text, 'html.parser')
ports = []
for a in soup_ports.find_all('a'):
    href = a.get('href', '')
    text = a.text.strip()
    if 'port of' in text.lower() and href.startswith('http') and 'washingtonports.org' not in href:
        ports.append({"Name": text, "Official_URL": href, "Type": "Port"})
print(f"Found {len(ports)} Port URLs.")

df = pd.DataFrame(schools + courts + ports)
if len(df) > 0:
    print(df.head())
