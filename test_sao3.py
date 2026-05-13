import requests
from bs4 import BeautifulSoup

url = "https://sao.wa.gov/reports-data/audit-reports"
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')
links = soup.find_all('a', href=True)
for l in links:
    if 'report' in l['href'].lower() or 'search' in l['href'].lower():
        print(l['href'])
