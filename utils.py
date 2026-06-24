# helper functions

import json
import re
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns
from scipy import stats

OHARE_CA = 76

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
