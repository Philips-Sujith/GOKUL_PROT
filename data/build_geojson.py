#!/usr/bin/env python3
"""
Generate authoritative GeoJSON polygon geometries for all 83 South India districts:
- Tamil Nadu (38 districts)
- Kerala (14 districts)
- Karnataka (31 districts)

Matches official Indian administrative district boundaries from INDIAN-SHAPEFILES / GADM,
normalizes district codes (TN-01..38, KL-01..14, KA-01..31), and generates clean,
contiguous boundary geometries with no artificial buffers, circles, or gaps.
"""

import json
import urllib.request
import re
import math
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
COORD_FILE = DATA_DIR / "district_coordinates.json"
GEOJSON_FILE = DATA_DIR / "south_india_districts.geojson"

# Exact Census / LGD code and ObjectId mapping for Karnataka districts
KARNATAKA_CODE_MAP = {
    "KA-01": {"dist_code": "0556", "objectid": "297", "name": "Bagalkote"},
    "KA-02": {"dist_code": "0565", "objectid": "302", "name": "Ballari"},
    "KA-03": {"dist_code": "0555", "objectid": "299", "name": "Belagavi"},
    "KA-04": {"dist_code": "0583", "objectid": "298", "name": "Bengaluru Rural"},
    "KA-05": {"dist_code": "0572", "objectid": "315", "name": "Bengaluru Urban"},
    "KA-06": {"dist_code": "0558", "objectid": "926", "name": "Bidar"},
    "KA-07": {"dist_code": "0578", "objectid": "303", "name": "Chamarajanagar"},
    "KA-08": {"dist_code": "0582", "objectid": "308", "name": "Chikkaballapura"},
    "KA-09": {"dist_code": "0570", "objectid": "301", "name": "Chikkamagaluru"},
    "KA-10": {"dist_code": "0566", "objectid": "304", "name": "Chitradurga"},
    "KA-11": {"dist_code": "0575", "objectid": "322", "name": "Dakshina Kannada"},
    "KA-12": {"dist_code": "0567", "objectid": "309", "name": "Davanagere"},
    "KA-13": {"dist_code": "0562", "objectid": "310", "name": "Dharwad"},
    "KA-14": {"dist_code": "0561", "objectid": "311", "name": "Gadag"},
    "KA-15": {"dist_code": "0574", "objectid": "313", "name": "Hassan"},
    "KA-16": {"dist_code": "0564", "objectid": "312", "name": "Haveri"},
    "KA-17": {"dist_code": "0579", "objectid": "314", "name": "Kalaburagi"},
    "KA-18": {"dist_code": "0576", "objectid": "1019", "name": "Kodagu"},
    "KA-19": {"dist_code": "0581", "objectid": "317", "name": "Kolar"},
    "KA-20": {"dist_code": "0560", "objectid": "305", "name": "Koppal"},
    "KA-21": {"dist_code": "0573", "objectid": "318", "name": "Mandya"},
    "KA-22": {"dist_code": "0577", "objectid": "319", "name": "Mysuru"},
    "KA-23": {"dist_code": "0559", "objectid": "307", "name": "Raichur"},
    "KA-24": {"dist_code": "0584", "objectid": "326", "name": "Ramanagara"},
    "KA-25": {"dist_code": "0568", "objectid": "320", "name": "Shivamogga"},
    "KA-26": {"dist_code": "0571", "objectid": "912", "name": "Tumakuru"},
    "KA-27": {"dist_code": "0569", "objectid": "813", "name": "Udupi"},
    "KA-28": {"dist_code": "0563", "objectid": "323", "name": "Uttara Kannada"},
    "KA-29": {"dist_code": "0738", "objectid": "306", "name": "Vijayanagara"},
    "KA-30": {"dist_code": "0557", "objectid": "324", "name": "Vijayapura"},
    "KA-31": {"dist_code": "0580", "objectid": "325", "name": "Yadgir"}
}

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

def point_line_distance(point, start, end):
    if start == end:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    n = abs((end[1] - start[1]) * point[0] - (end[0] - start[0]) * point[1] + end[0] * start[1] - end[1] * start[0])
    d = math.hypot(end[1] - start[1], end[0] - start[0])
    return n / d if d > 0 else 0

def rdp(points, epsilon):
    if len(points) < 3:
        return points
    dmax = 0.0
    index = 0
    end = len(points) - 1
    for i in range(1, end):
        d = point_line_distance(points[i], points[0], points[end])
        if d > dmax:
            index = i
            dmax = d
    if dmax > epsilon:
        rec1 = rdp(points[:index+1], epsilon)
        rec2 = rdp(points[index:], epsilon)
        return rec1[:-1] + rec2
    else:
        return [points[0], points[end]]

def simplify_geom(geom, epsilon=0.0008):
    gtype = geom['type']
    if gtype == 'Polygon':
        new_coords = []
        for ring in geom['coordinates']:
            simp = rdp(ring, epsilon)
            if len(simp) < 4:
                simp = ring
            new_coords.append([[round(c[0], 5), round(c[1], 5)] for c in simp])
        return {'type': 'Polygon', 'coordinates': new_coords}
    elif gtype == 'MultiPolygon':
        new_polys = []
        for poly in geom['coordinates']:
            new_rings = []
            for ring in poly:
                simp = rdp(ring, epsilon)
                if len(simp) < 4:
                    simp = ring
                new_rings.append([[round(c[0], 5), round(c[1], 5)] for c in simp])
            new_polys.append(new_rings)
        return {'type': 'MultiPolygon', 'coordinates': new_polys}
    return geom

def main():
    print(f"Reading target 83 districts from {COORD_FILE}...")
    with open(COORD_FILE, "r", encoding="utf-8") as f:
        our_districts = json.load(f)

    print("Fetching authoritative administrative boundary geometries from INDIAN-SHAPEFILES...")
    url = "https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/INDIA/INDIA_DISTRICTS.geojson"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw_geojson = json.loads(resp.read().decode("utf-8"))

    state_name_map = {
        "TAMIL NADU": "Tamil Nadu",
        "KERALA": "Kerala",
        "KARNATAKA": "Karnataka"
    }

    geo_features_by_state = {"Tamil Nadu": {}, "Kerala": {}, "Karnataka": {}}
    ka_features_by_dist_code = {}
    ka_features_by_objectid = {}

    for feat in raw_geojson["features"]:
        props = feat.get("properties") or {}
        raw_st = str(props.get("state") or "").strip().upper()
        if raw_st in state_name_map:
            st = state_name_map[raw_st]
            raw_dt = str(props.get("district") or "").strip()
            norm_dt = normalize(raw_dt)
            geo_features_by_state[st][norm_dt] = (raw_dt, feat)
            
            if st == "Karnataka":
                d_code = str(props.get("dist_code") or "").strip()
                obj_id = str(props.get("objectid") or "").strip()
                if d_code:
                    ka_features_by_dist_code[d_code] = (raw_dt, feat)
                if obj_id:
                    ka_features_by_objectid[obj_id] = (raw_dt, feat)

    matched_features = []
    unmatched = []

    for dist in our_districts:
        st = dist["state"]
        dist_id = dist["id"]
        dist_name = dist["name"]
        norm_name = normalize(dist_name)

        matched_feat = None
        matched_geo_name = None

        if st == "Karnataka" and dist_id in KARNATAKA_CODE_MAP:
            ka_info = KARNATAKA_CODE_MAP[dist_id]
            target_code = ka_info["dist_code"]
            target_obj = ka_info["objectid"]
            if target_code in ka_features_by_dist_code:
                matched_geo_name, matched_feat = ka_features_by_dist_code[target_code]
            elif target_obj in ka_features_by_objectid:
                matched_geo_name, matched_feat = ka_features_by_objectid[target_obj]

        if not matched_feat:
            state_geos = geo_features_by_state.get(st, {})
            if norm_name in state_geos:
                matched_geo_name, matched_feat = state_geos[norm_name]
            else:
                alias_list = ALIASES.get(norm_name, [])
                for alias in alias_list:
                    norm_alias = normalize(alias)
                    if norm_alias in state_geos:
                        matched_geo_name, matched_feat = state_geos[norm_alias]
                        break

        if matched_feat:
            simplified_geom = simplify_geom(matched_feat["geometry"], epsilon=0.0008)
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
                "geometry": simplified_geom
            }
            matched_features.append(new_feature)
        else:
            unmatched.append(dist)

    tn_count = len([f for f in matched_features if f["properties"]["state"] == "Tamil Nadu"])
    kl_count = len([f for f in matched_features if f["properties"]["state"] == "Kerala"])
    ka_count = len([f for f in matched_features if f["properties"]["state"] == "Karnataka"])

    print(f"Matched {len(matched_features)}/83 features:")
    print(f"  - Tamil Nadu : {tn_count}/38")
    print(f"  - Kerala     : {kl_count}/14")
    print(f"  - Karnataka  : {ka_count}/31")

    if unmatched:
        raise ValueError(f"Unmatched districts: {unmatched}")

    output_geojson = {
        "type": "FeatureCollection",
        "features": matched_features
    }

    with open(GEOJSON_FILE, "w", encoding="utf-8") as f:
        json.dump(output_geojson, f, indent=2)

    print(f"Saved authoritative South India GeoJSON to {GEOJSON_FILE} ({GEOJSON_FILE.stat().st_size / 1024:.1f} KB)")

    # Also copy to frontend/public/data/south_india_districts.geojson
    frontend_geojson = Path(__file__).resolve().parent.parent / "frontend" / "public" / "data" / "south_india_districts.geojson"
    frontend_geojson.parent.mkdir(parents=True, exist_ok=True)
    with open(frontend_geojson, "w", encoding="utf-8") as f:
        json.dump(output_geojson, f, indent=2)
    print(f"Copied to {frontend_geojson}")

if __name__ == "__main__":
    main()
