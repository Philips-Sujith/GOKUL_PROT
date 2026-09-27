import json
import urllib.request

url = 'https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/INDIA/INDIA_DISTRICTS.geojson'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=60) as resp:
    raw = json.loads(resp.read().decode('utf-8'))

print("Total features:", len(raw['features']))

for target in ['KARNATAKA', 'KERALA', 'TAMIL NADU']:
    feats = []
    for f in raw['features']:
        st = f.get('properties', {}).get('state')
        if st and str(st).strip().upper() == target:
            feats.append(f)
    print(f"\nState: {target} -> Count: {len(feats)}")
    for f in feats:
        print("  -", f['properties'])
