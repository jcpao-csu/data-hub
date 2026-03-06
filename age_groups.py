# age_groups.py
# JCPAO Dashboard — Defendant age group breakdown by period
#
# USAGE:
#   from age_groups import render_age_groups
#   from session_state import get_filtered_data
#
#   rcvd, fld, ntfld, disp = get_filtered_data()
#   render_age_groups(rcvd)

import numpy as np
import altair as alt
import pandas as pd
import streamlit as st

from session_state import get_filtered_data, MSHP_CODES

# Load filtered data (see session_state.py)
rcvd, fld, ntfld, disp = get_filtered_data()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_AGE_GROUPS   = ["Juvenile (< 18)", "Young Adult (18–24)", "Adult (25+)"]
_GROUP_COLORS = ["#e15759", "#f28e2b", "#4e79a7"]

# ---------------------------------------------------------------------------
# Data prep
# ---------------------------------------------------------------------------

def _prepare(rcvd: pd.DataFrame) -> pd.DataFrame:
    df = rcvd[["pbk_num", "period", "ref_date", "def_dob"]].copy()

    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")
    df["def_dob"]  = pd.to_datetime(df["def_dob"],  errors="coerce")
    df = df.dropna(subset=["ref_date", "def_dob"])
    df = df.drop_duplicates(subset=["pbk_num"])

    df["age"] = ((df["ref_date"] - df["def_dob"]).dt.days / 365.25).astype(int)
    df = df.loc[df["age"].between(0, 100)].copy()

    df["age_group"] = np.select(
        condlist=[
            df["age"] < 18,
            df["age"].between(18, 24),
            df["age"] >= 25,
        ],
        choicelist=_AGE_GROUPS,
        default=_AGE_GROUPS[2],
    )

    # Total per period for pct calculation
    total_per_period = (
        df.groupby("period")["pbk_num"]
        .nunique()
        .rename("period_total")
    )

    chart_df = (
        df.groupby(["period", "age_group"])["pbk_num"]
        .nunique()
        .reset_index(name="count")
        .assign(period=lambda d: d["period"].astype(str))
    )

    chart_df = chart_df.merge(
        total_per_period.reset_index().assign(period=lambda d: d["period"].astype(str)),
        on="period",
    )

    chart_df["pct"] = (chart_df["count"] / chart_df["period_total"]).round(3)

    return chart_df


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_age_groups(rcvd: pd.DataFrame = rcvd) -> None:

    chart_df = _prepare(rcvd)

    if chart_df.empty:
        st.info("No valid age data available for the current filters.")
        return

    view = st.segmented_control(
        key="age_group_segmented_control",
        label=None,
        options=["Count", "Normalized (%)"],
        default="Count",
        selection_mode="single",
    )

    is_normalized = view == "Normalized (%)"

    chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("period:O", title="Period", sort=None),
            y=alt.Y(
                "count:Q",
                title="Share of Cases Received" if is_normalized else "Cases Received",
                stack="normalize" if is_normalized else "zero",
                axis=alt.Axis(format=".0%") if is_normalized else alt.Axis(),
            ),
            color=alt.Color(
                "age_group:N",
                title="Age Group",
                scale=alt.Scale(domain=_AGE_GROUPS, range=_GROUP_COLORS),
                sort=_AGE_GROUPS,
            ),
            order=alt.Order("color_age_group_sort_index:Q"),
            tooltip=[
                alt.Tooltip("period:O",       title="Period"),
                alt.Tooltip("age_group:N",    title="Age Group"),
                alt.Tooltip("count:Q",        title="Cases"),
                alt.Tooltip("period_total:Q", title="Total Cases in Period"),
                alt.Tooltip("pct:Q",          title="% of Period", format=".1%"),
            ],
        )
        .properties(
            title="Defendant Age Group by Period" + (" (Normalized)" if is_normalized else ""),
            width="container",
        )
    )

    st.header("🧒 Defendant Age at Time of Referral")
    st.caption("Breakdown of cases by defendant age group at the time of referral to the prosecuting attorney's office.")
    st.altair_chart(chart, use_container_width=True)