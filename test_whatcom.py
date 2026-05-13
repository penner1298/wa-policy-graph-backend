import pandas as pd
df = pd.read_csv('sao-scraper/mapped_wa_universe_verified.csv')
print(df[df['Name'].str.contains('Whatcom', case=False)])
