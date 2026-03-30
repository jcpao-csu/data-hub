# stats/ntfld_refiled.py
# Not-filed cases that were subsequently filed with the court.
# Uses the filtered ntfld (cases declined within the selected period) joined
# against all-time unfiltered fld to determine if a case was ever re-filed.
#
# Visualizations:
#   - Stacked bar (count + normalized) — Eventually Filed vs Stayed Not Filed by period
#   - Line chart — re-filing rate (%) by period
#   - Horizontal bar — re-filing rate by not-filed reason (min_ntfld_category)

import altair as alt
import pandas as pd
import streamlit as st

_FILED_COLOR   = "#3db87a"
_NTFLD_COLOR   = "#78909c"
_STATUS_ORDER  = ["Eventually Filed", "Stayed Not Filed"]
_STATUS_COLORS = [_FILED_COLOR, _NTFLD_COLOR]


def _prepare_ntfld_refiled(
    ntfld: pd.DataFrame, fld_all: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Mark each not-filed case as eventually filed or not, then group by period.
    Returns (melted_df for stacked bar, wide_df for line chart).
    """
    filed_ids = set(fld_all["pbk_num"].dropna())
    df = ntfld.copy()
    df["eventually_filed"] = df["pbk_num"].isin(filed_ids)

    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    wide = (
        df.groupby(["period", "eventually_filed"])["pbk_num"]
        .nunique()
        .unstack(fill_value=0)
        .reindex(full_index, fill_value=0)
    )
    wide.index.name = "period"
    wide = wide.reset_index()

    for col in [True, False]:
        if col not in wide.columns:
            wide[col] = 0

    wide = wide.rename(columns={True: "Eventually Filed", False: "Stayed Not Filed"})
    wide["total"] = wide["Eventually Filed"] + wide["Stayed Not Filed"]
    wide["pct_refiled"] = (
        (wide["Eventually Filed"] / wide["total"] * 100)
        .where(wide["total"] > 0, other=0.0)
        .round(1)
    )
    wide["period"] = wide["period"].astype(str)

    melted = wide.melt(
        id_vars=["period", "total", "pct_refiled"],
        value_vars=["Eventually Filed", "Stayed Not Filed"],
        var_name="Status",
        value_name="cases",
    )
    melted["pct"] = (
        (melted["cases"] / melted["total"] * 100)
        .where(melted["total"] > 0, other=0.0)
        .round(1)
    )
    return melted, wide


def _prepare_ntfld_refiled_by_reason(
    ntfld: pd.DataFrame, fld_all: pd.DataFrame
) -> pd.DataFrame:
    """
    Group not-filed cases by min_ntfld_category × eventually_filed.
    Returns a wide DataFrame with re-filing rate per reason.
    """
    filed_ids = set(fld_all["pbk_num"].dropna())
    df = ntfld.dropna(subset=["min_ntfld_category"]).copy()
    df["eventually_filed"] = df["pbk_num"].isin(filed_ids)

    wide = (
        df.groupby(["min_ntfld_category", "eventually_filed"])["pbk_num"]
        .nunique()
        .unstack(fill_value=0)
        .reset_index()
    )
    for col in [True, False]:
        if col not in wide.columns:
            wide[col] = 0

    wide = wide.rename(columns={
        "min_ntfld_category": "Reason",
        True:  "Eventually Filed",
        False: "Stayed Not Filed",
    })
    wide["total"] = wide["Eventually Filed"] + wide["Stayed Not Filed"]
    wide["pct_refiled"] = (
        (wide["Eventually Filed"] / wide["total"] * 100)
        .where(wide["total"] > 0, other=0.0)
        .round(1)
    )
    return wide


def _build_refiled_bar(df: pd.DataFrame, is_normalized: bool) -> alt.Chart:
    """Stacked bar — eventually filed vs stayed not filed by period."""
    sel = alt.selection_point(fields=["Status"], bind="legend")

    y_enc = (
        alt.Y(
            "cases:Q",
            stack="normalize",
            axis=alt.Axis(format=".0%", title="Share of Not-Filed Cases"),
        )
        if is_normalized
        else alt.Y("cases:Q", stack="zero", title="Cases Not Filed")
    )

    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
            y=y_enc,
            color=alt.Color(
                "Status:N",
                title="Status",
                sort=_STATUS_ORDER,
                scale=alt.Scale(domain=_STATUS_ORDER, range=_STATUS_COLORS),
            ),
            opacity=alt.condition(sel, alt.value(1.0), alt.value(0.2)),
            tooltip=[
                alt.Tooltip("period:O",      title="Period"),
                alt.Tooltip("Status:N",      title="Status"),
                alt.Tooltip("cases:Q",       title="Cases",              format=","),
                alt.Tooltip("total:Q",       title="Total Not Filed",    format=","),
                alt.Tooltip("pct:Q",         title="% of Period Total",  format=".1f"),
                alt.Tooltip("pct_refiled:Q", title="% Eventually Filed", format=".1f"),
            ],
        )
        .add_params(sel)
        .properties(width="container")
    )


def _build_refiled_line(df: pd.DataFrame) -> alt.Chart:
    """Line chart — re-filing rate (%) by period, with hover points and rule."""
    hover = alt.selection_point(nearest=True, on="mouseover", fields=["period"], empty=False)

    base = alt.Chart(df).encode(
        x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("pct_refiled:Q", title="% Eventually Filed"),
        tooltip=[
            alt.Tooltip("period:O",           title="Period"),
            alt.Tooltip("pct_refiled:Q",      title="% Eventually Filed", format=".1f"),
            alt.Tooltip("Eventually Filed:Q", title="Cases Re-Filed",     format=","),
            alt.Tooltip("total:Q",            title="Total Not Filed",    format=","),
        ],
    )

    rule = (
        base.mark_rule(strokeWidth=1)
        .encode(opacity=alt.condition(hover, alt.value(0.3), alt.value(0)))
    )
    line = base.mark_line(color=_FILED_COLOR, strokeWidth=2, interpolate="monotone")
    points = (
        base.mark_point(color=_FILED_COLOR, filled=True, size=80)
        .encode(opacity=alt.condition(hover, alt.value(1), alt.value(0)))
        .add_params(hover)
    )
    return (rule + line + points).properties(width="container")


def _build_refiled_by_reason(df: pd.DataFrame) -> alt.Chart:
    """Horizontal bar — re-filing rate by not-filed reason, sorted descending."""
    return (
        alt.Chart(df)
        .mark_bar(color=_FILED_COLOR)
        .encode(
            y=alt.Y("Reason:N", sort="-x", title="Not-Filed Reason"),
            x=alt.X("pct_refiled:Q", title="% Eventually Filed"),
            tooltip=[
                alt.Tooltip("Reason:N",           title="Reason"),
                alt.Tooltip("pct_refiled:Q",      title="% Eventually Filed", format=".1f"),
                alt.Tooltip("Eventually Filed:Q", title="Cases Re-Filed",     format=","),
                alt.Tooltip("total:Q",            title="Total in Category",  format=","),
            ],
        )
        .properties(width="container")
    )


def render_ntfld_refiled(ntfld: pd.DataFrame, fld_all: pd.DataFrame) -> None:
    """Render not-filed cases that were eventually filed."""
    melted, wide = _prepare_ntfld_refiled(ntfld, fld_all)
    reason_df    = _prepare_ntfld_refiled_by_reason(ntfld, fld_all)

    total_refiled = int(wide["Eventually Filed"].sum())
    total_ntfld   = int(wide["total"].sum())
    overall_pct   = round(total_refiled / total_ntfld * 100, 1) if total_ntfld else 0.0

    with st.container(border=True):
        st.header(":material/published_with_changes: Not-Filed Cases Later Filed")
        st.caption(
            "Tracks cases that were initially declined but subsequently filed with the court. "
            "Cases are counted in the period they were first not filed; whether they were ever "
            "filed is checked against all-time filing records (unbounded by the date filter)."
        )

        st.markdown(
            f":green-background[**{total_refiled:,}** of **{total_ntfld:,}** not-filed cases "
            f"(**{overall_pct:.1f}%**) were eventually filed during the selected period.]"
        )
        st.write(" ")

        tab_count, tab_pct, tab_rate = st.tabs(["Count", "Normalized (%)", "Rate (%)"])
        with tab_count:
            st.altair_chart(_build_refiled_bar(melted, is_normalized=False), width="container")
        with tab_pct:
            st.altair_chart(_build_refiled_bar(melted, is_normalized=True), width="container")
        with tab_rate:
            st.altair_chart(_build_refiled_line(wide), width="container")

        st.divider()
        st.subheader("Re-Filing Rate by Reason")
        st.caption(
            "Of cases not filed for each reason, what share were later filed with the court? "
            "Sorted so the highest re-filing rates appear at the top."
        )
        st.altair_chart(_build_refiled_by_reason(reason_df), width="container")
