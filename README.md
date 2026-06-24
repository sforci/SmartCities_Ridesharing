# Smart Cities RideSharing — Chicago

Repository for the **Data Science Lab on Smart Cities** course (University of Milan-Bicocca).

Spatial inequity analysis between ridesourcing (Uber/Lyft) usage and socio-demographic vulnerability across Chicago's 77 Community Areas.

## Research question

Does ridesourcing act as a mobility equalizer or as a costly substitute for public transport in vulnerable areas?

## Project structure

```
SmartCities_Ridesharing/
├── SmartCities_RideSharing.ipynb   # main analysis
├── utils.py                        # TNP download and population loading
├── requirements.txt
├── data/                           # local data (geojson, CSV)
└── ridesharing_report/             # LaTeX report (rho-class)
```

## Setup

```bash
git clone https://github.com/sforci/SmartCities_Ridesharing.git
cd SmartCities_Ridesharing
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook SmartCities_RideSharing.ipynb
```

## Indicators

| Indicator | Description |
|---|---|
| **TUI** | Transport Usage Index: TNP trips per 1,000 residents |
| **Hardship Index** | Composite socioeconomic hardship score (Chicago Data Portal) |
| **Per capita income** | Per capita income by Community Area |
| **SDVI** | Socio-demographic vulnerability index (mean z-score of Hardship + income disadvantage) |
| **CCVI** | Auxiliary health vulnerability index (not included in SDVI) |

Community Area 76 (O'Hare) is excluded from socio-demographic modeling.

## Data sources

- [TNP Trips 2018–2022](https://data.cityofchicago.org/Transportation/Transportation-Network-Providers-Trips-2018-2022-/m6dm-c72p)
- [TNP Trips 2023–2024](https://data.cityofchicago.org/Transportation/Transportation-Network-Providers-Trips-2023-2024-/n26f-ihde)
- [Community Area boundaries](https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Community-Areas-Map/cauq-8yn6)
- [Hardship Index](https://data.cityofchicago.org/Health-Human-Services/Selected-socioeconomic-indicators-by-neighborhood/i9hv-en6g)
- [CCVI](https://data.cityofchicago.org/Health-Human-Services/Chicago-COVID-19-Community-Vulnerability-Index-CCV/xhc6-88s9)
- CMAP Community Data Snapshots (population by CA)

TNP data can be re-downloaded via API from the notebook (`utils.source_tnp_counts`). Vulnerability CSVs are in `data/`.

## Branches

- `main` — base notebook (TUI)
- `fn-health` — SDVI integration (Hardship + income), correlations, bivariate maps, and LaTeX report

## Report

See [`ridesharing_report/README.md`](ridesharing_report/README.md) for PDF compilation instructions.

```bash
cd ridesharing_report && make pdf
```

## Team

- Francesca Negri (`fn-health`)
- Silvia Forcina Barrero — [sforci](https://github.com/sforci), original repository
