import requests
from bs4 import BeautifulSoup
r = requests.get("https://www.washingtonports.org/ports", headers={'User-Agent':'Mozilla/5.0'})
soup = BeautifulSoup(r.text, 'html.parser')
for a in soup.find_all('a'):
    print(a.text.strip(), a.get('href'))
