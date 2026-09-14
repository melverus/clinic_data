"""
scrape_pp_addresses.py

Second-pass scraper: visits each individual Planned Parenthood health
center detail page (using the 'url' column from pp_health_centers.csv,
produced by scrape_planned_parenthood.py) and extracts the full street
address from the "Get Directions" Google Maps link embedded on the page,
e.g.:
    https://maps.google.com/?daddr=855+Central+Ave.,+Albany,+NY+12206,+USA+(Albany+Health+Center)
    -> "855 Central Ave., Albany, NY 12206 USA"

A 1.5-2 second delay is used between requests by default.

Usage:
    python scrape_pp_addresses.py --in pp_health_centers.csv --out pp_health_centers_with_address.csv --limit 5   # test first
    python scrape_pp_addresses.py --in pp_health_centers.csv --out pp_health_centers_with_address.csv            # then full run
"""

import argparse
import csv
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; portfolio-research-script/1.0; "
                  "non-commercial data science project; contact: melissagiluso@gmail.com)"
}

# Matches: https://maps.google.com/?daddr=855+Central+Ave.,+Albany,+NY+12206,+USA+(Albany+Health+Center)
DADDR_PATTERN = re.compile(r'maps\.google\.com/\?daddr=([^"\'&]+)')


def fetch_page(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def extract_address(html: str) -> str:
    """
    Pull the address out of the 'Get Directions' Google Maps link.
    Strips the trailing '(Facility Name)' parenthetical that Google
    Maps links include, since that's the center name, not the address.

    DEBUG TIP: if this returns '', the site may have changed how it
    renders the directions link. Search the raw HTML for 'daddr=' to
    confirm the pattern still exists, and adjust DADDR_PATTERN above.
    """
    match = DADDR_PATTERN.search(html)
    if not match:
        return ""
    raw = urllib.parse.unquote_plus(match.group(1))
    # Strip trailing "(Facility Name)" if present
    raw = re.sub(r"\s*\([^)]*\)\s*$", "", raw).strip()
    return raw


def main():
    parser = argparse.ArgumentParser(description="Scrape full addresses from PP health center detail pages.")
    parser.add_argument("--in", dest="in_csv", required=True, help="Input CSV (from scrape_planned_parenthood.py)")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds between requests (default 1.5)")
    parser.add_argument("--limit", type=int, default=None, help="Only process first N rows (for testing)")
    args = parser.parse_args()

    with open(args.in_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if args.limit:
        rows = rows[:args.limit]

    results = []
    for i, row in enumerate(rows):
        url = row.get("url", "")
        address = ""
        if url:
            try:
                html = fetch_page(url)
                address = extract_address(html)
            except Exception as e:
                print(f"[{i+1}/{len(rows)}] FAILED ({row.get('name','?')}): {e}")

        status = "OK" if address else "NO ADDRESS FOUND"
        print(f"[{i+1}/{len(rows)}] {row.get('name','?')} -> {address or status}")

        row["street_address"] = address
        results.append(row)

        if i < len(rows) - 1:
            time.sleep(args.delay)

    fieldnames = list(results[0].keys()) if results else ["name","city","state","zip","url","street_address"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    found = sum(1 for r in results if r.get("street_address"))
    print(f"\nDone. {found}/{len(results)} addresses found. Written to {args.out}")


if __name__ == "__main__":
    main()
