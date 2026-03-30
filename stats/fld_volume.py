# stats/fld_volume.py
# Visualizations for cases filed:
#   - render_fld_volume    : total cases filed by period (bar + line)
#   - render_file_rate     : filing rate (filed / filed+not filed) by period
#   - render_decision_time : median & mean days from referral to charging decision

import altair as alt
import pandas as pd
import streamlit as st

_COLOR     = "#3db87a"   # green
_FLD_COLOR = "#3db87a"   # green (filed)
_NF_COLOR  = "#f5c842"   # yellow (not filed)


# --- render_fld_volume ---

def _prepare_fld_volume(fld: pd.DataFrame) -> pd.DataFrame:
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    counts = (
        fld.groupby("period")["pbk_num"]
        .nunique()
        .reindex(full_index, fill_value=0)
    )
    counts.index.name = "period"
    counts = counts.reset_index().rename(columns={"pbk_num": "total_cases"})
    counts["period"] = counts["period"].astype(str)
    return counts


def _build_fld_volume_bar(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(color=_COLOR)
        .encode(
            x=alt.X("period:O", title=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("total_cases:Q", title=None),
            tooltip=[
                alt.Tooltip("period:O",       title="Period"),
                alt.Tooltip("total_cases:Q",  title="Cases Filed", format=","),
            ],
        )
        .properties(width="container", title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"))
    )


def _build_fld_volume_line(df: pd.DataFrame) -> alt.Chart:
    hover = alt.selection_point(nearest=True, on="mouseover", fields=["period"], empty=False)
    tooltips = [
        alt.Tooltip("period:O",       title="Period"),
        alt.Tooltip("total_cases:Q",  title="Cases Filed", format=","),
    ]
    base = alt.Chart(df).encode(
        x=alt.X("period:O", title="Period"),
        y=alt.Y("total_cases:Q", title="Cases Filed"),
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


def render_fld_volume(fld: pd.DataFrame) -> None:
    df = _prepare_fld_volume(fld)
    _FREQ_LABEL = {"M": "Monthly", "Q": "Quarterly", "Y": "Yearly"}
    start, end  = st.session_state["date_range_filter"]
    freq        = st.session_state["period_freq_filter"]
    subtitle    = f"{_FREQ_LABEL.get(freq, freq)} totals · {pd.Timestamp(str(start)).strftime('%b %Y')} – {pd.Timestamp(str(end)).strftime('%b %Y')}"
    with st.container(border=True):
        st.header(":material/task_alt: Cases Filed")
        tab_bar, tab_line = st.tabs(["Bar Chart", "Line Chart"])
        with tab_bar:
            st.altair_chart(_build_fld_volume_bar(df, title="Cases Filed", subtitle=subtitle), use_container_width=True)
        with tab_line:
            st.altair_chart(_build_fld_volume_line(df), use_container_width=True)


# --- render_file_rate ---

def _prepare_file_rate(fld: pd.DataFrame, ntfld: pd.DataFrame) -> pd.DataFrame:
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    fld = fld.copy()
    fld["file_status"] = "Filed"

    ntfld = ntfld.copy()
    ntfld = ntfld.loc[ntfld["min_ntfld_rank"] != 3]  # exclude PFI
    ntfld = ntfld.loc[~ntfld["pbk_num"].isin(fld["pbk_num"])]  # exclude cases also filed
    ntfld["file_status"] = "Not Filed"

    combined = pd.concat([
        fld[["period", "pbk_num", "file_status"]],
        ntfld[["period", "pbk_num", "file_status"]],
    ], ignore_index=True)

    counts = (
        combined.groupby(["period", "file_status"])["pbk_num"]
        .nunique()
        .reset_index(name="count")
    )

    # Pivot then reindex to full period range
    pivot = (
        counts.pivot_table(index="period", columns="file_status", values="count", fill_value=0)
        .rename_axis(None, axis=1)
    )
    for col in ["Filed", "Not Filed"]:
        if col not in pivot.columns:
            pivot[col] = 0

    pivot = pivot.reindex(full_index, fill_value=0)
    pivot.index.name = "period"
    df = pivot.reset_index()

    df["total_reviewed"] = df["Filed"] + df["Not Filed"]
    df["file_rate"] = (
        (df["Filed"] / df["total_reviewed"])
        .where(df["total_reviewed"] > 0, other=0.0)
        .round(3)
    )
    df["period"] = df["period"].astype(str)
    return df


def _build_file_rate_line(df: pd.DataFrame) -> alt.Chart:
    hover = alt.selection_point(nearest=True, on="mouseover", fields=["period"], empty=False)
    tooltips = [
        alt.Tooltip("period:O",          title="Period"),
        alt.Tooltip("Filed:Q",           title="Cases Filed",      format=","),
        alt.Tooltip("Not Filed:Q",       title="Cases Not Filed",  format=","),
        alt.Tooltip("total_reviewed:Q",  title="Total Reviewed",   format=","),
        alt.Tooltip("file_rate:Q",       title="Filing Rate",      format=".1%"),
    ]
    base = alt.Chart(df).encode(
        x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("file_rate:Q", title="Filing Rate",
                axis=alt.Axis(format=".0%"), scale=alt.Scale(domain=[0, 1])),
        tooltip=tooltips,
    )
    line = base.mark_line(color=_FLD_COLOR, strokeWidth=2, interpolate="monotone")
    points = (
        base.mark_point(color=_FLD_COLOR, filled=True, size=80)
        .encode(opacity=alt.condition(hover, alt.value(1), alt.value(0)))
        .add_params(hover)
    )
    rule = (
        base.mark_rule(strokeWidth=1)
        .encode(x="period:O", opacity=alt.condition(hover, alt.value(0.3), alt.value(0)))
    )
    return (rule + line + points).properties(width="container")


def render_file_rate(fld: pd.DataFrame, ntfld: pd.DataFrame) -> None:
    df = _prepare_file_rate(fld, ntfld)
    with st.container(border=True):
        st.header(":material/percent: Filing Rate")
        st.altair_chart(_build_file_rate_line(df), use_container_width=True)


# --- render_decision_time ---

def _prepare_decision_time(fld: pd.DataFrame, ntfld: pd.DataFrame) -> pd.DataFrame:
    fld = fld.copy()
    fld["days_to_decision"] = (
        pd.to_datetime(fld["earliest_fld_date"]) - pd.to_datetime(fld["ref_date"])
    ).dt.days
    fld["outcome"] = "Filed"

    ntfld = ntfld.copy()
    ntfld = ntfld.loc[ntfld["min_ntfld_rank"] != 3]  # exclude PFI
    ntfld["days_to_decision"] = (
        pd.to_datetime(ntfld["earliest_ntfld_date"]) - pd.to_datetime(ntfld["ref_date"])
    ).dt.days
    ntfld["outcome"] = "Not Filed"

    combined = pd.concat([
        fld[["period", "outcome", "days_to_decision"]],
        ntfld[["period", "outcome", "days_to_decision"]],
    ], ignore_index=True)
    combined = combined.loc[combined["days_to_decision"] >= 0]

    chart_df = (
        combined.groupby(["period", "outcome"])["days_to_decision"]
        .agg(median_days="median", mean_days="mean")
        .reset_index()
        .assign(
            median_days=lambda df: df["median_days"].round(1),
            mean_days=lambda df: df["mean_days"].round(1),
            period=lambda df: df["period"].astype(str),
        )
    )

    return chart_df.melt(
        id_vars=["period", "outcome"],
        value_vars=["median_days", "mean_days"],
        var_name="statistic",
        value_name="days",
    ).replace({"median_days": "Median", "mean_days": "Mean"})


def _build_decision_time_line(df: pd.DataFrame) -> alt.Chart:
    selection = alt.selection_point(fields=["outcome"], bind="legend")
    hover = alt.selection_point(nearest=True, on="mouseover", fields=["period"], empty=False)

    color_scale = alt.Scale(
        domain=["Filed", "Not Filed"],
        range=[_FLD_COLOR, _NF_COLOR],
    )
    dash_scale = alt.Scale(
        domain=["Median", "Mean"],
        range=[[1, 0], [6, 4]],
    )

    tooltips = [
        alt.Tooltip("period:O",    title="Period"),
        alt.Tooltip("outcome:N",   title="Outcome"),
        alt.Tooltip("statistic:N", title="Statistic"),
        alt.Tooltip("days:Q",      title="Days", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("days:Q", title="Days from Referral to Decision"),
        color=alt.Color("outcome:N", title="Outcome", scale=color_scale),
        strokeDash=alt.StrokeDash("statistic:N", title="Statistic", scale=dash_scale),
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


def render_decision_time(fld: pd.DataFrame, ntfld: pd.DataFrame) -> None:
    df = _prepare_decision_time(fld, ntfld)
    with st.container(border=True):
        st.header(":material/timer: Duration of Case Review")
        st.altair_chart(_build_decision_time_line(df), use_container_width=True)
