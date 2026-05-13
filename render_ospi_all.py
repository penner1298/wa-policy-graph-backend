from bs4 import BeautifulSoup
with open('sao-scraper/ospi.html', 'r') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
content = soup.find('div', {'class': 'field--name-body'})
if content:
    print(content.text.strip())
