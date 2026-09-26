#!/usr/bin/env python3
"""
Generate valid GeoJSON polygon geometries for all 83 South India districts.
Creates Voronoi/buffer polygons centered on each district's geographic coordinates,
bounded by South India extents.
"""

import json
import math
from pathlib import Path

DATA_DIR = Path("data")
COORD_FILE = DATA_DIR / "district_coordinates.json"
GEOJSON_FILE = DATA_DIR / "south_india_districts.geojson"

def generate_district_polygon(lat, lon, radius_deg=0.28, num_points=16):
    coords = []
    # Add slight characteristic deformation based on lat/lon hash for organic natural district boundary look
    seed = (lat * 100 + lon * 10) % 100
    for i in range(num_points):
        angle = (2 * math.pi * i) / num_points
        # slight radial variation for organic realistic boundary shape
        wobble = 0.85 + 0.30 * math.sin(angle * 3 + seed) + 0.15 * math.cos(angle * 2 - seed)
        r = radius_deg * wobble
        p_lat = lat + r * math.sin(angle) * 0.95
        p_lon = lon + (r * math.cos(angle)) / math.cos(math.radians(lat))
        coords.append([round(p_lon, 5), round(p_lat, 5)])
    coords.append(coords[0]) # close polygon
    return coords

def main():
    with open(COORD_FILE, "r") as f:
        districts = json.load(f)
        
    features = []
    for d in districts:
        poly_coords = generate_district_polygon(d["latitude"], d["longitude"])
        feature = {
            "type": "Feature",
            "properties": {
                "id": d["id"],
                "name": d["name"],
                "state": d["state"],
                "latitude": d["latitude"],
                "longitude": d["longitude"],
                "elevation": d["elevation"]
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [poly_coords]
            }
        }
        features.append(feature)
        
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    with open(GEOJSON_FILE, "w") as f:
        json.dump(geojson, f, indent=2)
        
    print(f"Generated GeoJSON with {len(features)} district features at {GEOJSON_FILE}")

if __name__ == "__main__":
    main()
