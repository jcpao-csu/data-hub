# maps/rcvd_def_zipcode.py
# Choropleth map of unique defendant home ZIP codes within Jackson County, MO.
# Uses the 29095_zipcodes shapefile; defendants with addresses outside the county
# are excluded from the map and reported separately as a metric.

import branca.colormap as cm
import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_folium import st_folium

_SHP_PATH = "assets/shp/29095_zipcodes/Jackson Zipcodes.shp"
# _COUNTY_SHP_PATH = "assets/shp/tl_2025_us_county/tl_2025_us_county.shp"
_COUNTY_SHP_PATH = "assets/shp/jackson_county_boundary/jackson_county_ONLY.shp"
_DEMARCATIONS_PATH = "assets/shp/jcpao_street_demarcations/jcpao_street_demarcations.shp"
_CENTER = [+39.0053640, -094.3432105]
_ZOOM = 10

# Light → dark blue scale, readable on CartoDB Positron (light basemap)
_COLOR_STEPS = ["#e4f3ff", "#60aeff", "#1a6fba", "#0a3d6e"]


@st.cache_data
def _load_geodata() -> tuple[set, gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Load and cache shapefiles. Returns (set of valid ZIPs, ZIP GeoDataFrame, Jackson County boundary, street demarcations)."""
    gdf = gpd.read_file(_SHP_PATH).to_crs(epsg=4326)
    jc_zips = set(gdf["ZCTA5CE20"].astype(str))

    jc_boundary = gpd.read_file(_COUNTY_SHP_PATH).to_crs(epsg=4326)
    # jc_boundary = counties[
    #     (counties["STATEFP"] == "29") & (counties["COUNTYFP"] == "095")
    # ][["geometry"]].copy()

    demarcations = gpd.read_file(_DEMARCATIONS_PATH).to_crs(epsg=4326)

    return jc_zips, gdf[["ZCTA5CE20", "geometry"]].copy(), jc_boundary, demarcations


def _prepare_def_zipcode(
    rcvd: pd.DataFrame,
    jc_zips: set,
) -> tuple[pd.DataFrame, int, int, int]:
    """
    Count unique defendants (by pbk_def_num) per ZIP code.
    ZIPs outside Jackson County are aggregated into a single outside count.
    Returns (in-county DataFrame with all JC ZIPs, outside_count, missing_count).
    """
    all_defs = (
        rcvd[["pbk_def_num", "def_zipcode"]]
        .drop_duplicates("pbk_def_num")
        .copy()
    )
    total_unique_defs = all_defs["pbk_def_num"].nunique()
    missing_count = int(all_defs["def_zipcode"].isna().sum())

    df = all_defs.dropna(subset=["def_zipcode"]).copy()
    df["def_zipcode"] = df["def_zipcode"].astype(str).str.strip().str[:5].str.zfill(5)

    in_county_mask = df["def_zipcode"].isin(jc_zips)
    outside_count = int((~in_county_mask).sum())

    counts = (
        df[in_county_mask]
        .groupby("def_zipcode")["pbk_def_num"]
        .nunique()
        .reset_index(name="defendant_count")
        .rename(columns={"def_zipcode": "ZCTA5CE20"})
    )

    # Ensure every JC ZIP appears (zeros for ZIPs with no defendants in the selection)
    full = pd.DataFrame({"ZCTA5CE20": sorted(jc_zips)})
    counts = full.merge(counts, on="ZCTA5CE20", how="left")
    counts["defendant_count"] = counts["defendant_count"].fillna(0).astype(int)
    return counts, outside_count, total_unique_defs, missing_count


def _prepare_def_zipcode_table(
    rcvd: pd.DataFrame,
    jc_zips: set,
) -> pd.DataFrame:
    """
    Build the full ZIP code summary table — all ZIPs found in the data,
    labeled Inside/Outside Jackson County, with defendant count and share.
    """
    df = (
        rcvd[["pbk_def_num", "def_zipcode"]]
        .dropna(subset=["pbk_def_num", "def_zipcode"])
        .drop_duplicates("pbk_def_num")
        .copy()
    )
    df["def_zipcode"] = df["def_zipcode"].astype(str).str.strip().str[:5].str.zfill(5)

    df["zip_label"] = df["def_zipcode"].where(df["def_zipcode"].isin(jc_zips), "Outside Jackson County")

    counts = (
        df.groupby("zip_label")["pbk_def_num"]
        .nunique()
        .reset_index(name="Defendants")
        .rename(columns={"zip_label": "ZIP Code"})
    )

    total = counts["Defendants"].sum()
    counts["% of Total"] = (counts["Defendants"] / total * 100).round(1) if total else 0.0

    # Sort: JC zips numerically first, Outside Jackson County last
    is_outside = counts["ZIP Code"] == "Outside Jackson County"
    return pd.concat([
        counts[~is_outside].sort_values("Defendants", ascending=False),
        counts[is_outside],
    ]).reset_index(drop=True)


def _build_def_zipcode_map(
    counts: pd.DataFrame,
    gdf: gpd.GeoDataFrame,
    jc_boundary: gpd.GeoDataFrame,
    demarcations: gpd.GeoDataFrame,
) -> folium.Map:
    merged = gdf.merge(counts, on="ZCTA5CE20", how="left")
    merged["defendant_count"] = merged["defendant_count"].fillna(0).astype(int)

    max_count = merged["defendant_count"].max() or 1
    colormap = cm.LinearColormap(
        colors=_COLOR_STEPS,
        vmin=0,
        vmax=max_count,
        caption="Unique Defendants",
    )

    m = folium.Map(
        location=_CENTER,
        zoom_start=_ZOOM,
        tiles="CartoDB positron",
        prefer_canvas=True,
    )

    folium.GeoJson(
        jc_boundary,
        name="Jackson County Boundary",
        style_function=lambda _: {
            "fillColor": "none",
            "color": "#1a6fba",
            "weight": 2.5,
            "dashArray": "6 4",
        },
    ).add_to(m)

    folium.GeoJson(
        merged,
        name="Defendants by ZIP",
        style_function=lambda feature: {
            "fillColor": colormap(feature["properties"]["defendant_count"]),
            "color": "#6b7a99",
            "weight": 0.8,
            "fillOpacity": 0.6,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["ZCTA5CE20", "defendant_count"],
            aliases=["ZIP Code", "Defendants"],
            localize=True,
            sticky=True,
            style=(
                "background-color: #1b2e45;"
                "color: #e8edf2;"
                "border: 1px solid #2a3f5f;"
                "border-radius: 4px;"
                "font-family: Inter, sans-serif;"
                "font-size: 13px;"
            ),
        ),
    ).add_to(m)

    if not demarcations.empty:
        folium.GeoJson(
            demarcations,
            name="Street Demarcations",
            show=True,
            style_function=lambda _: {
                "color": "#e05c5c",
                "weight": 2.0,
                "opacity": 0.6,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["label"],
                aliases=["Street"],
                localize=True,
                sticky=True,
                style=(
                    "background-color: #1b2e45;"
                    "color: #e8edf2;"
                    "border: 1px solid #2a3f5f;"
                    "border-radius: 4px;"
                    "font-family: Inter, sans-serif;"
                    "font-size: 13px;"
                ),
            ),
        ).add_to(m)

    colormap.add_to(m)
    return m


def _render_def_zipcode_metrics(counts: pd.DataFrame, outside_count: int) -> None:
    """Render the four defendant ZIP code summary metric cards."""
    in_county_total = int(counts["defendant_count"].sum())
    total = in_county_total + outside_count

    top_zip_row = counts.loc[counts["defendant_count"].idxmax()] if in_county_total > 0 else None
    top_zip = top_zip_row["ZCTA5CE20"] if top_zip_row is not None else "—"
    top_zip_count = int(top_zip_row["defendant_count"]) if top_zip_row is not None else 0

    st.markdown(
        "<style>[data-testid='stMetricDelta'] svg { display: none; }</style>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    start, end = st.session_state["date_range_filter"]
    with c1:
        st.metric(
            label="**Total Unique Defendants**",
            value=f"{total:,}",
            delta=f"From {pd.Timestamp(str(start)).strftime('%-m/%-d/%Y')} – {pd.Timestamp(str(end)).strftime('%-m/%-d/%Y')}",
            delta_color="off",
            # height=120,
            # width=300,
        )
    with c2:
        st.metric(
            label="**Inside/Bordering Jackson County**",
            value=f"{in_county_total:,}",
            delta=f"{in_county_total / total * 100:.1f}% of total" if total else "—",
            delta_color="off",
            # height=120,
            # width=300,
        )
    with c3:
        st.metric(
            label="**Outside Jackson County**",
            value=f"{outside_count:,}",
            delta=f"{outside_count / total * 100:.1f}% of total" if total else "—",
            delta_color="off",
            # height=120,
            # width=300,
        )
    with c4:
        st.metric(
            label="**Top ZIP Code**",
            value=top_zip,
            delta=f"{top_zip_count:,} defendants | {top_zip_count / total * 100:.1f}% of total" if total else "—",
            delta_color="off",
            # height=120,
            # width=300,
        )


    style_metric_cards(
        background_color="#0d1b2a",
        border_left_color="#4da6ff",
    )


def render_def_zipcode(rcvd: pd.DataFrame) -> None:
    """Render the defendant home ZIP code choropleth map."""
    jc_zips, gdf, jc_boundary, demarcations = _load_geodata()
    counts, outside_count, total_unique_defs, missing_count = _prepare_def_zipcode(rcvd, jc_zips)
    table = _prepare_def_zipcode_table(rcvd, jc_zips)

    with st.container(border=False):
        st.header(":material/map: Referred Defendants by ZIP Code")
        st.caption(
            f"Maps all unique defendants *(n={total_unique_defs:,})* referred to the JCPAO by their last known address (ZIP code). "
            "Defendants with addresses outside Jackson County are excluded from the map. "
            f"Defendants *(n={missing_count:,})* with missing or unknown addresses are also excluded from the map. "
            "Jackson County boundary demarcated in **:blue[blue]**. Troost Ave, Prospect Ave, and Independence Ave demarcated in **:red[red]**. "
            f"Data from {pd.Timestamp(str(st.session_state['date_range_filter'][0])).strftime('%-m/%-d/%Y')} to {pd.Timestamp(str(st.session_state['date_range_filter'][1])).strftime('%-m/%-d/%Y')}. "
        )

        _render_def_zipcode_metrics(counts, outside_count)

        col_map, col_table = st.columns([3, 1.2])
        with col_map:
            st_folium(
                _build_def_zipcode_map(counts, gdf, jc_boundary, demarcations),
                width="stretch",
                height=520,
                returned_objects=[],
            )
        with col_table:
            st.dataframe(
                table,
                # width="stretch",
                height=520,
                hide_index=True,
                column_config={
                    "ZIP Code":     st.column_config.TextColumn("ZIP Code"),
                    "Defendants": st.column_config.NumberColumn("Defendants", format="%d"),
                    "% of Total": st.column_config.NumberColumn("% of Total", format="%.1f%%"),
                },
            )
