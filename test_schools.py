import requests
from bs4 import BeautifulSoup
r = requests.get("https://ospi.k12.wa.us/about-ospi/about-school-districts/websites-and-contact-info", headers={'User-Agent':'Mozilla/5.0'})
print(f"Status: {r.status_code}")
soup = BeautifulSoup(r.text, 'html.parser')
links = soup.find_all('a')
print(f"Total links: {len(links)}")
for a in links[:50]:
    print(a.text.strip(), a.get('href'))
