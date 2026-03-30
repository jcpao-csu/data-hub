# ntfld_cases.py
# JCPAO Dashboard — Not Filed Cases Page
#
# Tracks cases declined by the office, with a focus on self defense declines.
# Charts respond to global sidebar filters (date range, period frequency, etc.)
# and a local Count / Percentage toggle.

import altair as alt
import pandas as pd
import streamlit as st

from read_data import get_dataframes
from session_state import get_filtered_data, render_sidebar
from stats.ntfld_volume import render_ntfld_volume
from stats.ntfld_reasons import render_ntfld_reasons, render_ntfld_treemap
from stats.ntfld_refiled import render_ntfld_refiled
from stats.ntfld_sankey import render_ntfld_sankey

# ---------------------------------------------------------------------------
# Load unfiltered data (safe before sidebar — no st.stop() risk)
# ---------------------------------------------------------------------------

_, FLD, _, _, _, _ = get_dataframes()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**Not Filed Cases**")
    st.divider()
    render_sidebar()

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.markdown("<h1 style='text-align: center;'>Not Filed Cases</h1>", unsafe_allow_html=True)
st.divider()

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

_, _, ntfld, _ = get_filtered_data()

render_ntfld_volume(ntfld)
render_ntfld_sankey(ntfld)
render_ntfld_reasons(ntfld)
render_ntfld_treemap(ntfld)
render_ntfld_refiled(ntfld, FLD)

# ---------------------------------------------------------------------------
# Data prep
# ---------------------------------------------------------------------------

_SD_COLOR = "#e8a838"

def _build_self_defense(ntfld: pd.DataFrame) -> pd.DataFrame:
    """
    Group not-filed cases by period and return counts of self-defense declines
    alongside total not-filed cases and the percentage share.

    A case is counted as a self-defense decline when:
      - min_ntfld_category == 'Self Defense', OR
      - min_ntfld_rank == 5 (the coded value for self defense)

    Periods within the selected date range that have zero not-filed cases are
    included via reindex so the chart x-axis has no gaps.
    """
    df = ntfld.copy()
    df["is_sd"] = (df["min_ntfld_category"] == "Self Defense") | (df["min_ntfld_rank"] == 5)

    grouped = (
        df.groupby("period")
        .agg(
            self_defense=("is_sd", "sum"),
            total_ntfld=("is_sd", "count"),
        )
    )

    # Build the complete period index from the sidebar date range + frequency
    # so that periods with zero cases are not silently dropped.
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)
    grouped = grouped.reindex(full_index, fill_value=0)
    grouped.index.name = "period"
    grouped = grouped.reset_index()

    grouped["pct"] = (
        (grouped["self_defense"] / grouped["total_ntfld"] * 100)
        .where(grouped["total_ntfld"] > 0, other=0.0)
        .round(1)
    )
    grouped["period"] = grouped["period"].astype(str)
    return grouped


sd_df = _build_self_defense(ntfld)

if sd_df.empty or sd_df["self_defense"].sum() == 0:
    st.info("No self defense declines found for the selected filters.")
    st.stop()

# ---------------------------------------------------------------------------
# Summary callout
# ---------------------------------------------------------------------------

total_sd = int(sd_df["self_defense"].sum())
total_ntfld_all = int(sd_df["total_ntfld"].sum())
overall_pct = round(total_sd / total_ntfld_all * 100, 1) if total_ntfld_all > 0 else 0.0

# ---------------------------------------------------------------------------
# Visualization container
# ---------------------------------------------------------------------------

with st.container():

    st.header("Cases Declined by Self Defense")
    st.caption(
        "Tracks not-filed cases where the office determined that the defendant "
        "acted in self defense. A case is flagged when the minimum not-filed "
        "reason is categorized as 'Self Defense' (or coded as rank 5). "
        "Periods with no cases are shown as zero rather than omitted."
    )

    st.markdown(
        f":orange-background[**{total_sd:,}** cases were declined due to self defense "
        f"(**{overall_pct:.1f}%** of all not-filed cases) during the selected period.]"
    )
    st.write(" ")

    # View toggle
    view_mode = st.segmented_control(
        "Display",
        options=["Count", "Percentage"],
        default="Count",
        key="sd_view_mode",
    )

    y_field = "self_defense" if view_mode == "Count" else "pct"
    y_title = "Self Defense Cases" if view_mode == "Count" else "% of Not-Filed Cases"

    _TOOLTIPS = [
        alt.Tooltip("period:O",       title="Period"),
        alt.Tooltip("self_defense:Q", title="Self Defense Cases", format=","),
        alt.Tooltip("total_ntfld:Q",  title="Total Not Filed",    format=","),
        alt.Tooltip("pct:Q",          title="% Self Defense",     format=".1f"),
    ]

    # Chart builders

    def _bar_chart(df: pd.DataFrame, y_field: str, y_title: str) -> alt.Chart:
        return (
            alt.Chart(df)
            .mark_bar(color=_SD_COLOR)
            .encode(
                x=alt.X("period:O", title="Period"),
                y=alt.Y(f"{y_field}:Q", title=y_title),
                tooltip=_TOOLTIPS,
            )
            .properties(width="container")
        )

    def _line_chart(df: pd.DataFrame, y_field: str, y_title: str) -> alt.LayerChart:
        hover = alt.selection_point(nearest=True, on="mouseover", fields=["period"], empty=False)
        base = alt.Chart(df).encode(
            x=alt.X("period:O", title="Period"),
            y=alt.Y(f"{y_field}:Q", title=y_title),
            tooltip=_TOOLTIPS,
        )
        line   = base.mark_line(color=_SD_COLOR, strokeWidth=2, interpolate="monotone")
        points = (
            base.mark_point(color=_SD_COLOR, filled=True, size=80)
            .encode(opacity=alt.condition(hover, alt.value(1), alt.value(0)))
            .add_params(hover)
        )
        return (line + points).properties(width="container")

    # Tabs
    tab_bar, tab_line = st.tabs(["Bar Chart", "Line Chart"])

    with tab_bar:
        st.altair_chart(_bar_chart(sd_df, y_field, y_title), use_container_width=True)

    with tab_line:
        st.altair_chart(_line_chart(sd_df, y_field, y_title), use_container_width=True)
