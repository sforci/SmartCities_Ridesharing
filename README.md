# Smart Cities RideSharing — Chicago

Repository per il corso **Data Science Lab on Smart Cities** (Università Milano-Bicocca).

Analisi dell'inequità spaziale tra uso di ridesourcing (Uber/Lyft) e vulnerabilità socio-sanitaria nelle 77 Community Areas di Chicago.

## Research question

Il ridesourcing agisce come equalizzatore della mobilità o come sostituto costoso del trasporto pubblico nelle aree vulnerabili?

## Struttura del progetto

```
SmartCities_Ridesharing/
├── SmartCities_RideSharing.ipynb   # analisi principale
├── utils.py                        # download TNP e caricamento popolazione
├── requirements.txt
├── data/                           # dati locali (geojson, CSV)
└── ridesharing_report/             # report LaTeX (rho-class)
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

## Indicatori

| Indicatore | Descrizione |
|---|---|
| **TUI** | Transport Usage Index: trip TNP per 1.000 residenti |
| **Hardship Index** | Vulnerabilità socioeconomica (Chicago Data Portal) |
| **CCVI** | Chicago COVID-19 Community Vulnerability Index |
| **HSVI** | Indice composito (z-score medio Hardship + CCVI) |

La Community Area 76 (O'Hare) è esclusa dal modeling socioeconomico.

## Data sources

- [TNP Trips 2018–2022](https://data.cityofchicago.org/Transportation/Transportation-Network-Providers-Trips-2018-2022-/m6dm-c72p)
- [TNP Trips 2023–2024](https://data.cityofchicago.org/Transportation/Transportation-Network-Providers-Trips-2023-2024-/n26f-ihde)
- [Community Area boundaries](https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Community-Areas-Map/cauq-8yn6)
- [Hardship Index](https://data.cityofchicago.org/Health-Human-Services/Selected-socioeconomic-indicators-by-neighborhood/i9hv-en6g)
- [CCVI](https://data.cityofchicago.org/Health-Human-Services/Chicago-COVID-19-Community-Vulnerability-Index-CCV/xhc6-88s9)
- CMAP Community Data Snapshots (popolazione per CA)

I dati TNP possono essere riscaricati via API dal notebook (`utils.source_tnp_counts`). I CSV di vulnerabilità sono in `data/`.

## Branch

- `main` — notebook base (TUI)
- `fn-health` — integrazione HSVI, correlazioni, mappe bivariate e report LaTeX

## Report

Vedi [`ridesharing_report/README.md`](ridesharing_report/README.md) per compilare il PDF.

```bash
cd ridesharing_report && make pdf
```

## Team

- Francesca Negri (`fn-health`)
- [sforci](https://github.com/sforci) — repository originale
