# stats/rcvd_by_agency.py
# Received cases broken down by referring agency.
# Renders stacked area, normalized, and line charts of top submitting agencies.

import altair as alt
import pandas as pd
import streamlit as st

# Top 9 agencies + "All Other Agencies"
_AGENCY_PALETTE = [
    "#4da6ff",  # 1
    "#f28e2b",  # 2
    "#e05c5c",  # 3
    "#3db87a",  # 4
    "#a78bfa",  # 5
    "#f5c842",  # 6
    "#26c6da",  # 7
    "#ff9da7",  # 8
    "#9c755f",  # 9
    "#78909c",  # All Other Agencies
]
_OTHER_LABEL = "All Other Agencies"
_AGENCY_RENAME = {
    "Missouri State Highway Patrol": "MSHP",
    "Jackson County Sheriff":        "JaCo Sheriff",
}


def _prepare_rcvd_by_agency(rcvd: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """
    Group received cases by period and agency.
    Top 9 agencies by overall total are named individually; the rest are summed
    into 'All Other Agencies'. Returns (df, domain, colors) for the color scale.
    """
    df = rcvd.copy()
    df["agency_name"] = df["agency_name"].replace(_AGENCY_RENAME)

    agency_totals = (
        df.groupby("agency_name")["pbk_num"]
        .nunique()
        .sort_values(ascending=False)
    )
    top_9 = agency_totals.head(9).index.tolist()

    df["Agency"] = df["agency_name"].where(df["agency_name"].isin(top_9), other=_OTHER_LABEL)

    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    wide = (
        df.groupby(["period", "Agency"])["pbk_num"]
        .nunique()
        .unstack(fill_value=0)
        .reindex(full_index, fill_value=0)
    )
    wide.index.name = "period"
    wide = wide.reset_index()

    melted = wide.melt(id_vars="period", var_name="Agency", value_name="total_cases")
    melted["period"] = melted["period"].astype(str)

    period_totals = melted.groupby("period")["total_cases"].transform("sum")
    melted["pct"] = (
        (melted["total_cases"] / period_totals * 100)
        .where(period_totals > 0, other=0.0)
        .round(1)
    )
    # Build ordered domain: top 9 in rank order, then "All Other Agencies"
    domain = top_9 + ([_OTHER_LABEL] if _OTHER_LABEL in melted["Agency"].values else [])
    colors = _AGENCY_PALETTE[: len(domain)]

    # rank=0 → largest agency → bottom of stack (Vega-Lite stacks ascending)
    rank_map = {agency: i for i, agency in enumerate(domain)}
    melted["rank"] = melted["Agency"].map(rank_map)
    melted = melted.reset_index(drop=True)

    return melted, domain, colors


def _build_rcvd_by_agency_area(
    df: pd.DataFrame,
    domain: list[str],
    colors: list[str],
    stack: str | bool,
) -> alt.Chart:
    """Stacked or normalized 100% area chart — received cases by agency over time."""
    legend_sel = alt.selection_point(fields=["Agency"], bind="legend")

    if stack == "normalize":
        y_enc = alt.Y("total_cases:Q", stack="normalize", axis=alt.Axis(format="%", title="Share of Cases"))
    else:
        y_enc = alt.Y("total_cases:Q", stack=True, title="Cases Received")

    tooltips = [
        alt.Tooltip("period:O",       title="Period"),
        alt.Tooltip("Agency:N",       title="Agency"),
        alt.Tooltip("total_cases:Q",  title="Cases Received",    format=","),
        alt.Tooltip("pct:Q",          title="% of Period Total", format=".1f"),
    ]

    return (
        alt.Chart(df)
        .mark_area(interpolate="monotone")
        .encode(
            x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
            y=y_enc,
            color=alt.Color(
                "Agency:N",
                title="Agency",
                sort=domain,
                scale=alt.Scale(domain=domain, range=colors),
            ),
            order=alt.Order("rank:Q"),
            opacity=alt.condition(legend_sel, alt.value(0.85), alt.value(0.15)),
            tooltip=tooltips,
        )
        .add_params(legend_sel)
        .properties(width="container")
    )


def _build_rcvd_by_agency_line(
    df: pd.DataFrame,
    domain: list[str],
    colors: list[str],
) -> alt.Chart:
    """Multi-line chart — received cases by agency over time, with hover-only points."""
    legend_sel = alt.selection_point(fields=["Agency"], bind="legend")
    hover      = alt.selection_point(nearest=True, on="mouseover", fields=["period"], empty=False)

    color_enc = alt.Color(
        "Agency:N",
        title="Agency",
        sort=domain,
        scale=alt.Scale(domain=domain, range=colors),
    )
    tooltips = [
        alt.Tooltip("period:O",       title="Period"),
        alt.Tooltip("Agency:N",       title="Agency"),
        alt.Tooltip("total_cases:Q",  title="Cases Received",    format=","),
        alt.Tooltip("pct:Q",          title="% of Period Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("total_cases:Q", title="Cases Received"),
        color=color_enc,
        tooltip=tooltips,
    )

    line = (
        base.mark_line(strokeWidth=2, interpolate="monotone")
        .encode(opacity=alt.condition(legend_sel, alt.value(1.0), alt.value(0.2)))
        .add_params(legend_sel)
    )
    points = (
        base.mark_point(filled=True, size=80)
        .encode(opacity=alt.condition(hover, alt.value(1), alt.value(0)))
        .add_params(hover)
    )

    return (line + points).properties(width="container")


def render_rcvd_by_agency(rcvd: pd.DataFrame) -> None:
    """Render stacked area, normalized, and line charts of received cases by top agencies."""
    with st.container(border=True):
        st.header(":material/local_police: Top Submitting Agencies")

        df, domain, colors = _prepare_rcvd_by_agency(rcvd)

        tab_line, tab_stacked, tab_normalized = st.tabs(["Line Chart", "Stacked", "Normalized (%)"])
        with tab_line:
            st.altair_chart(
                _build_rcvd_by_agency_line(df, domain, colors),
                width="container",
            )
        with tab_stacked:
            st.altair_chart(
                _build_rcvd_by_agency_area(df, domain, colors, True),
                width="container",
            )
        with tab_normalized:
            st.altair_chart(
                _build_rcvd_by_agency_area(df, domain, colors, "normalize"),
                width="container",
            )
