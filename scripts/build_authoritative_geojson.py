import json
import urllib.request
import re
from pathlib import Path

DATA_DIR = Path("data")
COORD_FILE = DATA_DIR / "district_coordinates.json"
GEOJSON_FILE = DATA_DIR / "south_india_districts.geojson"

ALIASES = {
    # Tamil Nadu
    "chengalpattu": ["chengalpattu", "chengalpet", "chengalpattu district"],
    "kallakurichi": ["kallakurichi", "kallakkurichi"],
    "mayiladuthurai": ["mayiladuthurai", "mayiladuturai"],
    "ranipet": ["ranipet", "ranipettai"],
    "tenkasi": ["tenkasi"],
    "tirupathur": ["tirupathur", "tirupattur"],
    "kanyakumari": ["kanniyakumari", "kanyakumari"],
    "nilgiris": ["the nilgiris", "nilgiris", "nilgiri"],
    "tirunelveli": ["tirunelveli", "tirunelveli kattabo"],
    "tiruchirappalli": ["tiruchirappalli", "trichy", "tiruchirapalli"],
    "kancheepuram": ["kancheepuram", "kanchipuram"],
    "viluppuram": ["viluppuram", "villupuram"],
    "thoothukudi": ["thoothukkudi", "thoothukudi", "tuticorin"],
    "tiruvallur": ["tiruvallur", "thiruvallur"],
    "tiruvarur": ["thiruvarur", "tiruvarur"],
    "tiruvannamalai": ["tiruvannamalai", "thiruvannamalai"],
    
    # Karnataka
    "vijayanagara": ["vijayanagara", "vijayanagar"],
    "bengaluru urban": ["bengaluru urban", "bangalore", "bangalore urban", "bengaluru"],
    "bengaluru rural": ["bengaluru rural", "bangalore rural"],
    "belagavi": ["belagavi", "belgaum"],
    "ballari": ["ballari", "bellary"],
    "kalaburagi": ["kalaburagi", "gulbarga"],
    "mysuru": ["mysuru", "mysore"],
    "shivamogga": ["shivamogga", "shimoga"],
    "tumakuru": ["tumakuru", "tumkur"],
    "vijayapura": ["vijayapura", "bijapur"],
    "chamarajanagara": ["chamarajanagar", "chamarajanagara"],
    "chikkamagaluru": ["chikkamagaluru", "chikmagalur"],
    "chikkaballapura": ["chikkaballapur", "chikkaballapura", "chikballapur"],
    "dakshina kannada": ["dakshina kannada", "south canara", "dakshin kannad"],
    "uttara kannada": ["uttara kannada", "north canara", "uttar kannad"],
    "bagalkote": ["bagalkote", "bagalkot"],
    "ramanagara": ["ramanagara", "ramanagar"],
    "yadgir": ["yadgir", "yadgiri"],
    "davanagere": ["davanagere", "davangere"],
    
    # Kerala
    "thiruvananthapuram": ["thiruvananthapuram", "trivandrum"],
    "ernakulam": ["ernakulam", "cochin"],
    "kozhikode": ["kozhikode", "calicut"],
    "alappuzha": ["alappuzha", "alleppey"],
    "palakkad": ["palakkad", "palghat"],
    "kannur": ["kannur", "cannanore"],
    "thrissur": ["thrissur", "trichur"],
    "wayanad": ["wayanad", "wynad"],
    "kasaragod": ["kasaragod", "kasargod"]
}

def normalize(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

def main():
    print("Loading our 83 South India district coordinate definitions...")
    with open(COORD_FILE, "r", encoding="utf-8") as f:
        our_districts = json.load(f)
    print(f"Total target districts: {len(our_districts)}")

    print("Fetching authoritative administrative district boundary GeoJSON from INDIAN-SHAPEFILES...")
    url = "https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/INDIA/INDIA_DISTRICTS.geojson"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw_geojson = json.loads(resp.read().decode("utf-8"))

    print(f"Total features in source GeoJSON: {len(raw_geojson['features'])}")

    state_name_map = {
        "TAMIL NADU": "Tamil Nadu",
        "KERALA": "Kerala",
        "KARNATAKA": "Karnataka"
    }

    # Index source features by state and normalized district name
    geo_features_by_state = {"Tamil Nadu": {}, "Kerala": {}, "Karnataka": {}}
    for feat in raw_geojson["features"]:
        props = feat.get("properties", {})
        raw_st = str(props.get("state", "")).strip().upper()
        if raw_st in state_name_map:
            st = state_name_map[raw_st]
            raw_dt = str(props.get("district", "")).strip()
            norm_dt = normalize(raw_dt)
            geo_features_by_state[st][norm_dt] = (raw_dt, feat)

    # Match each of our 83 districts
    matched_features = []
    unmatched = []

    for dist in our_districts:
        st = dist["state"]
        dist_id = dist["id"]
        dist_name = dist["name"]
        norm_name = normalize(dist_name)

        state_geos = geo_features_by_state.get(st, {})
        matched_feat = None
        matched_geo_name = None

        # 1. Direct match
        if norm_name in state_geos:
            matched_geo_name, matched_feat = state_geos[norm_name]
        else:
            # 2. Alias match
            alias_list = ALIASES.get(norm_name, [])
            for alias in alias_list:
                norm_alias = normalize(alias)
                if norm_alias in state_geos:
                    matched_geo_name, matched_feat = state_geos[norm_alias]
                    break

        if not matched_feat:
            # 3. Substring match fallback
            for g_norm, (g_raw, g_feat) in state_geos.items():
                if norm_name in g_norm or g_norm in norm_name:
                    matched_geo_name, matched_feat = g_raw, g_feat
                    break

        if matched_feat:
            # Build authoritative feature with required properties
            new_feature = {
                "type": "Feature",
                "properties": {
                    "id": dist_id,
                    "name": dist_name,
                    "state": dist["state"],
                    "latitude": dist["latitude"],
                    "longitude": dist["longitude"],
                    "elevation": dist["elevation"],
                    "source_district_name": matched_geo_name
                },
                "geometry": matched_feat["geometry"]
            }
            matched_features.append(new_feature)
        else:
            unmatched.append(dist)

    print("\n================ DATA-JOIN MATCHING REPORT ================")
    print(f"Total matched features: {len(matched_features)} / {len(our_districts)}")

    tn_matched = [f for f in matched_features if f["properties"]["state"] == "Tamil Nadu"]
    kl_matched = [f for f in matched_features if f["properties"]["state"] == "Kerala"]
    ka_matched = [f for f in matched_features if f["properties"]["state"] == "Karnataka"]

    print(f"Tamil Nadu : {len(tn_matched)} / 38 matched")
    print(f"Kerala     : {len(kl_matched)} / 14 matched")
    print(f"Karnataka  : {len(ka_matched)} / 31 matched")

    if unmatched:
        print(f"FAILED TO MATCH: {[(d['id'], d['name'], d['state']) for d in unmatched]}")
        for u in unmatched:
            st = u['state']
            print(f"Available in {st}: {list(geo_features_by_state[st].keys())}")
        raise ValueError(f"Could not match {len(unmatched)} districts!")

    output_geojson = {
        "type": "FeatureCollection",
        "features": matched_features
    }

    with open(GEOJSON_FILE, "w", encoding="utf-8") as f:
        json.dump(output_geojson, f, indent=2)

    print(f"\nSuccessfully generated authoritative GeoJSON: {GEOJSON_FILE}")
    print(f"File size: {GEOJSON_FILE.stat().st_size / 1024:.2f} KB")

if __name__ == "__main__":
    main()
