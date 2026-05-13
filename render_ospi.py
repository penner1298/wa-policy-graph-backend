from bs4 import BeautifulSoup
with open('sao-scraper/ospi.html', 'r') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
for a in soup.find_all('a'):
    href = a.get('href', '')
    if 'xls' in href or 'csv' in href or 'zip' in href or 'pdf' in href:
        print(a.text.strip(), href)
