import csv
import json
from duckduckgo_search import DDGS
import time
import zipfile
import xml.etree.ElementTree as ET

file_path = "/Users/thejoshpenner/.openclaw/media/inbound/ba66dee1-a545-4984-b36e-8fb08c08fcc7.xlsx"
out_csv = "/Users/thejoshpenner/.openclaw/workspace/sao-scraper/new_mapped_districts.csv"

def get_entities_from_xlsx():
    entities = []
    # Extract strings from the sharedStrings.xml
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            strings_xml = z.read('xl/sharedStrings.xml')
            root = ET.fromstring(strings_xml)
            namespace = {'ns': root.tag.split('}')[0].strip('{')}
            
            strings = []
            for t in root.findall('.//ns:t', namespace):
                if t.text:
                    strings.append(t.text.strip())
            
            # Usually the first row are headers, we'll just grab everything that looks like an entity name
            for s in strings:
                if ("District" in s or "Port" in s) and len(s) > 5:
                    entities.append(s)
    except Exception as e:
        print(f"Error parsing xlsx manually: {e}")
    
    return list(set(entities))

def search_url(entity_name):
    query = f'"{entity_name}" Washington state official website'
    try:
        results = DDGS().text(query, max_results=3)
        for r in results:
            url = r['href']
            if 'facebook.com' not in url and 'wikipedia.org' not in url and 'linkedin.com' not in url and 'sao.wa.gov' not in url:
                return url
        return ""
    except Exception as e:
        print(f"Search error for {entity_name}: {e}")
        return ""

def process_entities():
    entities = get_entities_from_xlsx()
    print(f"Found {len(entities)} unique entities to map.")
    
    mapped = []
    for i, entity in enumerate(entities):
        if 'wa' not in entity.lower() and 'washington' not in entity.lower():
            search_name = entity + " Washington"
        else:
            search_name = entity
            
        print(f"[{i+1}/{len(entities)}] Searching for: {search_name}")
        url = search_url(search_name)
        
        entity_type = "School" if "school" in entity.lower() else "Port" if "port" in entity.lower() else "District"
        
        mapped.append({
            "Name": entity,
            "Type": entity_type,
            "County": "Unknown", 
            "Official_URL": url,
            "ID": entity.lower().replace(" ", "").replace(".", "").replace(",", "")
        })
        time.sleep(1.5) 
        
    with open(out_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["Name", "Type", "County", "Official_URL", "ID"])
        writer.writeheader()
        writer.writerows(mapped)
        
    print(f"Finished. Saved to {out_csv}")

if __name__ == "__main__":
    process_entities()
