"""
geocode_table.py

Adds lat/lon columns to a table in the SQLite database by geocoding
each row's address via Nominatim (OpenStreetMap), and writes the
coordinates directly back into that table.

Safe to stop and re-run: rows that already have lat/lon are skipped,
so an interrupted run just picks back up where it left off.

Usage:
    python3 geocode.py --db clinics.db --table cpcs
    python3 geocode.py --db clinics.db --table pps --limit 5   # test first
"""

import argparse
import sqlite3
import time
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


def ensure_lat_lon_columns(conn, table: str):
    """Add lat/lon columns if they don't already exist."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    existing_cols = {row[1] for row in cursor.fetchall()}
    if "lat" not in existing_cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN lat REAL")
    if "lon" not in existing_cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN lon REAL")
    conn.commit()


import re

SUITE_PATTERN = re.compile(
    r"[,\s]*(suite|ste\.?|unit|#|apt\.?|floor|fl\.?|room|rm\.?)\s*\S+",
    re.IGNORECASE,
)


def strip_suite(street_address: str) -> str:
    """Remove suite/unit/apt/floor info that often breaks Nominatim's free-text search."""
    return SUITE_PATTERN.sub("", street_address).strip().rstrip(",")


def build_full_address(row: dict, drop_suite: bool = False) -> str:
    street = row.get("street_address", "") or ""
    if drop_suite:
        street = strip_suite(street)
    # if street_address already looks like a full address
    # (2+ commas — e.g. "855 Central Ave., Albany, NY 12206, USA"),
    # use it as-is instead of appending city/state/zip again
    if street.count(",") >= 2:
        return street.strip()

    parts = [street, row.get("city", ""), row.get("state", ""), row.get("zip", "")]
    return ", ".join(p.strip() for p in parts if p and str(p).strip())



def main():
    parser = argparse.ArgumentParser(description="Geocode a table's addresses and write lat/lon back to the DB.")
    parser.add_argument("--db", default="reproductive_rights.db", help="Path to SQLite database")
    parser.add_argument("--table", required=True, help="Table name to geocode")
    parser.add_argument("--limit", type=int, default=None, help="Only process first N ungeocoded rows (for testing)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests (Nominatim requires >= 1)")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    ensure_lat_lon_columns(conn, args.table)

    query = f"SELECT rowid, * FROM {args.table} WHERE lat IS NULL OR lon IS NULL"
    if args.limit:
        query += f" LIMIT {args.limit}"
    rows = conn.execute(query).fetchall()

    print(f"{len(rows)} rows need geocoding in '{args.table}'.")
    if not rows:
        conn.close()
        return

    geolocator = Nominatim(user_agent="portfolio-research-script (contact: replace-with-your-email)", timeout=10)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=args.delay, max_retries=2, error_wait_seconds=5)

    success, failed = 0, 0
    for i, row in enumerate(rows):
        row_dict = dict(row)
        address = build_full_address(row_dict)

        if not address:
            print(f"[{i+1}/{len(rows)}] SKIPPED (no address): rowid {row['rowid']}")
            failed += 1
            continue

        location = None
        attempts = [
            address,
            build_full_address(row_dict, drop_suite=True),  # retry without suite/unit info
            ", ".join(p for p in [row_dict.get("city",""), row_dict.get("state",""), row_dict.get("zip","")] if p),  # city/state/zip fallback
        ]
        tried = set()
        for attempt_address in attempts:
            if not attempt_address or attempt_address in tried:
                continue
            tried.add(attempt_address)
            try:
                location = geocode(attempt_address)
            except Exception as e:
                print(f"[{i+1}/{len(rows)}] ERROR geocoding '{attempt_address}': {e}")
                location = None
            if location:
                address = attempt_address  # record which version actually worked
                break

        if location:
            conn.execute(
                f"UPDATE {args.table} SET lat = ?, lon = ? WHERE rowid = ?",
                (location.latitude, location.longitude, row["rowid"]),
            )
            conn.commit()
            print(f"[{i+1}/{len(rows)}] OK: {address} -> ({location.latitude:.4f}, {location.longitude:.4f})")
            success += 1
        else:
            print(f"[{i+1}/{len(rows)}] NOT FOUND: {address}")
            failed += 1

    conn.close()
    print(f"\nDone. {success} geocoded, {failed} failed/skipped.")
    if failed:
        print("Re-run the same command to retry failed/remaining rows — already-geocoded rows are skipped automatically.")


if __name__ == "__main__":
    main()