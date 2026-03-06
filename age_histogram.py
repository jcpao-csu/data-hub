# age_histogram.py
# JCPAO Dashboard — Histogram of defendant age at time of case referral
#
# USAGE:
#   from age_histogram import render_age_histogram
#   from session_state import get_filtered_data
#
#   rcvd, fld, ntfld, disp = get_filtered_data()
#   render_age_histogram(rcvd)

import altair as alt
import pandas as pd
import streamlit as st

from session_state import get_filtered_data, MSHP_CODES

# Load filtered data (see session_state.py)
rcvd, fld, ntfld, disp = get_filtered_data()

# ---------------------------------------------------------------------------
# Data prep
# ---------------------------------------------------------------------------

def _prepare(rcvd: pd.DataFrame) -> pd.DataFrame:
    """
    Compute defendant age at time of referral.
    Drops rows where either date is null or age computes to negative/implausible.
    """
    df = rcvd[["pbk_num", "ref_date", "def_dob"]].copy()

    # Convert to datetime — handles string input from PostgreSQL
    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")
    df["def_dob"]  = pd.to_datetime(df["def_dob"],  errors="coerce")

    df = df.dropna(subset=["ref_date", "def_dob"])

    # Age in years at referral date
    df["age"] = (
        (df["ref_date"] - df["def_dob"]).dt.days / 365.25
    ).astype(int)

    # Drop implausible ages — under 10 or over 100 likely data anomalies
    df = df.loc[df["age"].between(10, 100)].copy()

    # One row per case
    df = df.drop_duplicates(subset=["pbk_num"])

    return df[["pbk_num", "age"]]


# ---------------------------------------------------------------------------
# Chart builder
# ---------------------------------------------------------------------------

def _build_chart(df: pd.DataFrame, bin_size: int) -> alt.Chart:
    total   = len(df)
    mean_age   = df["age"].mean()
    median_age = df["age"].median()

    # Base histogram
    bars = (
        alt.Chart(df)
        .mark_bar(color="#4e79a7", opacity=0.85)
        .encode(
            x=alt.X(
                "age:Q",
                bin=alt.Bin(step=bin_size),
                title="Age at Referral",
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "count():Q",
                title="Number of Cases",
            ),
            tooltip=[
                alt.Tooltip("age:Q",     title="Age (bin start)", bin=alt.Bin(step=bin_size)),
                alt.Tooltip("count():Q", title="Cases"),
            ],
        )
    )

    # Mean reference line
    mean_rule = (
        alt.Chart(pd.DataFrame({"age": [mean_age]}))
        .mark_rule(color="#e15759", strokeWidth=2, strokeDash=[4, 3])
        .encode(
            x="age:Q",
            tooltip=[alt.Tooltip("age:Q", title="Mean age", format=".1f")],
        )
    )

    # Median reference line
    median_rule = (
        alt.Chart(pd.DataFrame({"age": [median_age]}))
        .mark_rule(color="#f28e2b", strokeWidth=2, strokeDash=[4, 3])
        .encode(
            x="age:Q",
            tooltip=[alt.Tooltip("age:Q", title="Median age", format=".1f")],
        )
    )

    # Legend annotation
    legend_df = pd.DataFrame({
        "age":   [mean_age, median_age],
        "label": [
            f"Mean: {mean_age:.1f}",
            f"Median: {median_age:.1f}",
        ],
        "color": ["#e15759", "#f28e2b"],
    })

    legend_text = (
        alt.Chart(legend_df)
        .mark_text(align="left", fontSize=11, fontWeight="bold", dx=4)
        .encode(
            x=alt.X("age:Q"),
            y=alt.value(12),            # fixed y near top of chart
            text="label:N",
            color=alt.Color(
                "color:N",
                scale=None,             # use literal hex values
            ),
        )
    )

    chart = (
        (bars + mean_rule + median_rule + legend_text)
        .properties(
            width="container",
            height=340,
            title=alt.TitleParams(
                text="Defendant Age at Time of Referral",
                subtitle=f"n = {total:,} cases · ages 10–100 · bin width = {bin_size} yr",
                fontSize=14,
                subtitleFontSize=11,
                subtitleColor="#777",
                anchor="start",
            ),
        )
        .configure_view(strokeWidth=0)
        .configure_axis(domain=False, grid=False)
    )

    return chart


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_age_histogram(rcvd: pd.DataFrame = rcvd) -> None:
    """
    Render a histogram of defendant age at time of case referral,
    with mean and median reference lines and an adjustable bin width.
    """
    df = _prepare(rcvd)

    if df.empty:
        st.info("No valid age data available for the current filters.")
        return

    bin_size = st.select_slider(
        "Bin width (years)",
        options=[1, 2, 5, 10],
        value=5,
        help="Adjust the width of each age bracket.",
    )

    chart = _build_chart(df, bin_size)

    # Output
    st.header("📁 Suspect Age Histogram")
    st.caption("Interactive historgram of suspect age at time of case referral.")
    st.altair_chart(chart, use_container_width=True)