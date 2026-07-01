# Smart Cities RideSharing — Chicago

Repository for the **Data Science Lab for Smart Cities** final project (Università degli Studi di Milano-Bicocca).

Ecological analysis of ridesourcing (Uber/Lyft) equity across Chicago's 77 Community Areas (75 in the inferential sample, O'Hare excluded).

## Research question

Does ridesourcing act as a mobility equaliser in transit-poor, vulnerable peripheries, or as a costly substitute concentrated where public transport is already strong?

**Main result (2024):** the compensatory hypothesis is **rejected**. TUI peaks in central and lakefront areas, correlates negatively with vulnerability (Pearson r up to -0.54) and positively with transit access (r = 0.75). The preferred model is a Spatial Error Model on log(1+TUI) (AIC 75.2 vs 80.0 for SLAG).

## Repository structure

```
SmartCities_Ridesharing/
├── SmartCities_RideSharing.ipynb   # main analysis pipeline
├── utils.py                        # data loading, indicators, maps, spatial stats, regression helpers
├── requirements.txt
├── data/                           # cached CSV/GeoJSON (see below)
└── ridesharing_report/
    └── DSLSC Project Template/     # LaTeX final essay (ProjectTemplate.tex)
```

## Notebook pipeline

| Section | Content |
|--------|---------|
| 1. Data sources | Chicago Data Portal, CMAP, CTA layers, GTFS |
| 2. TUI | Monthly TNP pickups per 1,000 residents; **median** 2024 value per CA |
| 3. Vulnerability | `load_vulnerability_data` + `build_vulnerability_indices` (SDVI, HSVI) |
| 4. TUI vs vulnerability | Pearson/Spearman correlations, scatterplots, choropleth maps |
| 5. Weighted TUI | Income-normalised annual ridesourcing spend (median fare by CA) |
| 6. Loop travel time | Mean `trip_seconds` to Loop (dropoff CA 32) by pickup CA |
| 7. Transit Accessibility Index | Bus/rail density + GTFS weekday departures per km² |
| — | Moran's I, Moran scatterplot, LISA clusters on TUI |
| 8. OLS regression | log(1+TUI), z-scored predictors, HC3 robust SE |
| 9. Spatial models | SEM vs SLAG (`spreg`); SEM preferred |
| Appendix A | VIF, reduced models (robustness) |

Maps and charts are saved with `save_chart()` to `data/output_charts/` (gitignored).

## Indicators

| Indicator | Built in repo? | Description |
|-----------|----------------|-------------|
| **TUI** | Yes | Transport Usage Index: TNP pickups per 1,000 residents (median monthly values in 2024) |
| **SDVI** | Yes | `mean(z(Hardship), z(-income))` |
| **HSVI** | Yes | `mean(z(Hardship), z(CCVI))` — baseline regressor in spatial models |
| **CCVI** | External | Chicago COVID-19 Community Vulnerability Index (descriptive) |
| **Weighted TUI** | Yes | Annual ridesourcing spend per capita / per capita income |
| **Loop travel time** | Yes | Mean ridesourcing travel time to the Loop by pickup CA |
| **TAI / transit deficit** | Yes | Z-score mean of bus stops, rail stations, and GTFS departures per km²; deficit = negative z |

Community Area **76 (O'Hare)** is excluded from analysis (transport-hub outlier).

## `utils.py` overview

- **Ingestion:** `source_tnp_counts`, `source_tnp_fares`, `source_loop_travel_times` (Socrata API, cached under `data/`)
- **Core:** `load_chicago_community_areas`, `load_all_cca_population`, `build_tui_map`, `build_analysis_gdf`
- **Vulnerability:** `load_vulnerability_data`, `build_vulnerability_indices`
- **Burden & access:** `compute_weighted_tui`, `compute_transit_accessibility`, `compute_gtfs_stop_frequency`
- **Spatial:** `compute_moran`, `compute_lisa`, Queen contiguity weights
- **Regression:** `prepare_spatial_regression_data`, `run_spatial_error_model`, `run_spatial_lag_model`, `moran_residuals_spatial_model`
- **Plots:** choropleths, scatterplots, `save_chart`

## Setup

```bash
git clone https://github.com/sforci/SmartCities_Ridesharing.git
cd SmartCities_Ridesharing
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook SmartCities_RideSharing.ipynb
```

### Data notes

- Most inputs are committed under `data/` (TNP counts, hardship, CCVI, boundaries, CMAP population GeoJSON, CTA layers).
- **`data/google_transit/`** (CTA GTFS feed) is gitignored. Download from [CTA GTFS](https://www.transitchicago.com/developers/gtfs/) and extract into `data/google_transit/` before running section 7.
- TNP trip counts can be refreshed from the notebook via `utils.source_tnp_counts` (API).
- Cached outputs: `data/transit_accessibility_index.csv`, `data/tnp_loop_travel_times_2024.csv`, `data/tnp_median_fares_2023_2024.csv`.

## Data sources

- [TNP Trips 2018–2022](https://data.cityofchicago.org/Transportation/Transportation-Network-Providers-Trips-2018-2022-/m6dm-c72p)
- [TNP Trips 2023–2024](https://data.cityofchicago.org/Transportation/Transportation-Network-Providers-Trips-2023-2024-/n26f-ihde) (fares, trip duration)
- [Community Area boundaries](https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Community-Areas-Map/cauq-8yn6)
- [Hardship Index & income](https://data.cityofchicago.org/Health-Human-Services/Selected-socioeconomic-indicators-by-neighborhood/i9hv-en6g)
- [CCVI](https://data.cityofchicago.org/Health-Human-Services/Chicago-COVID-19-Community-Vulnerability-Index-CCV/xhc6-88s9)
- [CMAP Community Data Snapshots](https://datahub.cmap.illinois.gov/search?tags=community%2520data%2520snapshots) (population)
- [CTA bus stops](https://data.cityofchicago.org/Transportation/CTA-Bus-Stops/7jxj-5p9r) · [CTA rail stations](https://data.cityofchicago.org/Transportation/CTA-L-Rail-Stations/8pix-ypme)
- [CTA GTFS](https://www.transitchicago.com/developers/gtfs/)

## Report

LaTeX final essay: `ridesharing_report/DSLSC Project Template/ProjectTemplate.tex` (~20 pages, figures in `figs/`).

```bash
cd "ridesharing_report/DSLSC Project Template"
pdflatex ProjectTemplate.tex && bibtex ProjectTemplate && pdflatex ProjectTemplate.tex && pdflatex ProjectTemplate.tex
```

To refresh figures from the notebook, export from `data/output_charts/` into `ridesharing_report/DSLSC Project Template/figs/`.

## Team

- Silvia Forcina Barrero — [sforci](https://github.com/sforci)
- Francesca Negri — [FrancescaNegriUNiMiB](https://github.com/FrancescaNegriUNiMiB)
