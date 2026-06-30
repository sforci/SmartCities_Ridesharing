# helper functions

import json
import re
from calendar import monthrange
from pathlib import Path
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns
from scipy import stats
from libpysal.weights import Queen
from esda.moran import Moran, Moran_Local
from splot.esda import moran_scatterplot
from spreg import ML_Error, ML_Lag


OHARE_CA = 76
LOOP_CA = 32
DEFAULT_AVG_TRIP_COST_USD = 17.5

HARDHIP_RENAME = {
    "Community Area Number": "community_area",
    "ca": "community_area",
    "HARDSHIP INDEX": "hardship_index",
    "hardship_index": "hardship_index",
    "PER CAPITA INCOME ": "per_capita_income",
    "per_capita_income_": "per_capita_income",
}

CCVI_RENAME = {
    "Community Area or ZIP Code": "community_area",
    "community_area_or_zip": "community_area",
    "CCVI Score": "ccvi_score",
    "ccvi_score": "ccvi_score",
    "Geography Type": "geography_type",
    "geography_type": "geography_type",
}


def source_tnp_counts(url, df_name, data_dir="data", force=False):
    '''
    Download or reuse monthly TNP counts by community area.
    Input: API url, output name. Output: CSV path under data/.
    '''
    out_path = Path(data_dir) / f"{df_name}.csv"
    if out_path.exists() and not force:
        print(f"Using cached TNP data: {out_path}")
        return out_path

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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tnp_counts.to_csv(out_path, index=False)
    print(f"Downloaded TNP data: {out_path}")
    return out_path

def source_tnp_fares(url, df_name, data_dir="data", force=False):
    '''
    Download median TNP fares by community area.
    Input: API url, output name. Output: CSV path under data/.
    '''
    out_path = Path(data_dir) / f"{df_name}.csv"
    if out_path.exists() and not force:
        print(f"Using cached TNP data: {out_path}")
        return out_path

    query = """
    SELECT
    date_trunc_y(trip_start_timestamp) AS year,
    pickup_community_area,
    median(trip_total) AS median_fare
    WHERE pickup_community_area IS NOT NULL
    GROUP BY
    date_trunc_y(trip_start_timestamp),
    pickup_community_area
    ORDER BY
    date_trunc_y(trip_start_timestamp),
    pickup_community_area
    """

    response = requests.get(url, params={"$query": query})
    response.raise_for_status()

    tnp_fares = pd.DataFrame(response.json())
    tnp_fares["year"] = pd.to_datetime(tnp_fares["year"])
    tnp_fares["pickup_community_area"] = tnp_fares["pickup_community_area"].astype(int)
    tnp_fares["median_fare"] = tnp_fares["median_fare"].astype(float)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tnp_fares.to_csv(out_path, index=False)
    print(f"Downloaded TNP data: {out_path}")
    return out_path

def source_loop_travel_times(
    url: str,
    df_name: str,
    year: int = 2024,
    dropoff_ca: int = LOOP_CA,
    exclude_pickup_ca: int = OHARE_CA,
    data_dir: str | Path = "data",
    force: bool = False,
) -> Path:
    '''
    Download or reuse mean trip_seconds to Loop by pickup CA (monthly API aggregates).
    Input: API url, cache name, year. Output: CSV with community_area, mean_trip_seconds, n_trips.
    '''
    data_dir = Path(data_dir)
    out_path = data_dir / f"{df_name}.csv"
    monthly_dir = data_dir / f"{df_name}_monthly"
    if out_path.exists() and not force:
        print(f"Using cached loop travel times: {out_path}")
        return out_path

    monthly_dir.mkdir(parents=True, exist_ok=True)
    monthly_frames = []
    for month in range(1, 13):
        month_path = monthly_dir / f"{year}_{month:02d}.csv"
        if month_path.exists() and not force:
            chunk = pd.read_csv(month_path)
            monthly_frames.append(chunk)
            continue

        last_day = monthrange(year, month)[1]
        start = f"{year}-{month:02d}-01T00:00:00"
        end = f"{year}-{month:02d}-{last_day:02d}T23:59:59"
        where = (
            f"dropoff_community_area={dropoff_ca} "
            f"AND pickup_community_area IS NOT NULL "
            f"AND pickup_community_area != {exclude_pickup_ca} "
            f"AND trip_start_timestamp between '{start}' AND '{end}'"
        )
        params = {
            "$select": "pickup_community_area, avg(trip_seconds) as mean_trip_seconds, count(trip_id) as n_trips",
            "$where": where,
            "$group": "pickup_community_area",
        }

        for attempt in range(3):
            try:
                response = requests.get(url, params=params, timeout=180)
                response.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                print(f"  retry {year}-{month:02d} (attempt {attempt + 2}/3)")

        chunk = pd.DataFrame(response.json())
        if chunk.empty:
            print(f"  {year}-{month:02d}: no trips")
            continue
        chunk["month"] = month
        chunk.to_csv(month_path, index=False)
        monthly_frames.append(chunk)
        print(f"  {year}-{month:02d}: {len(chunk)} pickup areas")

    monthly = pd.concat(monthly_frames, ignore_index=True)
    monthly["mean_trip_seconds"] = pd.to_numeric(monthly["mean_trip_seconds"], errors="coerce")
    monthly["n_trips"] = pd.to_numeric(monthly["n_trips"], errors="coerce")
    monthly["pickup_community_area"] = monthly["pickup_community_area"].astype(int)

    weighted = monthly["mean_trip_seconds"] * monthly["n_trips"]
    annual = (
        monthly.assign(weighted_seconds=weighted)
        .groupby("pickup_community_area", as_index=False)
        .agg(mean_trip_seconds=("weighted_seconds", "sum"), n_trips=("n_trips", "sum"))
    )
    annual["mean_trip_seconds"] = annual["mean_trip_seconds"] / annual["n_trips"]
    annual = annual.rename(columns={"pickup_community_area": "community_area"})
    annual.to_csv(out_path, index=False)
    print(f"Downloaded loop travel times: {out_path}")
    return out_path


def compute_loop_travel_times(
    trips_df: pd.DataFrame,
    year: int | None = 2024,
    dropoff_ca: int = LOOP_CA,
    exclude_pickup_ca: int = OHARE_CA,
) -> pd.DataFrame:
    '''
    Mean trip_seconds to Loop by pickup CA from trip-level TNP records.
    Input: trip-level df with pickup/dropoff/seconds. Output: community_area, mean_trip_seconds, n_trips.
    '''
    df = trips_df.copy()
    if year is not None:
        if "year" not in df.columns:
            df["trip_start_timestamp"] = pd.to_datetime(df["trip_start_timestamp"])
            df["year"] = df["trip_start_timestamp"].dt.year
        df = df[df["year"] == year]

    pickup_col = "pickup_community_area" if "pickup_community_area" in df.columns else "community_area"
    dropoff_col = "dropoff_community_area"

    df = df[
        (pd.to_numeric(df[dropoff_col], errors="coerce") == dropoff_ca)
        & (df[pickup_col].notna())
        & (pd.to_numeric(df[pickup_col], errors="coerce") != exclude_pickup_ca)
    ].copy()
    df["trip_seconds"] = pd.to_numeric(df["trip_seconds"], errors="coerce")
    df = df.dropna(subset=["trip_seconds"])

    return (
        df.groupby(pickup_col, as_index=False)
        .agg(mean_trip_seconds=("trip_seconds", "mean"), n_trips=("trip_seconds", "count"))
        .rename(columns={pickup_col: "community_area"})
    )


def build_loop_travel_time_map(
    community_areas: gpd.GeoDataFrame,
    loop_travel_times: pd.DataFrame,
) -> gpd.GeoDataFrame:
    '''
    Merge mean travel times to Loop with community area boundaries.
    Input: boundaries, loop travel table. Output: GeoDataFrame for mapping.
    '''
    return community_areas.merge(loop_travel_times, on="community_area", how="left")


def plot_loop_travel_time_map(map_df, year, ax=None):
    '''
    Choropleth of mean rideshare travel time to the Loop by pickup CA.
    Input: GeoDataFrame with mean_trip_seconds, year. Output: matplotlib axes.
    '''
    if ax is None:
        _, ax = plt.subplots(figsize=(14, 14))

    plot_df = map_df[map_df["community_area"] != OHARE_CA].copy()
    plot_df["mean_trip_minutes"] = plot_df["mean_trip_seconds"] / 60
    plot_df.plot(
        column="mean_trip_minutes",
        cmap="YlOrRd",
        linewidth=0.5,
        edgecolor="black",
        legend=True,
        ax=ax,
        missing_kwds={"color": "lightgrey", "label": "No data"},
    )
    ax.set_title(f"Mean rideshare travel time to the Loop — {year} (minutes)")
    ax.axis("off")
    return ax


def load_cca_population_file(filepath: str | Path, name_to_id: dict | None = None) -> pd.DataFrame:
    '''
    Load population from one CCA geojson file.
    Input: file path, optional name lookup. Output: community_area, population, year.
    '''
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
        columns={"GEOG": "community_area_name", "TOT_POP": "population"}
    )
    population["year"] = year
    population["population"] = pd.to_numeric(population["population"], errors="coerce")
    return population


def load_all_cca_population(population_folder: str | Path) -> pd.DataFrame:
    '''
    Load population from all CCA_*.geojson files in a folder.
    Input: data folder. Output: community_area, year, population.
    '''
    population_folder = Path(population_folder)
    files = sorted(population_folder.glob("CCA_*.geojson"))
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

    return pd.concat(
        [load_cca_population_file(file, name_to_id=name_to_id) for file in files],
        ignore_index=True,
    )


def load_chicago_community_areas(filepath: str | Path) -> gpd.GeoDataFrame:
    '''
    Load Chicago community area boundaries.
    Input: geojson path. Output: GeoDataFrame with community_area and name.
    '''
    gdf = gpd.read_file(filepath)
    gdf = gdf.rename(columns={"area_num_1": "community_area", "community": "community_area_name"})
    gdf["community_area"] = gdf["community_area"].astype(int)
    return gdf


def build_tui_map(
    community_areas: gpd.GeoDataFrame,
    tui: pd.DataFrame,
    year: int,
) -> gpd.GeoDataFrame:
    '''
    Merge boundaries with mean annual TUI for one year.
    Input: boundaries, monthly TUI, year. Output: GeoDataFrame for mapping.
    '''
    tui_year = (
        tui[tui["year"] == year]
        .groupby("community_area", as_index=False)["tui_index"]
        .mean()
    )
    return community_areas.merge(tui_year, on="community_area", how="left")


def load_vulnerability_data(data_dir: str | Path = "data") -> pd.DataFrame:
    '''
    Load hardship, income, CCVI and compute HSVI and SDVI.
    Input: data folder. Output: vulnerability table per community_area.
    '''
    data_dir = Path(data_dir)
    hardship = pd.read_csv(data_dir / "hardship_index.csv").rename(columns=HARDHIP_RENAME)
    ccvi = pd.read_csv(data_dir / "ccvi.csv").rename(columns=CCVI_RENAME)

    hardship["community_area"] = pd.to_numeric(hardship["community_area"], errors="coerce")
    ccvi["community_area"] = pd.to_numeric(ccvi["community_area"], errors="coerce")
    hardship = hardship.dropna(subset=["community_area"]).copy()
    hardship["community_area"] = hardship["community_area"].astype(int)
    ccvi = ccvi.dropna(subset=["community_area"]).copy()
    ccvi["community_area"] = ccvi["community_area"].astype(int)
    hardship["hardship_index"] = pd.to_numeric(hardship["hardship_index"], errors="coerce")
    hardship["per_capita_income"] = pd.to_numeric(hardship["per_capita_income"], errors="coerce")
    ccvi["ccvi_score"] = pd.to_numeric(ccvi["ccvi_score"], errors="coerce")

    if "geography_type" in ccvi.columns:
        ccvi = ccvi[ccvi["geography_type"].str.upper() == "CA"].copy()
    ccvi = ccvi.drop_duplicates(subset="community_area", keep="first")

    vulnerability = hardship[["community_area", "hardship_index", "per_capita_income"]].merge(
        ccvi[["community_area", "ccvi_score"]],
        on="community_area",
        how="outer",
    )

    vulnerability["income_vuln"] = -vulnerability["per_capita_income"]
    for col in ["hardship_index", "income_vuln", "ccvi_score"]:
        vulnerability[f"{col}_z"] = (vulnerability[col] - vulnerability[col].mean()) / vulnerability[col].std()
    vulnerability["hsvi"] = vulnerability[["hardship_index_z", "ccvi_score_z"]].mean(axis=1)
    vulnerability["sdvi"] = vulnerability[["hardship_index_z", "income_vuln_z"]].mean(axis=1)
    return vulnerability


def build_analysis_gdf(
    tui_map: gpd.GeoDataFrame,
    vulnerability: pd.DataFrame,
    exclude_ca: int = OHARE_CA,
) -> gpd.GeoDataFrame:
    '''
    Merge TUI and vulnerability; drop O'Hare and incomplete rows.
    Input: TUI map, vulnerability table. Output: analysis GeoDataFrame.
    '''
    gdf = tui_map.merge(vulnerability, on="community_area", how="left")
    gdf = gdf[gdf["community_area"] != exclude_ca].copy()
    return gdf.dropna(subset=["tui_index", "hsvi", "sdvi"])


def compute_tui_correlations(
    gdf: pd.DataFrame,
    tui_col: str = "tui_index",
    vuln_cols: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    '''
    Compute Pearson, Spearman and pairwise tests for TUI vs vulnerability cols.
    Input: analysis GeoDataFrame. Output: correlation matrices and test table.
    '''
    if vuln_cols is None:
        vuln_cols = ["hsvi", "sdvi", "ccvi_score"]

    cols = [tui_col, *vuln_cols]
    pearson = gdf[cols].corr(method="pearson")
    spearman = gdf[cols].corr(method="spearman")

    labels = {"hsvi": "HSVI", "sdvi": "SDVI", "ccvi_score": "CCVI"}
    tests = []
    for col in vuln_cols:
        r_p, p_p = stats.pearsonr(gdf[tui_col], gdf[col])
        r_s, p_s = stats.spearmanr(gdf[tui_col], gdf[col])
        tests.append({
            "indicator": labels.get(col, col),
            "pearson_r": r_p,
            "pearson_p": p_p,
            "spearman_rho": r_s,
            "spearman_p": p_s,
        })

    return pearson, spearman, pd.DataFrame(tests)


def compute_weighted_tui(
    trips_df: pd.DataFrame,
    vulnerability: pd.DataFrame,
    median_trip_cost_usd: pd.DataFrame,
    year: int = 2024,
    income_col: str = "per_capita_income",
    exclude_ca: int = OHARE_CA,
) -> pd.DataFrame:
    '''
    Financial Burden Index from annual TNP spend per capita relative to area income.
    Input: monthly trips df, vulnerability table, year, mean trip cost (USD).
    Output: community_area, total_spend, rideshare_spend_pc, Weighted_TUI.
    '''
    year_df = trips_df[trips_df["year"] == year]
    
    median_trip_cost_usd = pd.read_csv(median_trip_cost_usd)
    median_trip_cost_usd["year"] = pd.to_datetime(median_trip_cost_usd["year"]).dt.year
    median_trip_cost_usd = median_trip_cost_usd[median_trip_cost_usd["year"] == year]
    median_trip_cost_usd["community_area"] = median_trip_cost_usd["pickup_community_area"].astype(int)
    median_trip_cost_usd = median_trip_cost_usd[median_trip_cost_usd["community_area"] != 76
]
    annual = (
        year_df.groupby("community_area", as_index=False)
        .agg(n_trips=("n_trips", "sum"), population=("population", "mean"))
    )
    annual = annual.merge(median_trip_cost_usd, how="left", on="community_area")
    annual["total_spend"] = annual["n_trips"] * annual["median_fare"]
    annual["rideshare_spend_pc"] = annual["total_spend"] / annual["population"]

    out = annual.merge(
        vulnerability[["community_area", income_col]],
        on="community_area",
        how="left",
    )
    out = out[out["community_area"] != exclude_ca].copy()
    out["Weighted_TUI"] = out["rideshare_spend_pc"] / out[income_col]
    return out


def build_weighted_tui_map(
    community_areas: gpd.GeoDataFrame,
    weighted_tui: pd.DataFrame,
) -> gpd.GeoDataFrame:
    '''
    Merge Weighted_TUI with community area boundaries.
    Input: boundaries, weighted tui table. Output: GeoDataFrame for mapping.
    '''
    return community_areas.merge(weighted_tui, on="community_area", how="left")


def plot_weighted_tui_map(map_df, year, ax=None):
    '''
    Choropleth of Weighted_TUI (financial burden) by community area.
    Input: GeoDataFrame with Weighted_TUI, year. Output: matplotlib axes.
    '''
    if ax is None:
        _, ax = plt.subplots(figsize=(14, 14))

    plot_df = map_df[map_df["community_area"] != OHARE_CA].copy()
    plot_df.plot(
        column="Weighted_TUI",
        cmap="YlOrRd",
        linewidth=0.5,
        edgecolor="black",
        legend=True,
        ax=ax,
        missing_kwds={"color": "lightgrey", "label": "No data"},
    )
    ax.set_title(f"Weighted TUI — Financial Burden Index ({year})")
    ax.axis("off")
    return ax


def save_chart(chart, filename, output_dir="data/output_charts"):
    '''
    Save a matplotlib chart as PNG under data/output_charts.
    Input: figure or axes, output filename. Output: saved file path.
    '''
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fig = chart if hasattr(chart, "savefig") else chart.get_figure()
    name = filename if filename.endswith(".png") else f"{filename}.png"
    out_path = output_dir / name
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    return out_path


def plot_tui_index(map_df, year, add_labels=True, ax=None):
    '''
    Choropleth of TUI by community area.
    Input: GeoDataFrame with tui_index, year. Output: matplotlib axes.
    '''
    if ax is None:
        _, ax = plt.subplots(figsize=(14, 14))

    map_df.plot(
        column="tui_index",
        cmap="RdYlGn_r",
        linewidth=0.5,
        edgecolor="black",
        legend=True,
        ax=ax,
        missing_kwds={"color": "lightgrey", "label": "No data"},
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
                va="center",
            )

    ax.set_title(f"TUI Index by Community Area — {year}")
    ax.axis("off")
    return ax


def plot_tui_vulnerability_scatter(gdf, x="sdvi", y="tui_index", year=2024, ax=None):
    '''
    Scatter of TUI vs vulnerability index with linear fit.
    Input: analysis GeoDataFrame, x column. Output: matplotlib axes.
    '''
    scatter_labels = {
        "ccvi_score": ("CCVI", "TUI vs CCVI"),
        "hsvi": ("HSVI (z Hardship + CCVI)", "TUI vs HSVI"),
        "sdvi": ("SDVI (z Hardship + income)", "TUI vs SDVI"),
    }
    xlabel, title = scatter_labels.get(x, (x, f"TUI vs {x}"))

    if ax is None:
        _, ax = plt.subplots(figsize=(7, 5))

    sns.regplot(
        data=gdf,
        x=x,
        y=y,
        scatter_kws={"alpha": 0.7, "s": 50},
        line_kws={"color": "crimson"},
        ax=ax,
    )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(f"TUI (trips per 1,000 residents, {year})")
    ax.set_title(title)
    return ax


def plot_tui_vulnerability_maps(gdf, year=2024):
    '''
    Side-by-side choropleth maps of TUI and SDVI.
    Input: analysis GeoDataFrame, year. Output: matplotlib figure.
    '''
    fig, axes = plt.subplots(1, 2, figsize=(18, 9))
    plot_kw = dict(
        linewidth=0.5,
        edgecolor="black",
        legend=True,
        missing_kwds={"color": "lightgrey", "label": "No data"},
    )

    gdf.plot(column="tui_index", cmap="RdYlGn_r", ax=axes[0], **plot_kw)
    axes[0].set_title(f"TUI ({year})")
    axes[0].axis("off")

    gdf.plot(column="sdvi", cmap="YlOrRd", ax=axes[1], **plot_kw)
    axes[1].set_title("SDVI")
    axes[1].axis("off")

    plt.suptitle("TUI vs socio-demographic vulnerability (excl. O'Hare)", fontsize=13, y=1.02)
    plt.tight_layout()
    return fig

def compute_moran(gdf, tui_col="tui_index"):
    '''
    Compute Moran's I for TUI index.
    Input: analysis GeoDataFrame, TUI column. Output: Moran object.
    '''

    gdf = gdf.dropna(subset=[tui_col]).copy()
    w = Queen.from_dataframe(gdf, use_index=False)
    w.transform = "r"
    y = gdf[tui_col].values
    moran = Moran(y, w, permutations=999)
    
    print("Moran's I:", moran.I)
    print("p-value:", moran.p_sim)
    return moran


def plot_moran_scatterplot(moran):
    ''' 
    Plot Moran scatterplot for TUI index.  
    '''
    fig, ax = moran_scatterplot(moran)
    ax.set_title("Moran scatterplot: TUI")
    plt.show()

def compute_lisa(gdf, tui_col="tui_index"):
    '''
    Compute Local Indicators of Spatial Association (LISA) for TUI index.
    Input: analysis GeoDataFrame, TUI column. Output: Moran_Local object.
    '''
    gdf = gdf.dropna(subset=[tui_col]).copy()
    w = Queen.from_dataframe(gdf, use_index=False)
    w.transform = "r"
    y = gdf[tui_col].values
    lisa = Moran_Local(y, w, permutations=999)

    gdf["lisa_q"] = lisa.q
    gdf["lisa_p"] = lisa.p_sim

    gdf["lisa_cluster"] = "Not significant"
    gdf.loc[(gdf["lisa_p"] < 0.05) & (gdf["lisa_q"] == 1), "lisa_cluster"] = "High-High"
    gdf.loc[(gdf["lisa_p"] < 0.05) & (gdf["lisa_q"] == 2), "lisa_cluster"] = "Low-High"
    gdf.loc[(gdf["lisa_p"] < 0.05) & (gdf["lisa_q"] == 3), "lisa_cluster"] = "Low-Low"
    gdf.loc[(gdf["lisa_p"] < 0.05) & (gdf["lisa_q"] == 4), "lisa_cluster"] = "High-Low"
    
    print("LISA computed.")
    return lisa, gdf

def plot_lisa_map(gdf, year, ax=None):
    '''
    Choropleth of LISA clusters for TUI index.
    Input: analysis GeoDataFrame with lisa_cluster, year. Output: matplotlib axes.
    '''
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))

    gdf.plot(
        column="lisa_cluster",
        categorical=True,
        linewidth=0.5,
        edgecolor="black",
        legend=True,
        ax=ax,
        missing_kwds={"color": "lightgrey", "label": "No data"},
    )
    ax.set_title(f"LISA Clusters for TUI Index — {year}")
    ax.axis("off")
    plt.show()

def zscore(x):
    return (x - x.mean()) / x.std()


def load_transit_points(path):
    gdf = gpd.read_file(path)

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    return gdf


def count_points_in_areas(points_gdf, community_areas, count_col):
    points = points_gdf.to_crs(community_areas.crs)

    joined = gpd.sjoin(
        points,
        community_areas[["community_area", "geometry"]],
        how="inner",
        predicate="intersects"
    )

    counts = (
        joined
        .groupby("community_area")
        .size()
        .reset_index(name=count_col)
    )

    return counts


def compute_transit_accessibility(
    community_areas,
    bus_path,
    rail_path
):
    ca = community_areas.copy()

    # project to meters to calculate area correctly
    ca = ca.to_crs("EPSG:26916")
    ca["area_km2"] = ca.geometry.area / 1_000_000

    bus = load_transit_points(bus_path)
    rail = load_transit_points(rail_path)

    bus_counts = count_points_in_areas(bus, ca, "n_bus_stops")
    rail_counts = count_points_in_areas(rail, ca, "n_rail_stations")

    transit = (
        ca[["community_area", "community_area_name", "area_km2", "geometry"]]
        .merge(bus_counts, on="community_area", how="left")
        .merge(rail_counts, on="community_area", how="left")
    )
    transit = transit[transit["community_area"] != 76].copy()

    transit["n_bus_stops"] = transit["n_bus_stops"].fillna(0)
    transit["n_rail_stations"] = transit["n_rail_stations"].fillna(0)

    transit["bus_stops_per_km2"] = transit["n_bus_stops"] / transit["area_km2"]
    transit["rail_stations_per_km2"] = transit["n_rail_stations"] / transit["area_km2"]

    transit["bus_access_z"] = zscore(transit["bus_stops_per_km2"])
    transit["rail_access_z"] = zscore(transit["rail_stations_per_km2"])

    transit["transit_access"] = transit[["bus_access_z", "rail_access_z"]].mean(axis=1)
    transit["transit_access_z"] = zscore(transit["transit_access"])
    transit["transit_deficit"] = -transit["transit_access_z"]

    return transit


def plot_transit_deficit(transit_gdf):
    fig, ax = plt.subplots(figsize=(12, 12))

    transit_gdf.plot(
        column="transit_deficit",
        cmap="RdYlGn_r",
        linewidth=0.5,
        edgecolor="black",
        legend=True,
        ax=ax
    )

    ax.set_title("Transit Deficit Index by Community Area")
    ax.axis("off")

    plt.show()

def prepare_spatial_regression_data(gdf, y_col, x_cols):
    df = gdf.dropna(subset=[y_col, *x_cols]).copy()

    # standardize X variables for easier comparison
    for col in x_cols:
        df[f"{col}_z"] = (df[col] - df[col].mean()) / df[col].std()

    y = df[[y_col]].values
    X = df[[f"{col}_z" for col in x_cols]].values

    w = Queen.from_dataframe(df, use_index=False)
    w.transform = "r"

    return df, y, X, w, [f"{col}_z" for col in x_cols]


def run_spatial_error_model(gdf, y_col, x_cols):
    df, y, X, w, x_names = prepare_spatial_regression_data(gdf, y_col, x_cols)

    model = ML_Error(
        y=y,
        x=X,
        w=w,
        name_y=y_col,
        name_x=x_names,
        name_w="queen",
        name_ds="analysis_gdf"
    )

    return model, df, w


def run_spatial_lag_model(gdf, y_col, x_cols):
    df, y, X, w, x_names = prepare_spatial_regression_data(gdf, y_col, x_cols)

    model = ML_Lag(
        y=y,
        x=X,
        w=w,
        name_y=y_col,
        name_x=x_names,
        name_w="queen",
        name_ds="analysis_gdf"
    )

    return model, df, w


def moran_residuals_spatial_model(model, w, filtered=False):
    if filtered:
        residuals = model.e_filtered.flatten()
    else:
        residuals = model.u.flatten()
    moran = Moran(residuals, w, permutations=999)

    print("Moran's I residuals:", moran.I)
    print("p-value:", moran.p_sim)

    return moran