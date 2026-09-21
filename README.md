# Reproductive Healthcare Access: CPC vs. Clinic Location Analysis

**A data pipeline and analysis examining the geographic distribution of Crisis Pregnancy Centers (CPCs) and Planned Parenthood health centers across the United States — built to surface where deceptive-marketing reproductive health facilities may outnumber verified medical providers.**

---

<img width="1890" height="871" alt="County classification map preview" src="https://github.com/user-attachments/assets/21fa300d-c951-4966-9b62-a3e451486430" />

**[→ Open the full interactive county map](https://melverus.github.io/clinic_data/charts/county_map.html)** &nbsp;|&nbsp; **[→ Open the interactive facility map](https://melverus.github.io/clinic_data/charts/clinic_map.html)**

*(GitHub strips scripts from README files, so the map above is a static preview — click through for the live, clickable version.)*

---

## Key Finding

For every US county, the analysis checks what's within a 15-mile radius (matching the methodology of a 2024 JMIR spatial-analysis study on CPC/clinic access) and classifies it as:

- **CPC-only** — one or more Crisis Pregnancy Centers within 15 miles, zero real clinics
- **Dual-presence** — both present within 15 miles
- **Clinic-dominant** — real clinic(s) within 15 miles, no CPCs
- **No presence** — neither present within 15 miles

The resulting map shows this isn't evenly distributed. **Among the 1,456 US counties with any reproductive health facility within 15 miles, nearly 4 out of 5 (79.8%) have only a Crisis Pregnancy Center — no verified medical provider at all.** Just 20.2% of "covered" counties have access to a real clinic. Overall, 36.1% of all US counties (1,162 of 3,222) are CPC-only zones, compared to only 0.5% where a real clinic has no CPC competing nearby.


---

## Data Sources

| Dataset | Source | Access Method |
|---|---|---|
| Crisis Pregnancy Center locations | [Reproaction's Fake Clinic Database](https://reproaction.org/database/) | PDF extraction (`extract_cpc.py`) |
| Planned Parenthood health center locations | [plannedparenthood.org](https://www.plannedparenthood.org) | Custom web scraper (`scrape_pp.py`) |
| Planned Parenthood street addresses | Individual health center pages | Second-pass scraper (`scrape_pp_addresses.py`) |
| County boundaries & centroids | [US Census Bureau 2024 County Gazetteer File](https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_counties_national.zip) | Direct download (`load_counties.py`) |

**Dataset size:** 2,429 Crisis Pregnancy Centers (Reproaction) and 412 of 503 scraped Planned Parenthood locations had a usable street address (the remaining 91 were discarded rather than geocoded on incomplete data) — **2,841 total facility records** in the analysis.

**Geocoding:** All addresses were converted to latitude/longitude via Nominatim (OpenStreetMap), using a rate-limited request pattern (`geocode.py`) with a fallback strategy for addresses that failed to resolve on the first attempt (see [Methodology](#methodology--data-cleaning)).

**County classification:** Each of the 3,143 US counties (2024 Census Gazetteer) was checked against every geocoded facility to count how many CPCs and how many real clinics fall within 15 miles, producing the classification used in the map above (`classify_counties.py`).

---

## Tech Stack

- **Python** — `pandas`, `pdfplumber`, `BeautifulSoup`, `matplotlib`, `folium`, `geopy`
- **SQL** — SQLite, via `sqlite3` and `pandas.read_sql_query`
- **Data extraction** — PDF table parsing, static HTML web scraping, address geocoding
- **Geospatial analysis** — haversine distance calculations, county-level spatial classification, choropleth mapping



---

## Methodology & Data Cleaning

**The CPC dataset started as an unstructured PDF**, not a clean CSV. Since the source PDF had no table gridlines, columns were reconstructed by parsing word-level x-coordinates and mapping them to inferred column ranges (`extract_cpc.py`). This surfaced a real data-quality issue: an off-by-a-fraction-of-a-pixel column boundary was silently merging the "Advertises as APR?" field into the adjacent website-URL column, corrupting that field for every row. It was caught during validation, isolated, and fixed.

**The Planned Parenthood dataset required two scraping passes**, since the site's state-level directory pages list only name/city/zip, with full addresses living on each facility's individual page. The second-pass scraper parses each page's embedded Google Maps "Get Directions" link — a more reliable extraction point than loose page text — and runs at a deliberately conservative rate out of respect for a nonprofit health service's infrastructure. 91 of 503 locations lacked a resolvable address and were excluded rather than geocoded on incomplete data.

**Geocoding required a fallback strategy.** A meaningful share of addresses failed to resolve on the first pass, mostly due to suite/unit numbers ("Suite F," "#200") that free-text geocoders can't resolve. Each failed address is retried with suite info stripped, then falls back to a city/state/zip-level match if needed — logged so it's clear which precision level each point ultimately used.

**Verification against ground truth.** A handful of geocoded points were manually checked against known real-world addresses during development

---

## Skills Demonstrated

- **Data extraction from unstructured sources** — positional PDF table parsing, HTML scraping with respectful rate-limiting
- **Data validation** — catching and fixing a silent extraction bug, verifying geocoded points against real-world ground truth rather than trusting output blindly
- **Geospatial analysis** — geocoding pipelines with retry/fallback logic, haversine distance calculations, county-level spatial classification adapted from a published research methodology
- **SQL** — schema design, `GROUP BY`/`CASE WHEN`/`HAVING` aggregations
- **Python** — modular, single-responsibility, resumable scripts with CLI arguments (`argparse`)
- **Data visualization** — direct SQL-to-chart pipelines, interactive point maps with clustering, categorical choropleth mapping
- **Ethical data practices** — evaluating a data source's Terms of Use and technical structure before scraping it, and choosing not to scrape a source (Abortion Finder) where doing so would have required simulating sensitive personal queries against a crisis service

---

## Limitations

- CPC and clinic datasets reflect a snapshot in time; facility openings/closures are not tracked historically
- 91 of 503 scraped Planned Parenthood locations were excluded due to missing address data
- The 15-mile radius is a fixed threshold adapted from published research; it doesn't account for urban/rural differences in what a "reasonable distance" means
- County centroid-to-facility distance is a reasonable proxy for regional access, not a substitute for actual travel-time analysis
- CPC "advertises as APR" data reflects Reproaction's independent verification methodology, not a government or peer-reviewed source

---


## Setup

```bash
pip install pandas pdfplumber beautifulsoup4 matplotlib folium geopy --break-system-packages

# Build the database
python3 csv_to_sql.py --csv cpc_database.csv pp_health_centers_with_address.csv --table cpcs pps --db clinics.db
python3 geocode_table.py --db clinics.db --table cpcs
python3 geocode_table.py --db clinics.db --table pps

# County classification
python3 load_county_centroids.py --file 2024_Gaz_counties_national.txt --db clinics.db
python3 classify_counties.py --db clinics.db --radius-miles 15

# Visualizations
python3 visualize_clinic_data.py --db clinics.db --out charts
python3 map_county_classification.py --db clinics.db --out charts/county_map.html
```
