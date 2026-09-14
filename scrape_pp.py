"""
scrape_pp.py

Scrapes Planned Parenthood's per-state health center directory pages
(e.g. https://www.plannedparenthood.org/health-center/ca) and produces
a clean CSV of health center name, city, state, and detail-page URL.

This targets a STATIC listing page (no JS rendering, no personal
inputs required) -- not the ZIP/age/last-period search form. Only
~51 requests total (one per state + DC), with a pause in between each.

Usage:
    python3 scrape_pp.py --out pp_health_centers.csv --states ca   # test first
    python3 scrape_pp.py --out pp_health_centers.csv               # then full run
"""

from bs4 import BeautifulSoup
import argparse
import csv
import re
import time
import urllib.request
from pathlib import Path

STATE_ABBRS = [
    "al","ak","az","ar","ca","co","ct","de","fl","ga","hi","id","il","in","ia",
    "ks","ky","la","me","md","ma","mi","mn","ms","mo","mt","ne","nv","nh","nj",
    "nm","ny","nc","nd","oh","ok","or","pa","ri","sc","sd","tn","tx","ut","vt",
    "va","wa","wv","wi","wy","dc",
]

BASE_URL = "https://www.plannedparenthood.org/health-center/{}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; portfolio-research-script/1.0; "
                  "non-commercial data science project; contact: replace-with-your-email)"
}


def fetch_state_page(state_abbr: str) -> str:
    url = BASE_URL.format(state_abbr)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def parse_centers(html: str, state_abbr: str) -> list:
    """
    Extract (name, url) pairs from real anchor tags whose href matches
    the health-center detail-page pattern, then pull city/zip from the
    URL slug itself
    """
    soup = BeautifulSoup(html, "html.parser")
    centers = []

    href_pattern = re.compile(r"^/health-center/([^/]+)/([^/]+)/(\d{5})/([^/]+)/?$")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        match = href_pattern.match(href)
        if not match:
            continue
        state_slug, city_slug, zip_code, facility_slug = match.groups()
        name = a.get_text(strip=True)
        if not name:
            continue
        centers.append({
            "name": name,
            "city": city_slug.replace("-", " ").title(),
            "state": state_abbr.upper(),
            "zip": zip_code,
            "url": f"https://www.plannedparenthood.org{href}",
        })

    seen = set()
    unique_centers = []
    for c in centers:
        key = (c["name"], c["url"])
        if key not in seen:
            seen.add(key)
            unique_centers.append(c)

    return unique_centers


def main():
    parser = argparse.ArgumentParser(description="Scrape Planned Parenthood's state health center directories.")
    parser.add_argument("--out", default="pp_health_centers.csv", help="Output CSV path")
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds to wait between requests (default 1.5)")
    parser.add_argument("--states", nargs="*", default=None,
                         help="Optional: limit to specific state abbreviations (e.g. --states ny ca). Default: all 50 + DC.")
    args = parser.parse_args()

    states = args.states if args.states else STATE_ABBRS

    all_centers = []
    for i, state in enumerate(states):
        try:
            html = fetch_state_page(state)
            centers = parse_centers(html, state)
            print(f"[{state.upper()}] {len(centers)} centers found")
            all_centers.extend(centers)
        except Exception as e:
            print(f"[{state.upper()}] FAILED: {e}")

        if i < len(states) - 1:
            time.sleep(args.delay)

    out_path = Path(args.out)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "city", "state", "zip", "url"])
        writer.writeheader()
        writer.writerows(all_centers)

    print(f"\nDone. {len(all_centers)} total health centers written to {out_path}")


if __name__ == "__main__":
    main()