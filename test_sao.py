import requests
from bs4 import BeautifulSoup

url = "https://portal.sao.wa.gov/ReportSearch/Home/AuditReports"
headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

# Let's see if we can just get the page and parse it or if it requires POST
response = requests.get(url, headers=headers)
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    print(soup.title.text if soup.title else "No title")
    # check for obvious table or list
    print(len(soup.find_all('table')))
    
