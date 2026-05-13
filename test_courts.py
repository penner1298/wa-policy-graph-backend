import requests
from bs4 import BeautifulSoup
r = requests.get("https://www.courts.wa.gov/court_dir/?fa=court_dir.countycityref", headers={'User-Agent':'Mozilla/5.0'})
soup = BeautifulSoup(r.text, 'html.parser')
for a in soup.find_all('a'):
    href = a.get('href', '')
    if 'http' in href and 'wa.gov' not in href and 'courts.wa' not in href:
        print(a.text.strip(), href)
