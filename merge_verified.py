import pandas as pd

cities = pd.read_csv('sao-scraper/verified_wa_cities.csv')
counties = pd.read_csv('sao-scraper/verified_wa_counties.csv')

# standardize
# Cities: Name, Type, County, Official_URL
# Counties: Name, Type, County, Official_URL

merged = pd.concat([cities, counties], ignore_index=True)

# create a safe ID
def make_id(name):
    # remove non-alphanumeric, lower case
    import re
    return re.sub(r'[^a-z0-9]', '', str(name).lower())

merged['ID'] = merged['Name'].apply(make_id)
merged.to_csv('sao-scraper/mapped_wa_universe_verified.csv', index=False)
print(f"Merged {len(merged)} verified entities ({len(cities)} cities, {len(counties)} counties).")
