# stats/special_laws.py
# Shared cumulative referral chart for Blair's Law and Valentine's Law.
# Both laws took effect on the same date (August 28, 2024).
#
# Public API:
#   render_law_volume(rcvd_law, fld_law, ntfld_law, disp_law, law_name)
#     All DataFrames should be unfiltered by sidebar date range but pre-filtered
#     to the relevant law boolean column (e.g. RCVD_BL, FLD_BL, ...).

import altair as alt
import pandas as pd
import streamlit as st

_LAW_DATE = pd.Timestamp("2024-08-28")  # effective date for both laws

_STATUS_ORDER  = ["Received", "Filed", "Not Filed", "Disposed"]
_STATUS_COLORS = ["#4da6ff", "#3db87a", "#e05c5c", "#9b72e6"]
_RULE_COLOR    = "#50c8c6"  # teal — effective-date marker
_MUTED         = "#6b7a99"


def _cumulative_series(
    df: pd.DataFrame,
    date_col: str,
    id_col: str = "pbk_num",
) -> pd.Series:
    """
    Build a daily cumulative count from _LAW_DATE to today for one status.
    Returns a Series indexed by date.
    """
    s = df[[id_col, date_col]].drop_duplicates(id_col).copy()
    s["date"] = pd.to_datetime(s[date_col], errors="coerce").dt.normalize()
    s = s.dropna(subset=["date"])

    daily = (
        s[s["date"] >= _LAW_DATE]
        .groupby("date")[id_col]
        .nunique()
        .sort_index()
    )

    full_idx = pd.date_range(
        start=_LAW_DATE,
        end=pd.Timestamp.now().normalize(),
        freq="D",
    )
    return daily.reindex(full_idx, fill_value=0).cumsum()


def _prepare_law_cumulative(
    rcvd_law: pd.DataFrame,
    fld_law: pd.DataFrame,
    ntfld_law: pd.DataFrame,
    disp_law: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    """
    Long-format DataFrame with columns: date, cumulative_cases, status.
    Not Filed excludes cases whose pbk_num also appears in fld_law (PFI→filed).
    """
    fld_ids      = set(fld_law["pbk_num"])
    ntfld_true   = ntfld_law[~ntfld_law["pbk_num"].isin(fld_ids)]

    series = {
        "Received" : _cumulative_series(rcvd_law,  "ref_date"),
        "Filed"    : _cumulative_series(fld_law,   "earliest_fld_date"),
        "Not Filed": _cumulative_series(ntfld_true, "earliest_ntfld_date"),
        "Disposed" : _cumulative_series(disp_law,  "earliest_disp_date"),
    }

    display_start = max(start, _LAW_DATE)

    frames = []
    for status, s in series.items():
        df = s.reset_index()
        df.columns = ["date", "cumulative_cases"]
        df["status"] = status
        df = df[(df["date"] >= display_start) & (df["date"] <= end)]
        frames.append(df)

    return pd.concat(frames, ignore_index=True)


def _build_law_cumulative_chart(df: pd.DataFrame, law_name: str) -> alt.Chart:
    legend_sel = alt.selection_point(fields=["status"], bind="legend")
    hover      = alt.selection_point(nearest=True, on="mouseover", fields=["date"], empty=False)
    color_scale = alt.Scale(domain=_STATUS_ORDER, range=_STATUS_COLORS)

    base = alt.Chart(df).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(tickCount="month", format="%b %Y")),
        y=alt.Y("cumulative_cases:Q", title="Cumulative Cases"),
        color=alt.Color("status:N", scale=color_scale, legend=alt.Legend(title="Status")),
        opacity=alt.condition(legend_sel, alt.value(1), alt.value(0.1)),
        tooltip=[
            alt.Tooltip("date:T",             title="Date",            format="%b %-d, %Y"),
            alt.Tooltip("status:N",           title="Status"),
            alt.Tooltip("cumulative_cases:Q", title="Cumulative Cases", format=","),
        ],
    ).add_params(legend_sel)

    line   = base.mark_line(strokeWidth=2, interpolate="monotone")
    points = (
        base.mark_point(filled=True, size=60)
        .encode(opacity=alt.condition(hover, alt.value(1), alt.value(0)))
        .add_params(hover)
    )

    law_date_df = pd.DataFrame({"date": [_LAW_DATE]})
    law_rule = (
        alt.Chart(law_date_df)
        .mark_rule(color=_RULE_COLOR, strokeWidth=1.5, strokeDash=[5, 3])
        .encode(x=alt.X("date:T"))
    )
    law_label = (
        alt.Chart(law_date_df)
        .mark_text(align="left", dx=4, fontSize=11, fontWeight="bold",
                   color=_RULE_COLOR, opacity=0.85)
        .encode(
            x=alt.X("date:T"),
            y=alt.value(14),
            text=alt.value("Law effective Aug 28, 2024"),
        )
    )

    return (line + points + law_rule + law_label).properties(
        title=alt.TitleParams(
            f"{law_name} — Cumulative Cases",
            subtitle=f"Total cases with a {law_name} charge since the law took effect",
            anchor="start",
            subtitleColor="#e8edf2",
        ),
        height=400,
    )


def render_law_volume(
    rcvd_law: pd.DataFrame,
    fld_law: pd.DataFrame,
    ntfld_law: pd.DataFrame,
    disp_law: pd.DataFrame,
    law_name: str,
) -> None:
    """
    Render the cumulative cases chart for a single special law.

    All DataFrames should be unfiltered by sidebar date range but pre-filtered
    to the relevant law boolean column. Not Filed excludes cases that were
    eventually filed (pbk_num present in fld_law).
    """
    today = pd.Timestamp.now().normalize()
    df    = _prepare_law_cumulative(rcvd_law, fld_law, ntfld_law, disp_law, _LAW_DATE, today)

    if df.empty:
        st.info(f"No {law_name} cases found.", icon="ℹ️")
        return

    st.altair_chart(_build_law_cumulative_chart(df, law_name), width="stretch")
