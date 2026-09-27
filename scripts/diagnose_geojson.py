import json
from pathlib import Path

with open('data/south_india_districts.geojson', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Feature count:', len(data['features']))
for f in data['features'][:10]:
    props = f['properties']
    geom = f['geometry']
    gtype = geom['type']
    coords = geom['coordinates']
    
    all_pts = []
    if gtype == 'Polygon':
        for ring in coords:
            all_pts.extend(ring)
    elif gtype == 'MultiPolygon':
        for poly in coords:
            for ring in poly:
                all_pts.extend(ring)
    
    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    print(f"{props['id']} {props['name']} ({props['state']}): {gtype}, num_points={len(all_pts)}")
    print(f"   Bounding box: Lon [{min_x:.3f}, {max_x:.3f}], Lat [{min_y:.3f}, {max_y:.3f}]")
    print(f"   District weather coord: Lon {props['longitude']}, Lat {props['latitude']}")
    print(f"   Span: dLon={max_x-min_x:.3f} deg, dLat={max_y-min_y:.3f} deg")
    print(f"   Sample first 3 coords: {all_pts[:3]}")
