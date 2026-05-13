import requests

print("Testing CivicPlus/CivicClerk API (Lakewood as target)...")

# CivicClerk heavily uses an internal GraphQL or highly obfuscated REST endpoint
# We'll test the public endpoint often used by their portal
# Lakewood URL: https://cityoflakewood.civicweb.net/Portal/MeetingInformation.aspx

# CivicWeb portal uses a different structure, let's just see if we can pull the raw XML/HTML of the meetings list easily
url = "https://cityoflakewood.civicweb.net/Portal/MeetingInformation.aspx?Id=1461"
headers = {"User-Agent": "Mozilla/5.0"}

try:
    resp = requests.get(url, headers=headers)
    print(f"Status: {resp.status_code}")
    if "Agenda" in resp.text:
        print("Successfully accessed CivicWeb portal page. (Will require a lightweight BeautifulSoup parser, but completely viable).")
except Exception as e:
    print(e)
