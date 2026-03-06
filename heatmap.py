# heatmap.py
# JCPAO Dashboard — Calendar heatmaps: avg cases by day-of-month × month, smoothed across years
#
# USAGE:
#   from heatmap import render_heatmaps
#   from session_state import get_filtered_data
#
#   rcvd, fld, ntfld, disp = get_filtered_data()
#   render_heatmaps(rcvd, fld, ntfld, disp)

import altair as alt
import pandas as pd
import streamlit as st

from session_state import get_filtered_data, MSHP_CODES

# Load filtered data (see session_state.py)
rcvd, fld, ntfld, disp = get_filtered_data()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_MONTH_ORDER = [
    "Jan", "Feb", "Mar", "Apr", "May",
    "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

_CHARTS = [
    {
        "label":         "Cases Received",
        "date_col":      "ref_date",
        "color_scheme":  "blues",
        "tooltip_title": "Avg. received/day",
    },
    {
        "label":         "Cases Filed",
        "date_col":      "earliest_fld_date",
        "color_scheme":  "greens",
        "tooltip_title": "Avg. filed/day",
    },
    {
        "label":         "Cases Not Filed",
        "date_col":      "earliest_ntfld_date",
        "color_scheme":  "oranges",
        "tooltip_title": "Avg. not filed/day",
    },
    {
        "label":         "Cases Disposed",
        "date_col":      "earliest_disp_date",
        "color_scheme":  "purples",
        "tooltip_title": "Avg. disposed/day",
    },
]

# ---------------------------------------------------------------------------
# Data prep
# ---------------------------------------------------------------------------

def _prepare(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """
    Compute average cases per (month, day-of-month) cell, averaged across
    all years in the data. E.g. "Jan 15" shows the mean case count across
    every Jan 15 that appears in the dataset.
    """
    out = df[["pbk_num", date_col]].copy()
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    out = out.dropna(subset=[date_col])
    out = out.drop_duplicates(subset=["pbk_num"])

    out["year"]       = out[date_col].dt.year
    out["month_num"]  = out[date_col].dt.month
    out["month_abbr"] = out[date_col].dt.strftime("%b")
    out["day"]        = out[date_col].dt.day

    # Step 1: count cases per (year, month, day) — how many hit that exact date
    daily_counts = (
        out.groupby(["year", "month_num", "month_abbr", "day"])["pbk_num"]
        .nunique()
        .reset_index(name="count")
    )

    # Step 2: average across years per (month, day) cell
    averaged = (
        daily_counts.groupby(["month_num", "month_abbr", "day"])["count"]
        .mean()
        .reset_index(name="avg_cases")
    )
    averaged["avg_cases"] = averaged["avg_cases"].round(2)

    # Drop impossible dates (e.g. Feb 30) that may appear as anomalies
    averaged = averaged.loc[averaged["avg_cases"] > 0].copy()

    return averaged


# ---------------------------------------------------------------------------
# Chart builder
# ---------------------------------------------------------------------------

def _build_chart(
    averaged: pd.DataFrame,
    label: str,
    color_scheme: str,
    tooltip_title: str,
) -> alt.Chart | None:
    """
    Build a single heatmap: day-of-month (x) × month (y), color = avg cases.
    Smoothed across all years — no faceting.
    """
    if averaged.empty:
        return None

    chart = (
        alt.Chart(averaged)
        .mark_rect(stroke="white", strokeWidth=0.8)
        .encode(
            x=alt.X(
                "day:O",
                title="Day of Month",
                axis=alt.Axis(
                    labelAngle=0,
                    labelFontSize=10,
                    ticks=False,
                    domain=False,
                ),
            ),
            y=alt.Y(
                "month_abbr:O",
                sort=_MONTH_ORDER,
                title=None,
                axis=alt.Axis(
                    labelFontSize=11,
                    ticks=False,
                    domain=False,
                ),
            ),
            color=alt.Color(
                "avg_cases:Q",
                title=tooltip_title,
                scale=alt.Scale(scheme=color_scheme),
                legend=alt.Legend(
                    orient="right",
                    titleFontSize=10,
                    labelFontSize=9,
                    gradientLength=100,
                ),
            ),
            tooltip=[
                alt.Tooltip("month_abbr:O", title="Month"),
                alt.Tooltip("day:O",        title="Day"),
                alt.Tooltip("avg_cases:Q",  title=tooltip_title, format=".2f"),
            ],
        )
        .properties(
            width="container",
            height=220,
            title=alt.TitleParams(
                text=label,
                subtitle="Average cases per calendar day, across all years in selected date range",
                fontSize=14,
                subtitleFontSize=11,
                subtitleColor="#777",
                anchor="start",
            ),
        )
        .configure_view(strokeWidth=0)
        .configure_axis(domain=False)
    )

    return chart


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_heatmaps(
    rcvd: pd.DataFrame = rcvd,
    fld: pd.DataFrame = fld,
    ntfld: pd.DataFrame = ntfld,
    disp: pd.DataFrame = disp,
) -> None:
    """
    Render four stacked calendar heatmaps (received, filed, not filed, disposed).
    Each chart shows day-of-month × month, averaged across all years in the
    selected date range.
    """
    dataframes = {
        "Cases Received":  (rcvd,  "ref_date"),
        "Cases Filed":     (fld,   "earliest_fld_date"),
        "Cases Not Filed": (ntfld, "earliest_ntfld_date"),
        "Cases Disposed":  (disp,  "earliest_disp_date"),
    }

    for cfg in _CHARTS:
        label        = cfg["label"]
        df, date_col = dataframes[label]

        averaged = _prepare(df, date_col)
        chart    = _build_chart(averaged, label, cfg["color_scheme"], cfg["tooltip_title"])

        if chart is None:
            st.info(f"No data available for **{label}** with the current filters.")
        else:
            st.altair_chart(chart, use_container_width=True)

        st.divider()


render_heatmaps()