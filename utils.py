# helper functions

import pandas as pd
import requests
import os
from pathlib import Path
import re
import json
import matplotlib.pyplot as plt


def source_tnp_counts(url, df_name):
    query = """
    SELECT
    date_trunc_ym(trip_start_timestamp) AS month,
    pickup_community_area,
    count(trip_id) AS n_trips
    WHERE pickup_community_area IS NOT NULL
    GROUP BY
    date_trunc_ym(trip_start_timestamp),
    pickup_community_area
    ORDER BY
    date_trunc_ym(trip_start_timestamp),
    pickup_community_area
    """

    response = requests.get(url, params={"$query": query})
    response.raise_for_status()

    tnp_counts = pd.DataFrame(response.json())

    tnp_counts["month"] = pd.to_datetime(tnp_counts["month"])
    tnp_counts["pickup_community_area"] = tnp_counts["pickup_community_area"].astype(int)
    tnp_counts["n_trips"] = tnp_counts["n_trips"].astype(int)

    tnp_counts.to_csv(os.path.join("data", f"{df_name}.csv"), index=False)
    

def load_cca_population_file(filepath: str | Path, name_to_id: dict | None = None) -> pd.DataFrame:
    filepath = Path(filepath)

    year = int(re.search(r"(\d{4})", filepath.stem).group(1))

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = [feature["properties"] for feature in data["features"]]
    df = pd.DataFrame(records)

    if "GEOID" in df.columns:
        df["community_area"] = df["GEOID"].astype(int)
    else:
        df["community_area"] = df["GEOG"].map(name_to_id).astype(int)

    population = df[["community_area", "GEOG", "TOT_POP"]].rename(
        columns={
            "GEOG": "community_area_name",
            "TOT_POP": "population"
        }
    )

    population["year"] = year
    population["population"] = pd.to_numeric(population["population"], errors="coerce")

    return population


def load_all_cca_population(population_folder: str | Path) -> pd.DataFrame:
    population_folder = Path(population_folder)
    files = sorted(population_folder.glob("CCA_*.geojson"))

    # Build name -> Community Area ID lookup from files that have GEOID
    ref_records = []

    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = [feature["properties"] for feature in data["features"]]
        df = pd.DataFrame(records)

        if "GEOID" in df.columns:
            ref_records.append(df[["GEOG", "GEOID"]])

    ref = pd.concat(ref_records, ignore_index=True).drop_duplicates()
    name_to_id = dict(zip(ref["GEOG"], ref["GEOID"].astype(int)))

    population = pd.concat(
        [load_cca_population_file(file, name_to_id=name_to_id) for file in files],
        ignore_index=True
    )

    return population

def plot_tui_index(map_df, year, add_labels=True):
    fig, ax = plt.subplots(figsize=(14, 14))

    map_df.plot(
        column="tui_index",
        cmap="RdYlGn_r",   # low = green, high = red
        linewidth=0.5,
    edgecolor="black",
    legend=True,
    ax=ax,
    missing_kwds={"color": "lightgrey", "label": "No data"}
    )
    
    if add_labels:
        label_points = map_df.copy()
        label_points["label_point"] = label_points.geometry.representative_point()

        for _, row in label_points.iterrows():
            ax.text(
                row["label_point"].x,
                row["label_point"].y,
                row["community_area_name"].title(),
                fontsize=5,
                ha="center",
                va="center"
            )


    ax.set_title(f"TUI Index by Community Area — {year}")
    ax.axis("off")

    plt.show()