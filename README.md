# Reproductive Healthcare Access: CPC vs Clinic Location Analysis

**A data pipeline and analysis examining the geographic distribution of Crisis Pregnancy Centers (CPCs) and Planned Parenthood health centers across the United States — built to surface where deceptive-marketing reproductive health facilities may outnumber verified medical providers.**
 
---

## Data Sources
 
| Dataset | Source | Access Method |
|---|---|---|
| Crisis Pregnancy Center locations | [Reproaction's Fake Clinic Database](https://reproaction.org/database/) | PDF extraction |
| Planned Parenthood health center locations | [plannedparenthood.org](https://www.plannedparenthood.org) | Custom web scraper (`scrape_planned_parenthood.py`) |
| Planned Parenthood street addresses | Individual health center pages | Second-pass scraper (`scrape_pp_addresses.py`) |

Addresses for 412/503 Planned Parenthood locations were obtained. Locations with no address information were discarded. Locations for 2429 Crisis Pregnancy Centers were provided by the Reproaction database. This brings the total to 2841 entries for this analysis. 

The addresses were then geocoded to latitude and longitude coordinates via Nomination (OpenStreetMap). ('geocode.py'). These coordinates are used for clinic location and distance analysis. 

Each data point was given a classification to one of 3,143 counties recorded in the 2024 census dataset publicly available at:
[2024 Census Data](https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_counties_national.zip)


 
---
