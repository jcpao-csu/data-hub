# stats/case_volume.py
# Total cases processed by period — received, filed, not filed, disposed.
# Renders a grouped bar chart and a line chart, toggled via st.tabs.

import altair as alt
import pandas as pd
import streamlit as st

_STATUS_ORDER  = ["Received", "Filed", "Not Filed", "Disposed"]
_STATUS_COLORS = ["#4da6ff", "#3db87a", "#f5c842", "#e05c5c"]

_CONFIGS = [
    ("Received",  "period"),
    ("Filed",     "period"),
    ("Not Filed", "period"),
    ("Disposed",  "period"),
]


def _prepare_case_volume(
    rcvd: pd.DataFrame,
    fld: pd.DataFrame,
    ntfld: pd.DataFrame,
    disp: pd.DataFrame,
) -> pd.DataFrame:
    """Wrangle all four case-status DataFrames into a single tidy long-format DataFrame."""
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    configs = [
        (rcvd,  "Received"),
        (fld,   "Filed"),
        (ntfld, "Not Filed"),
        (disp,  "Disposed"),
    ]

    dfs = []
    for df, status in configs:
        counts = df.groupby("period")["pbk_num"].nunique()
        counts = counts.reindex(full_index, fill_value=0)
        counts.index.name = "period"
        counts = counts.reset_index()
        counts = counts.rename(columns={"pbk_num": "total_cases"})
        counts["Case Status"] = status
        counts["period"] = counts["period"].astype(str)
        dfs.append(counts)

    combined = pd.concat(dfs, ignore_index=True)
    combined["Case Status"] = pd.Categorical(
        combined["Case Status"],
        categories=_STATUS_ORDER,
        ordered=True,
    )
    return combined


def _build_case_volume_bar(df: pd.DataFrame) -> alt.Chart:
    """Grouped bar chart — total cases by period and case status."""
    selection = alt.selection_point(fields=["Case Status"], bind="legend")

    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("total_cases:Q", title="Case Volume"),
            color=alt.Color(
                "Case Status:N",
                sort=_STATUS_ORDER,
                title="Case Status",
                scale=alt.Scale(domain=_STATUS_ORDER, range=_STATUS_COLORS),
            ),
            xOffset=alt.XOffset("Case Status:N", sort=_STATUS_ORDER),
            opacity=alt.condition(selection, alt.value(1.0), alt.value(0.2)),
            tooltip=[
                alt.Tooltip("period:O",       title="Period"),
                alt.Tooltip("Case Status:N",  title="Case Status"),
                alt.Tooltip("total_cases:Q",  title="Total Cases", format=","),
            ],
        )
        .add_params(selection)
        .properties(width="container")
    )


def _build_case_volume_line(df: pd.DataFrame) -> alt.Chart:
    """Line chart — total cases by period and case status, with hover-only points."""
    selection = alt.selection_point(fields=["Case Status"], bind="legend")
    hover = alt.selection_point(nearest=True, on="mouseover", fields=["period"], empty=False)

    tooltips = [
        alt.Tooltip("period:O",       title="Period"),
        alt.Tooltip("Case Status:N",  title="Case Status"),
        alt.Tooltip("total_cases:Q",  title="Total Cases", format=","),
    ]

    base = alt.Chart(df).encode(
        x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("total_cases:Q", title="Case Volume"),
        color=alt.Color(
            "Case Status:N",
            sort=_STATUS_ORDER,
            title="Case Status",
            scale=alt.Scale(domain=_STATUS_ORDER, range=_STATUS_COLORS),
        ),
        tooltip=tooltips,
    )

    line = (
        base.mark_line(strokeWidth=2, interpolate="monotone")
        .encode(opacity=alt.condition(selection, alt.value(1.0), alt.value(0.2)))
        .add_params(selection)
    )

    points = (
        base.mark_point(filled=True, size=80)
        .encode(opacity=alt.condition(hover, alt.value(1), alt.value(0)))
        .add_params(hover)
    )

    return (line + points).properties(width="container")


def render_case_volume(
    rcvd: pd.DataFrame,
    fld: pd.DataFrame,
    ntfld: pd.DataFrame,
    disp: pd.DataFrame,
) -> None:
    """Render grouped bar and line charts of total cases processed by period."""
    df = _prepare_case_volume(rcvd, fld, ntfld, disp)

    with st.container(border=True):
        st.header(":material/bar_chart: Cases Processed")
        # st.caption(
        #     "Total cases received, filed, not filed, and disposed grouped by the selected "
        #     "period granularity. Click a status in the legend to highlight or isolate it. "
        #     "Periods with no cases are shown as zero rather than omitted."
        # )

        tab_line, tab_bar = st.tabs(["Line Chart", "Bar Chart"])
        with tab_line:
            st.altair_chart(_build_case_volume_line(df), use_container_width=True)
        with tab_bar:
            st.altair_chart(_build_case_volume_bar(df), use_container_width=True)
