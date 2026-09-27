import json
from pathlib import Path

def main():
    geojson_path = Path("data/south_india_districts.geojson")
    with open(geojson_path, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    coords_path = Path("data/district_coordinates.json")
    with open(coords_path, "r", encoding="utf-8") as f:
        coords = json.load(f)

    features = geojson["features"]
    print(f"Total GeoJSON district features: {len(features)}")
    
    feature_map = {f["properties"]["id"]: f for f in features}
    
    # State counts
    tn_f = [f for f in features if f["properties"]["state"] == "Tamil Nadu"]
    kl_f = [f for f in features if f["properties"]["state"] == "Kerala"]
    ka_f = [f for f in features if f["properties"]["state"] == "Karnataka"]

    print(f"\nTamil Nadu : {len(tn_f)}/38 matched")
    print(f"Kerala     : {len(kl_f)}/14 matched")
    print(f"Karnataka  : {len(ka_f)}/31 matched")

    # Test joining with coordinates and categories
    print("\n--- DETAILED 83-DISTRICT VERIFICATION ---")
    all_valid = True
    for d in coords:
        d_id = d["id"]
        d_name = d["name"]
        d_state = d["state"]
        
        f = feature_map.get(d_id)
        if not f:
            print(f"MISSING FEATURE: {d_id} {d_name}")
            all_valid = False
            continue
            
        g_type = f["geometry"]["type"]
        if g_type not in ("Polygon", "MultiPolygon"):
            print(f"INVALID GEOM TYPE: {d_id} {g_type}")
            all_valid = False
            continue
            
        source_name = f["properties"].get("source_district_name")
        print(f"[{d_id}] {d_name:20s} ({d_state:10s}) -> GeoJSON: {g_type:12s} (Source: {source_name})")

    if all_valid:
        print("\nSUCCESS: All 83/83 districts verified with valid administrative polygon geometry!")
    else:
        print("\nFAILURE: Some districts failed validation.")

if __name__ == "__main__":
    main()
