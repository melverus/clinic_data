# Reproductive Healthcare Access: CPC vs Clinic Location Analysis

**A data pipeline and analysis examining the geographic distribution of Crisis Pregnancy Centers (CPCs) and Planned Parenthood health centers across the United States — built to surface where deceptive-marketing reproductive health facilities may outnumber verified medical providers.**
 
---

## Data Sources
 
| Dataset | Source | Access Method |
|---|---|---|
| Crisis Pregnancy Center locations | [Reproaction's Fake Clinic Database](https://reproaction.org/database/) | PDF extraction |
| Planned Parenthood health center locations | [plannedparenthood.org](https://www.plannedparenthood.org) | Custom web scraper (`scrape_planned_parenthood.py`) |
| Planned Parenthood street addresses | Individual health center pages | Second-pass scraper (`scrape_pp_addresses.py`) |
 
---
