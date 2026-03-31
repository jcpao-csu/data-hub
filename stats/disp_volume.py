# stats/disp_volume.py
# Visualizations for cases disposed:
#   - render_disp_volume   : total cases disposed by period (bar + line)
#   - render_case_life     : median & mean days from referral to disposition

import altair as alt
import pandas as pd
import streamlit as st

_COLOR = "#e05c5c"  # red


def _prepare_disp_volume(disp: pd.DataFrame) -> pd.DataFrame:
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    counts = (
        disp.groupby("period")["pbk_num"]
        .nunique()
        .reindex(full_index, fill_value=0)
    )
    counts.index.name = "period"
    counts = counts.reset_index().rename(columns={"pbk_num": "total_cases"})
    counts["period"] = counts["period"].astype(str)
    return counts


def _build_disp_volume_bar(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(color=_COLOR)
        .encode(
            x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("total_cases:Q", title="Cases Disposed"),
            tooltip=[
                alt.Tooltip("period:O",       title="Period"),
                alt.Tooltip("total_cases:Q",  title="Cases Disposed", format=","),
            ],
        )
        .properties(width="container")
    )


def _build_disp_volume_line(df: pd.DataFrame) -> alt.Chart:
    hover = alt.selection_point(nearest=True, on="mouseover", fields=["period"], empty=False)
    tooltips = [
        alt.Tooltip("period:O",       title="Period"),
        alt.Tooltip("total_cases:Q",  title="Cases Disposed", format=","),
    ]
    base = alt.Chart(df).encode(
        x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("total_cases:Q", title="Cases Disposed"),
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


def render_disp_volume(disp: pd.DataFrame) -> None:
    df = _prepare_disp_volume(disp)
    with st.container(border=True):
        st.header(":material/check_circle: Cases Disposed")
        tab_bar, tab_line = st.tabs(["Bar Chart", "Line Chart"])
        with tab_bar:
            st.altair_chart(_build_disp_volume_bar(df))
        with tab_line:
            st.altair_chart(_build_disp_volume_line(df))


# --- render_case_life ---

_FLD_COLOR = "#4da6ff"  # blue — filing milestone

_STAGE_ORDER  = ["Referral → Disposition", "Filing → Disposition"]
_STAGE_COLORS = [_COLOR, _FLD_COLOR]


def _prepare_case_life(disp: pd.DataFrame, fld_all: pd.DataFrame) -> pd.DataFrame:
    """
    Compute median and mean days for two durations per period:
      - Referral → Disposition : ref_date to earliest_disp_date (all disposed cases)
      - Filing → Disposition   : earliest_fld_date to earliest_disp_date (filed cases only,
                                  joined from unfiltered fld_all by pbk_num)
    """
    df = disp.copy()
    df["days_ref_to_disp"] = (
        pd.to_datetime(df["earliest_disp_date"]) - pd.to_datetime(df["ref_date"])
    ).dt.days
    df = df.loc[df["days_ref_to_disp"] >= 0]

    # Join filing dates from unfiltered fld
    fld_dates = fld_all[["pbk_num", "earliest_fld_date"]].drop_duplicates("pbk_num")
    df = df.merge(fld_dates, on="pbk_num", how="left")
    df["days_fld_to_disp"] = (
        pd.to_datetime(df["earliest_disp_date"]) - pd.to_datetime(df["earliest_fld_date"])
    ).dt.days

    ref_stats = (
        df.groupby("period")["days_ref_to_disp"]
        .agg(median_days="median", mean_days="mean")
        .reset_index()
        .assign(stage="Referral → Disposition")
    )

    fld_df = df.loc[df["days_fld_to_disp"].notna() & (df["days_fld_to_disp"] >= 0)]
    fld_stats = (
        fld_df.groupby("period")["days_fld_to_disp"]
        .agg(median_days="median", mean_days="mean")
        .reset_index()
        .assign(stage="Filing → Disposition")
    )

    combined = pd.concat([ref_stats, fld_stats], ignore_index=True)
    combined["median_days"] = combined["median_days"].round(1)
    combined["mean_days"]   = combined["mean_days"].round(1)
    combined["period"]      = combined["period"].astype(str)

    melted = combined.melt(
        id_vars=["period", "stage"],
        value_vars=["median_days", "mean_days"],
        var_name="statistic",
        value_name="days",
    ).replace({"median_days": "Median", "mean_days": "Mean"})
    melted["years"] = (melted["days"] / 365.25).round(2)
    return melted


def _build_case_life_line(df: pd.DataFrame) -> alt.Chart:
    selection = alt.selection_point(fields=["stage"], bind="legend")
    hover     = alt.selection_point(nearest=True, on="mouseover", fields=["period"], empty=False)

    color_scale = alt.Scale(domain=_STAGE_ORDER, range=_STAGE_COLORS)
    dash_scale  = alt.Scale(domain=["Median", "Mean"], range=[[1, 0], [6, 4]])

    tooltips = [
        alt.Tooltip("period:O",    title="Period"),
        alt.Tooltip("stage:N",     title="Duration"),
        alt.Tooltip("statistic:N", title="Statistic"),
        alt.Tooltip("days:Q",      title="Days",    format=".1f"),
        alt.Tooltip("years:Q",     title="Years", format=".2f"),
    ]

    base = alt.Chart(df).encode(
        x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("days:Q", title="Days"),
        color=alt.Color("stage:N", title="Duration", scale=color_scale, sort=_STAGE_ORDER),
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


def render_case_life(disp: pd.DataFrame, fld_all: pd.DataFrame) -> None:
    """Render median and mean days for referral-to-disposition and filing-to-disposition."""
    df = _prepare_case_life(disp, fld_all)

    # Compute coverage stats for the Filing → Disposition lines
    total_disp   = disp["pbk_num"].nunique()
    filed_ids    = set(fld_all["pbk_num"].dropna())
    n_with_fld   = disp["pbk_num"].isin(filed_ids).sum()
    n_no_fld     = total_disp - n_with_fld
    pct_excluded = round(n_no_fld / total_disp * 100, 1) if total_disp else 0.0

    with st.container(border=True):
        st.header(":material/hourglass: Case Life Duration")
        # st.caption(
        #     "Median and mean days for two durations — :red[Referral → Disposition] "
        #     "(from when the case was received to final disposition) and "
        #     ":blue[Filing → Disposition] (from when charges were formally filed to "
        #     "final disposition, for cases that were filed). Solid line = Median; "
        #     "dashed line = Mean. Negative durations are excluded."
        # )
        st.info(
            f"**{n_no_fld:,} of {total_disp:,} disposed cases ({pct_excluded:.1f}%) have no "
            f"matching filing record** and are excluded from the Filing → Disposition lines. "
            f"This is most common for cases disposed in early years (e.g. 2016) where the "
            f"corresponding filing predates available data (2016 onward).",
            icon=":material/info:",
        )
        st.altair_chart(_build_case_life_line(df))
