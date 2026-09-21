"""
load_county_centroids.py

Loads the Census Bureau's County Gazetteer File (tab-delimited .txt,
after unzipping the download) into a 'county_centroids' table in your
database. This gives you ~3,143 US counties with their centroid
lat/lon -- the reference points used to check "what's nearby" for
the CPC-vs-clinic zone classification.

Source: https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_counties_national.zip

Usage:
    python load_county_centroids.py --file 2024_Gaz_counties_national.txt --db clinics.db
"""

import argparse
import sqlite3
import csv


def main():
    parser = argparse.ArgumentParser(description="Load Census county gazetteer file into the database.")
    parser.add_argument("--file", required=True, help="Path to the unzipped Gazetteer .txt file")
    parser.add_argument("--db", default="clinics.db", help="Path to SQLite database")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.execute("DROP TABLE IF EXISTS county_centroids")
    conn.execute("""
        CREATE TABLE county_centroids (
            geoid TEXT,
            state TEXT,
            county_name TEXT,
            lat REAL,
            lon REAL
        )
    """)

    # The Gazetteer file is tab-delimited. Column names can vary slightly
    # by year, so we read the header and look up the columns by name
    # rather than assuming a fixed position.
    with open(args.file, encoding="latin-1") as f:
        reader = csv.DictReader(f, delimiter="\t")
        reader.fieldnames = [name.strip() for name in reader.fieldnames]  # trim stray whitespace

        rows_to_insert = []
        for row in reader:
            row = {k.strip(): v.strip() for k, v in row.items()}
            rows_to_insert.append((
                row.get("GEOID"),
                row.get("USPS"),
                row.get("NAME"),
                float(row["INTPTLAT"]),
                float(row["INTPTLONG"]),
            ))

    conn.executemany(
        "INSERT INTO county_centroids (geoid, state, county_name, lat, lon) VALUES (?, ?, ?, ?, ?)",
        rows_to_insert,
    )
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM county_centroids").fetchone()[0]
    print(f"Loaded {count} counties into 'county_centroids' table in {args.db}")
    conn.close()


if __name__ == "__main__":
    main()