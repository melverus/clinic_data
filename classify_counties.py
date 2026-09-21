"""
classify_counties.py

For each county centroid, counts how many CPCs and how many real
Planned Parenthood clinics fall within a given radius, then classifies
the county into one of:
    - "cpc_only"     -- CPC(s) nearby, zero real clinics nearby
    - "dual_presence" -- both nearby
    - "pp_dominant"  -- real clinics nearby, zero CPCs nearby
    - "no_presence"  -- neither nearby

Radius defaults to 15 miles, matching the methodology used in the
2024 JMIR spatial-analysis study this project's approach is adapted
from.

Requires: 'county_centroids' table (run load_county_centroids.py first)
          and geocoded 'cpcs'/'pps' tables (lat/lon populated).

Usage:
    python classify_counties.py --db clinics.db --radius-miles 15
"""

import argparse
import sqlite3
import math
import pandas as pd


def haversine_miles(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in miles."""
    R = 3958.8  # Earth's radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def classify(cpc_count: int, pp_count: int) -> str:
    if cpc_count > 0 and pp_count == 0:
        return "cpc_only"
    if cpc_count > 0 and pp_count > 0:
        return "dual_presence"
    if cpc_count == 0 and pp_count > 0:
        return "pp_dominant"
    return "no_presence"


def main():
    parser = argparse.ArgumentParser(description="Classify counties by CPC/PP presence within a radius.")
    parser.add_argument("--db", default="clinics.db", help="Path to SQLite database")
    parser.add_argument("--radius-miles", type=float, default=15.0, help="Radius in miles (default 15, per JMIR study methodology)")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)

    counties = pd.read_sql_query("SELECT geoid, state, county_name, lat, lon FROM county_centroids", conn)
    cpcs = pd.read_sql_query("SELECT lat, lon FROM cpcs WHERE lat IS NOT NULL AND lon IS NOT NULL", conn)
    pps = pd.read_sql_query("SELECT lat, lon FROM pps WHERE lat IS NOT NULL AND lon IS NOT NULL", conn)

    if counties.empty:
        print("No counties found. Run load_county_centroids.py first.")
        return
    if cpcs.empty and pps.empty:
        print("No geocoded CPC/PP rows found. Run geocode_table.py on both tables first.")
        return

    print(f"Classifying {len(counties)} counties against {len(cpcs)} CPCs and {len(pps)} PP clinics "
          f"(radius: {args.radius_miles} miles)...")

    results = []
    for i, county in counties.iterrows():
        cpc_nearby = sum(
            1 for _, c in cpcs.iterrows()
            if haversine_miles(county["lat"], county["lon"], c["lat"], c["lon"]) <= args.radius_miles
        )
        pp_nearby = sum(
            1 for _, p in pps.iterrows()
            if haversine_miles(county["lat"], county["lon"], p["lat"], p["lon"]) <= args.radius_miles
        )
        category = classify(cpc_nearby, pp_nearby)
        results.append({
            "geoid": county["geoid"],
            "state": county["state"],
            "county_name": county["county_name"],
            "cpc_count_nearby": cpc_nearby,
            "pp_count_nearby": pp_nearby,
            "category": category,
        })
        if (i + 1) % 250 == 0:
            print(f"  ...{i + 1}/{len(counties)} counties processed")

    results_df = pd.DataFrame(results)
    results_df.to_sql("county_classification", conn, if_exists="replace", index=False)
    conn.close()

    print(f"\nDone. Wrote 'county_classification' table ({len(results_df)} rows) to {args.db}")
    print("\nSummary:")
    print(results_df["category"].value_counts().to_string())


if __name__ == "__main__":
    main()