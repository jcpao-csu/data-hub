# stats/ntfld_volume.py
# Visualizations for cases not filed:
#   - render_ntfld_volume  : total cases not filed by period (bar + line)

import altair as alt
import pandas as pd
import streamlit as st

_COLOR = "#f5c842"  # yellow


def _prepare_ntfld_volume(ntfld: pd.DataFrame) -> pd.DataFrame:
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    counts = (
        ntfld.groupby("period")["pbk_num"]
        .nunique()
        .reindex(full_index, fill_value=0)
    )
    counts.index.name = "period"
    counts = counts.reset_index().rename(columns={"pbk_num": "total_cases"})
    counts["period"] = counts["period"].astype(str)
    return counts


def _build_ntfld_volume_bar(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(color=_COLOR)
        .encode(
            x=alt.X("period:O", title=None),
            y=alt.Y("total_cases:Q", title=None),
            tooltip=[
                alt.Tooltip("period:O",       title="Period"),
                alt.Tooltip("total_cases:Q",  title="Cases Not Filed", format=","),
            ],
        )
        .properties(width="container", title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"))
    )


def _build_ntfld_volume_line(df: pd.DataFrame) -> alt.Chart:
    hover = alt.selection_point(nearest=True, on="mouseover", fields=["period"], empty=False)
    tooltips = [
        alt.Tooltip("period:O",       title="Period"),
        alt.Tooltip("total_cases:Q",  title="Cases Not Filed", format=","),
    ]
    base = alt.Chart(df).encode(
        x=alt.X("period:O", title="Period"),
        y=alt.Y("total_cases:Q", title="Cases Not Filed"),
        tooltip=tooltips,
    )
    line = base.mark_line(color=_COLOR, strokeWidth=2, interpolate="monotone")
    points = (
        base.mark_point(color=_COLOR, filled=True, size=80)
        .encode(opacity=alt.condition(hover, alt.value(1), alt.value(0)))
        .add_params(hover)
    )
    rule = (
        base.mark_rule(strokeWidth=1)
        .encode(x="period:O", opacity=alt.condition(hover, alt.value(0.3), alt.value(0)))
    )
    return (rule + line + points).properties(width="container")


def render_ntfld_volume(ntfld: pd.DataFrame) -> None:
    df = _prepare_ntfld_volume(ntfld)
    _FREQ_LABEL = {"M": "Monthly", "Q": "Quarterly", "Y": "Yearly"}
    start, end  = st.session_state["date_range_filter"]
    freq        = st.session_state["period_freq_filter"]
    subtitle    = f"{_FREQ_LABEL.get(freq, freq)} totals · {pd.Timestamp(str(start)).strftime('%b %Y')} – {pd.Timestamp(str(end)).strftime('%b %Y')}"
    with st.container(border=True):
        st.header(":material/block: Cases Not Filed")
        tab_bar, tab_line = st.tabs(["Bar Chart", "Line Chart"])
        with tab_bar:
            st.altair_chart(_build_ntfld_volume_bar(df, title="Cases Not Filed", subtitle=subtitle))
        with tab_line:
            st.altair_chart(_build_ntfld_volume_line(df))
