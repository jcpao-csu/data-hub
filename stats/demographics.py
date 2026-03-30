# stats/demographics.py
# Defendant demographics — racial composition and case processing disparity analysis.
#
# Charts:
#   - render_demo_composition   : racial composition of cases received (horizontal bar)
#   - render_demo_filing_rate   : filing rate by race vs. overall average (bar + rule)
#   - render_demo_disp_outcomes : disposition outcome mix by race (normalized stacked bar)
#   - render_demo_vs_census     : defendant race % vs. county population % (grouped bar + disparity index)
#   - render_county_composition : Jackson County racial composition donut by ACS year

import altair as alt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


_RACE_LABELS: dict[str, str] = {
    "W": "White",
    "B": "Black",
    "H": "Hispanic",
    "A": "Asian",
    "I": "Am. Indian",
    "M": "Multiracial",
    "P": "Pacific Islander",
    "U": "Unknown",
}

_COMP_COLOR   = "#4da6ff"
_FILING_COLOR = "#4da6ff"
_AVG_COLOR    = "#f28e2b"


# --- render_demo_composition ---

def _prepare_demo_composition(rcvd: pd.DataFrame) -> pd.DataFrame:
    df = rcvd.copy()
    df["race_label"] = df["def_race"].map(_RACE_LABELS).fillna("Unknown")

    counts = (
        df.groupby("race_label")["pbk_num"]
        .nunique()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total * 100).round(1) if total else 0.0
    return counts


def _build_demo_composition_bar(df: pd.DataFrame) -> alt.Chart:
    sort_order = df["race_label"].tolist()
    return (
        alt.Chart(df)
        .mark_bar(color=_COMP_COLOR)
        .encode(
            x=alt.X("count:Q", title="Cases Received"),
            y=alt.Y("race_label:N", title=None, sort=sort_order),
            tooltip=[
                alt.Tooltip("race_label:N", title="Race"),
                alt.Tooltip("count:Q",      title="Cases Received", format=","),
                alt.Tooltip("pct:Q",        title="% of Total",     format=".1f"),
            ],
        )
        .properties(width="container")
    )


def render_demo_composition(rcvd: pd.DataFrame) -> None:
    """Render racial composition of received cases."""
    df = _prepare_demo_composition(rcvd)

    with st.container(border=True):
        st.header(":material/groups: Racial Composition — Cases Received")
        st.caption(
            "Count of cases received by defendant race within the selected date range. "
            "This provides the baseline denominator for interpreting the rate charts below. "
            "Note: without population-level comparison data, raw counts alone do not indicate "
            "disparity — use the filing rate and disposition charts for that analysis."
        )
        st.altair_chart(_build_demo_composition_bar(df), use_container_width=True)


# --- render_demo_filing_rate ---

def _prepare_demo_filing_rate(
    fld: pd.DataFrame,
    ntfld: pd.DataFrame,
) -> tuple[pd.DataFrame, float]:
    """
    Filing rate by race: filed / (filed + not filed), excluding PFI from the denominator.
    Returns (per-race DataFrame, overall filing rate).
    """
    filed_by_race = (
        fld.groupby("def_race")["pbk_num"]
        .nunique()
        .rename("filed")
    )
    ntfld_decisions = ntfld.loc[ntfld["min_ntfld_rank"] != 3]
    ntfld_by_race = (
        ntfld_decisions.groupby("def_race")["pbk_num"]
        .nunique()
        .rename("not_filed")
    )

    df = (
        filed_by_race.to_frame()
        .join(ntfld_by_race, how="outer")
        .fillna(0)
        .reset_index()
    )
    df["total_reviewed"] = df["filed"] + df["not_filed"]
    df["filing_rate"] = (
        (df["filed"] / df["total_reviewed"])
        .where(df["total_reviewed"] > 0, other=0.0)
        .round(3)
    )
    df["race_label"] = df["def_race"].map(_RACE_LABELS).fillna("Unknown")
    df = df.sort_values("filing_rate", ascending=True).reset_index(drop=True)

    total_filed    = df["filed"].sum()
    total_reviewed = df["total_reviewed"].sum()
    overall_rate   = round(total_filed / total_reviewed, 3) if total_reviewed > 0 else 0.0
    return df, overall_rate


def _build_demo_filing_rate_bar(df: pd.DataFrame, overall_rate: float) -> alt.Chart:
    sort_order = df["race_label"].tolist()

    bars = (
        alt.Chart(df)
        .mark_bar(color=_FILING_COLOR)
        .encode(
            x=alt.X(
                "filing_rate:Q",
                title="Filing Rate",
                axis=alt.Axis(format=".0%"),
                scale=alt.Scale(domain=[0, 1]),
            ),
            y=alt.Y("race_label:N", title=None, sort=sort_order),
            tooltip=[
                alt.Tooltip("race_label:N",     title="Race"),
                alt.Tooltip("filed:Q",          title="Cases Filed",      format=","),
                alt.Tooltip("not_filed:Q",      title="Cases Not Filed",  format=","),
                alt.Tooltip("total_reviewed:Q", title="Total Reviewed",   format=","),
                alt.Tooltip("filing_rate:Q",    title="Filing Rate",      format=".1%"),
            ],
        )
    )

    avg_df = pd.DataFrame({"rate": [overall_rate]})
    rule = (
        alt.Chart(avg_df)
        .mark_rule(color=_AVG_COLOR, strokeDash=[5, 4], strokeWidth=2)
        .encode(x=alt.X("rate:Q"))
    )
    label = (
        alt.Chart(avg_df)
        .mark_text(color=_AVG_COLOR, align="left", dx=5, dy=-8, fontSize=12)
        .encode(
            x=alt.X("rate:Q"),
            y=alt.value(0),
            text=alt.value(f"Overall avg: {overall_rate:.1%}"),
        )
    )

    return (bars + rule + label).properties(width="container")


def render_demo_filing_rate(fld: pd.DataFrame, ntfld: pd.DataFrame) -> None:
    """Render filing rate by race with overall average reference line."""
    df, overall_rate = _prepare_demo_filing_rate(fld, ntfld)

    with st.container(border=True):
        st.header(":material/percent: Filing Rate by Race")
        st.caption(
            "Filing rate per racial group — cases filed divided by total cases with a "
            "charging decision (filed + not filed, excluding PFI / Pending Further "
            "Investigation). The dashed line marks the overall average filing rate. "
            "Races with fewer cases may show more volatile rates."
        )
        st.altair_chart(_build_demo_filing_rate_bar(df, overall_rate), use_container_width=True)


# --- render_demo_disp_outcomes ---

_RANK_TO_CATEGORY: dict[float, str] = {
    1:   "Conviction",
    2:   "Conviction",
    3:   "Conviction",
    4:   "Resolved Nolle",
    5:   "Resolved Nolle",
    6:   "Pending Nolle",
    7:   "Pending Nolle",
    7.5: "Acquittal",
    8:   "Unresolved Nolle",
    9:   "Unresolved Nolle",
    10:  "Unresolved Nolle",
    11:  "Unresolved Nolle",
}

_OUTCOME_ORDER  = ["Conviction", "Resolved Nolle", "Pending Nolle", "Acquittal", "Unresolved Nolle"]
_OUTCOME_COLORS = ["#3db87a",    "#4da6ff",         "#e8a838",       "#e05c5c",   "#c0392b"]


def _prepare_demo_disp_outcomes(disp: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    df = disp.copy()
    df["category"]   = df["min_disp_rank"].map(_RANK_TO_CATEGORY).fillna("Unknown")
    df["race_label"] = df["def_race"].map(_RACE_LABELS).fillna("Unknown")

    counts = (
        df.groupby(["race_label", "category"])["pbk_num"]
        .nunique()
        .reset_index(name="count")
    )
    race_totals = counts.groupby("race_label")["count"].transform("sum")
    counts["pct"] = (counts["count"] / race_totals * 100).round(1)

    # Sort races by conviction rate ascending so highest conviction sits at top of chart
    race_total_map = counts.groupby("race_label")["count"].sum().to_dict()
    conviction_map  = (
        counts.loc[counts["category"] == "Conviction"]
        .set_index("race_label")["count"]
        .to_dict()
    )
    all_races  = counts["race_label"].unique().tolist()
    conv_rates = {r: conviction_map.get(r, 0) / race_total_map.get(r, 1) for r in all_races}
    race_sort  = sorted(all_races, key=lambda r: conv_rates[r])

    return counts, race_sort


def _build_demo_disp_outcomes_bar(df: pd.DataFrame, race_sort: list[str]) -> alt.Chart:
    selection = alt.selection_point(fields=["category"], bind="legend")

    present = [c for c in _OUTCOME_ORDER if c in df["category"].values]
    colors  = [_OUTCOME_COLORS[_OUTCOME_ORDER.index(c)] for c in present]

    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(
                "count:Q",
                stack="normalize",
                title="Share of Disposed Cases",
                axis=alt.Axis(format=".0%"),
            ),
            y=alt.Y("race_label:N", title=None, sort=race_sort),
            color=alt.Color(
                "category:N",
                title="Outcome",
                sort=present,
                scale=alt.Scale(domain=present, range=colors),
            ),
            opacity=alt.condition(selection, alt.value(1.0), alt.value(0.2)),
            tooltip=[
                alt.Tooltip("race_label:N", title="Race"),
                alt.Tooltip("category:N",   title="Outcome"),
                alt.Tooltip("count:Q",      title="Cases",           format=","),
                alt.Tooltip("pct:Q",        title="% of Race Total", format=".1f"),
            ],
        )
        .add_params(selection)
        .properties(width="container")
    )


def render_demo_disp_outcomes(disp: pd.DataFrame) -> None:
    """Render disposition outcome mix by race as a normalized stacked bar chart."""
    df, race_sort = _prepare_demo_disp_outcomes(disp)

    with st.container(border=True):
        st.header(":material/balance: Disposition Outcomes by Race")
        st.caption(
            "Proportional breakdown of disposed case outcomes per racial group, classified "
            "by `min_disp_rank` (most favorable outcome per case). Races are sorted by "
            "conviction rate — highest conviction rate at top. "
            ":green[Conviction] includes trial guilty, guilty plea, and plea deal; "
            ":red[Acquittal] reflects trial not guilty verdicts; Nolle Prosequi cases are "
            "split into :blue[Resolved], :orange[Pending], and :darkred[Unresolved]. "
            "Click a legend category to highlight it."
        )
        st.altair_chart(_build_demo_disp_outcomes_bar(df, race_sort), use_container_width=True)


# --- render_demo_vs_census ---

_CENSUS_SOURCE  = "County Population"
_DEFN_SOURCE    = "Defendant Caseload"
_CENSUS_COLOR   = "#78909c"
_DEFN_COLOR     = "#4da6ff"
_OVER_COLOR     = "#e05c5c"
_UNDER_COLOR    = "#3db87a"


def _prepare_demo_vs_census(
    rcvd: pd.DataFrame,
    census_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Merge defendant racial composition (% of received cases, excluding Unknown)
    with Census county population estimates.

    Returns:
        long_df   — tidy long format for the grouped comparison bar chart
        ratio_df  — one row per race with disparity index (defendant % / population %)
    """
    # Defendant % by race — exclude Unknown from denominator
    def_counts = (
        rcvd[rcvd["def_race"] != "U"]
        .groupby("def_race")["pbk_num"]
        .nunique()
        .reset_index(name="def_count")
    )
    total_def = def_counts["def_count"].sum()
    def_counts["def_pct"] = (
        (def_counts["def_count"] / total_def * 100).round(1) if total_def else 0.0
    )
    def_counts["race_label"] = def_counts["def_race"].map(_RACE_LABELS).fillna("Unknown")

    merged = census_df.merge(
        def_counts[["race_label", "def_pct", "def_count"]],
        on="race_label",
        how="left",
    ).fillna({"def_pct": 0.0, "def_count": 0})

    # Disparity index: defendant share / population share
    merged["disparity"] = (
        (merged["def_pct"] / merged["pct"])
        .where(merged["pct"] > 0, other=0.0)
        .round(2)
    )

    # Sort races by defendant count descending for consistent y-axis order
    sort_order = merged.sort_values("def_count", ascending=False)["race_label"].tolist()

    # Long format for grouped comparison chart
    pop_rows = (
        merged[["race_label", "pct", "population"]]
        .rename(columns={"pct": "value"})
        .assign(source=_CENSUS_SOURCE, count=merged["population"])
    )
    def_rows = (
        merged[["race_label", "def_pct", "def_count"]]
        .rename(columns={"def_pct": "value", "def_count": "count"})
        .assign(source=_DEFN_SOURCE)
    )
    long_df = pd.concat([pop_rows, def_rows], ignore_index=True)
    long_df["sort_order"] = long_df["race_label"].map(
        {r: i for i, r in enumerate(sort_order)}
    )

    return long_df, merged, sort_order


def _build_census_comparison_bar(
    long_df: pd.DataFrame,
    sort_order: list[str],
) -> alt.Chart:
    """Grouped horizontal bar — defendant % vs. county population % by race."""
    source_order  = [_DEFN_SOURCE, _CENSUS_SOURCE]
    source_colors = [_DEFN_COLOR, _CENSUS_COLOR]

    selection = alt.selection_point(fields=["source"], bind="legend")

    return (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "value:Q",
                title="Share (%)",
                axis=alt.Axis(format=".1f"),
            ),
            y=alt.Y("race_label:N", title=None, sort=sort_order),
            yOffset=alt.YOffset("source:N", sort=source_order),
            color=alt.Color(
                "source:N",
                title="Source",
                sort=source_order,
                scale=alt.Scale(domain=source_order, range=source_colors),
            ),
            opacity=alt.condition(selection, alt.value(1.0), alt.value(0.2)),
            tooltip=[
                alt.Tooltip("race_label:N", title="Race"),
                alt.Tooltip("source:N",     title="Source"),
                alt.Tooltip("value:Q",      title="Share (%)", format=".1f"),
                alt.Tooltip("count:Q",      title="Count",     format=","),
            ],
        )
        .add_params(selection)
        .properties(width="container")
    )


def _build_census_disparity_bar(
    ratio_df: pd.DataFrame,
    sort_order: list[str],
) -> alt.Chart:
    """Horizontal bar — disparity index (defendant % / county %) by race."""
    df = ratio_df.copy()
    df["color"] = df["disparity"].apply(
        lambda v: "Over-represented" if v > 1.0 else "Under-represented"
    )

    ref_df = pd.DataFrame({"x": [1.0]})
    rule = (
        alt.Chart(ref_df)
        .mark_rule(strokeDash=[5, 4], strokeWidth=2, color=_CENSUS_COLOR)
        .encode(x=alt.X("x:Q"))
    )

    bars = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(
                "disparity:Q",
                title="Disparity Index  (defendant % ÷ population %)",
                scale=alt.Scale(domainMin=0),
            ),
            y=alt.Y("race_label:N", title=None, sort=sort_order),
            color=alt.Color(
                "color:N",
                title="Representation",
                scale=alt.Scale(
                    domain=["Over-represented", "Under-represented"],
                    range=[_OVER_COLOR, _UNDER_COLOR],
                ),
            ),
            tooltip=[
                alt.Tooltip("race_label:N", title="Race"),
                alt.Tooltip("def_pct:Q",    title="Defendant %",    format=".1f"),
                alt.Tooltip("pct:Q",        title="Population %",   format=".1f"),
                alt.Tooltip("disparity:Q",  title="Disparity Index", format=".2f"),
            ],
        )
    )

    return (bars + rule).properties(width="container")


def render_demo_vs_census(
    rcvd: pd.DataFrame,
    census_df: pd.DataFrame,
    census_note: str = "latest",
) -> None:
    """
    Render defendant racial composition vs. Jackson County population estimates
    from the US Census ACS 5-year survey.

    census_note: "exact" if the ACS vintage matches the selected year,
                 "latest" if a multi-year date range defaulted to latest available.
    """
    long_df, ratio_df, sort_order = _prepare_demo_vs_census(rcvd, census_df)
    acs_year = census_df["acs_year"].iloc[0] if "acs_year" in census_df.columns else "N/A"
    span_start = int(acs_year) - 4 if isinstance(acs_year, (int, float)) else "N/A"

    if census_note == "exact":
        vintage_note = f"ACS {acs_year} (5-year estimates, {span_start}–{acs_year}), matched to the selected year"
    else:
        vintage_note = f"ACS {acs_year} (5-year estimates, {span_start}–{acs_year}), latest available — selected range spans multiple years"

    with st.container(border=True):
        st.header(":material/compare: Defendant Race vs. County Population")
        st.caption(
            f"Compares the racial composition of received cases (defendant caseload, "
            f"excluding Unknown race) against Jackson County population estimates from the "
            f"US Census ({vintage_note}). The **Disparity Index** tab shows the ratio of "
            f"defendant share to population share — a value above 1.0 indicates a racial "
            f"group is over-represented in the caseload relative to their share of the county "
            f"population; below 1.0 indicates under-representation."
        )

        tab_compare, tab_disparity = st.tabs(["Comparison", "Disparity Index"])
        with tab_compare:
            st.altair_chart(
                _build_census_comparison_bar(long_df, sort_order),
                use_container_width=True,
            )
        with tab_disparity:
            st.altair_chart(
                _build_census_disparity_bar(ratio_df, sort_order),
                use_container_width=True,
            )


# --- render_census_trend ---

def _prepare_census_trend(census_all: pd.DataFrame) -> pd.DataFrame:
    df = census_all.copy()
    df["acs_year"] = df["acs_year"].astype(str)
    return df


def _build_census_trend_bar(df: pd.DataFrame) -> alt.Chart:
    years      = sorted(df["acs_year"].unique().tolist())
    race_order = (
        df.groupby("race_label")["pct"]
        .mean()
        .sort_values(ascending=False)
        .index.tolist()
    )

    selection = alt.selection_point(fields=["acs_year"], bind="legend")

    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(
                "race_label:N",
                title=None,
                sort=race_order,
                axis=alt.Axis(labelAngle=-45),
            ),
            xOffset=alt.XOffset("acs_year:O", sort=years),
            y=alt.Y("pct:Q", title="Share of County Population (%)"),
            color=alt.Color(
                "acs_year:O",
                title="ACS Year",
                sort=years,
                scale=alt.Scale(scheme="blues"),
            ),
            opacity=alt.condition(selection, alt.value(1.0), alt.value(0.2)),
            tooltip=[
                alt.Tooltip("race_label:N", title="Race / Ethnicity"),
                alt.Tooltip("acs_year:O",   title="ACS Year"),
                alt.Tooltip("pct:Q",        title="% of County",  format=".1f"),
                alt.Tooltip("population:Q", title="Population",   format=","),
            ],
        )
        .add_params(selection)
        .properties(width="container")
    )


def render_census_trend(census_all: pd.DataFrame) -> None:
    """Grouped bar chart of Jackson County racial composition across ACS vintage years."""
    df = _prepare_census_trend(census_all)

    with st.container(border=True):
        st.header(":material/trending_up: County Racial Composition Over Time")
        st.caption(
            "Racial and ethnic composition of Jackson County, MO across ACS 5-year vintage "
            "years. Bars are grouped by race — each cluster shows how that group's share of "
            "the county population has changed year over year. Note: ACS vintages are 5-year "
            "rolling estimates, so adjacent years are not fully independent. Click a year in "
            "the legend to isolate it."
        )
        st.altair_chart(_build_census_trend_bar(df), use_container_width=True)


# --- render_county_composition ---

# Fixed color per race label — consistent across all years
_COUNTY_RACE_COLORS: dict[str, str] = {
    "White":            "#4da6ff",
    "Black":            "#3db87a",
    "Hispanic":         "#e8a838",
    "Asian":            "#e05c5c",
    "Am. Indian":       "#9b59b6",
    "Pacific Islander": "#1abc9c",
    "Multiracial":      "#78909c",
    "Other":            "#f0a0c0",
}


def _build_county_donut(df: pd.DataFrame) -> go.Figure:
    """Donut chart of county racial composition for a single ACS vintage year."""
    df = df.sort_values("pct", ascending=False).reset_index(drop=True)
    colors = [_COUNTY_RACE_COLORS.get(r, "#aaaaaa") for r in df["race_label"]]

    fig = go.Figure(
        go.Pie(
            labels=df["race_label"],
            values=df["pct"],
            hole=0.5,
            marker=dict(colors=colors),
            textposition="outside",
            texttemplate="%{label}<br>%{value:.1f}%",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Population: %{customdata:,}<br>"
                "Share: %{value:.1f}%"
                "<extra></extra>"
            ),
            customdata=df["population"],
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e8eaf0", size=12),
        margin=dict(t=40, b=40, l=120, r=120),
        showlegend=True,
        legend=dict(font=dict(color="#e8eaf0")),
    )
    return fig


def render_county_composition() -> None:
    """
    Donut chart of Jackson County racial composition using ACS 5-year estimates.
    Year selector lets users browse vintages from 2016 to the latest available.
    Fetches and caches each year independently via get_census_demographics().
    """
    from census_data import get_census_demographics, get_latest_acs_year

    latest_year = get_latest_acs_year()
    if latest_year is None:
        with st.container(border=True):
            st.header(":material/donut_large: Jackson County Racial Composition")
            st.warning("Census data unavailable.", icon=":material/cloud_off:")
        return

    years = list(range(latest_year, 2015, -1))  # descending: latest first

    with st.container(border=True):
        st.header(":material/donut_large: Jackson County Racial Composition")
        st.caption(
            "Racial and ethnic composition of Jackson County, MO based on the US Census "
            "ACS 5-year estimates. Each vintage year represents a 5-year rolling average "
            "ending in that year (e.g., 2022 covers 2018–2022). Select a year to explore "
            "how the county's demographic makeup has shifted over time. Click a legend "
            "entry to isolate that group."
        )

        selected_year = st.selectbox(
            "ACS Vintage Year",
            options=years,
            format_func=lambda y: f"{y}  ({y - 4}–{y})",
            key="county_composition_year",
        )

        census_df = get_census_demographics(selected_year)
        if census_df is None:
            st.warning(f"ACS {selected_year} data could not be loaded.", icon=":material/cloud_off:")
            return

        st.plotly_chart(_build_county_donut(census_df), use_container_width=True)
