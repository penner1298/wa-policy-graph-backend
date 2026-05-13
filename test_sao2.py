import requests
from bs4 import BeautifulSoup

url = "https://sao.wa.gov/reports-data/audit-reports"
headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

response = requests.get(url, headers=headers)
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    print(soup.title.text if soup.title else "No title")
    print("Iframes:")
    for iframe in soup.find_all('iframe'):
        print(iframe.get('src'))
