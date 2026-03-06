# recidivism.py
# JCPAO Dashboard — Recidivism / re-referral metrics
#
# USAGE:
#   from recidivism import render_recidivism
#   from session_state import get_filtered_data
#
#   rcvd_full, _, _, _ = get_filtered_data(apply_filters=False)  # unfiltered
#   rcvd, _, _, _      = get_filtered_data()                     # filtered
#   render_recidivism(rcvd, rcvd_full)

import numpy as np
import altair as alt
import pandas as pd
import streamlit as st

from read_data import RCVD
from session_state import get_filtered_data, MSHP_CODES

# Load filtered data (see session_state.py)
rcvd, fld, ntfld, disp = get_filtered_data()

# ---------------------------------------------------------------------------
# Core prep — run on FULL dataset to get accurate first-seen dates
# ---------------------------------------------------------------------------

def _compute_first_seen(rcvd_full: pd.DataFrame) -> pd.DataFrame:
    """
    Using the full unfiltered dataset, compute each defendant's
    first-ever referral date. This ensures defendants referred before
    the current filter window are still correctly flagged as prior.

    Returns a df with columns: pbk_def_num, first_ref_date
    """
    df = rcvd_full.copy()

    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")

    # Drop rows with blank/null defendant ID
    df = df.loc[df["pbk_def_num"].notna() & (df["pbk_def_num"].astype(str).str.strip() != "")]

    # Sort by ref_date, then case number (pbk_num) as tiebreaker
    df = df.sort_values(["ref_date", "pbk_num"], ascending=[True, True])

    # First appearance per defendant across entire history
    first_seen = (
        df.drop_duplicates(subset=["pbk_def_num"], keep="first")[["pbk_def_num", "ref_date"]]
        .rename(columns={"ref_date": "first_ref_date"})
    )

    return first_seen


def _prepare(rcvd: pd.DataFrame, rcvd_full: pd.DataFrame) -> pd.DataFrame:
    """
    Merge first-seen dates onto the filtered dataset and flag each
    case as new or prior referral.
    """
    df = rcvd.copy()

    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")

    # Drop blank defendant IDs
    df = df.loc[df["pbk_def_num"].notna() & (df["pbk_def_num"].astype(str).str.strip() != "")]

    # Sort filtered df
    df = df.sort_values(["ref_date", "pbk_num"], ascending=[True, True])

    # Merge in first-seen dates from full history
    first_seen = _compute_first_seen(rcvd_full)
    df = df.merge(first_seen, on="pbk_def_num", how="left")

    # Flag: if this referral IS the first-ever referral, it's new
    df["referral_type"] = np.where(
        df["ref_date"] == df["first_ref_date"],
        "New Defendant",
        "Prior Referral",
    )

    return df


# ---------------------------------------------------------------------------
# Chart 1 — New vs. Prior Referral Rate by Period
# ---------------------------------------------------------------------------

def _build_referral_type_chart(df: pd.DataFrame, is_normalized: bool) -> alt.Chart:
    type_order  = ["New Defendant", "Prior Referral"]
    type_colors = ["#4da6ff", "#e05c5c"]

    total_per_period = (
        df.groupby("period")["pbk_num"]
        .nunique()
        .rename("period_total")
    )

    chart_df = (
        df.groupby(["period", "referral_type"])["pbk_num"]
        .nunique()
        .reset_index(name="count")
        .assign(period=lambda d: d["period"].astype(str))
    )

    chart_df = chart_df.merge(
        total_per_period.reset_index().assign(period=lambda d: d["period"].astype(str)),
        on="period",
    )
    chart_df["pct"] = (chart_df["count"] / chart_df["period_total"]).round(3)

    return (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("period:O", title="Period", sort=None),
            y=alt.Y(
                "count:Q",
                title="Share of Cases" if is_normalized else "Cases Referred",
                stack="normalize" if is_normalized else "zero",
                axis=alt.Axis(format=".0%") if is_normalized else alt.Axis(),
            ),
            color=alt.Color(
                "referral_type:N",
                title="Defendant Type",
                scale=alt.Scale(domain=type_order, range=type_colors),
                sort=type_order,
            ),
            order=alt.Order("color_referral_type_sort_index:Q"),
            tooltip=[
                alt.Tooltip("period:O",         title="Period"),
                alt.Tooltip("referral_type:N",  title="Defendant Type"),
                alt.Tooltip("count:Q",          title="Cases"),
                alt.Tooltip("period_total:Q",   title="Total Cases in Period"),
                alt.Tooltip("pct:Q",            title="% of Period", format=".1%"),
            ],
        )
        .properties(
            title="New vs. Previously Referred Defendants by Period"
                  + (" (Normalized)" if is_normalized else ""),
            width="container",
        )
    )


# ---------------------------------------------------------------------------
# Chart 2 — Recurrence Count Distribution
# ---------------------------------------------------------------------------

def _build_recurrence_chart(rcvd_full: pd.DataFrame) -> alt.Chart:
    """
    Across the full dataset, how many defendants appeared exactly
    once, twice, three times, etc.?
    """
    df = rcvd_full.copy()
    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")
    df = df.loc[df["pbk_def_num"].notna() & (df["pbk_def_num"].astype(str).str.strip() != "")]
    df = df.drop_duplicates(subset=["pbk_num"])

    # Count referrals per defendant
    referral_counts = (
        df.groupby("pbk_def_num")["pbk_num"]
        .nunique()
        .reset_index(name="n_referrals")
    )

    # Cap display at 6+ to avoid long tail cluttering the chart
    referral_counts["n_referrals_label"] = referral_counts["n_referrals"].apply(
        lambda x: "6+" if x >= 6 else str(x)
    )

    label_order = ["1", "2", "3", "4", "5", "6+"]

    dist = (
        referral_counts.groupby("n_referrals_label")["pbk_def_num"]
        .nunique()
        .reindex(label_order, fill_value=0)
        .reset_index(name="n_defendants")
    )

    total_defs = dist["n_defendants"].sum()
    dist["pct"]             = (dist["n_defendants"] / total_defs).round(3)
    dist["pct_label"]       = (dist["pct"] * 100).round(1).astype(str) + "%"
    dist["n_defendants_fmt"] = dist["n_defendants"].apply(lambda x: f"{x:,}")

    return (
        alt.Chart(dist)
        .mark_bar(color="#4da6ff", opacity=0.85, cornerRadius=3)
        .encode(
            x=alt.X(
                "n_referrals_label:O",
                sort=label_order,
                title="Number of Referrals",
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y("n_defendants:Q", title="Number of Defendants"),
            tooltip=[
                alt.Tooltip("n_referrals_label:O", title="Referrals"),
                alt.Tooltip("n_defendants_fmt:N",  title="Defendants"),
                alt.Tooltip("pct_label:N",         title="% of All Defendants"),
            ],
        )
        .properties(
            title=alt.TitleParams(
                text="Referral Frequency Distribution",
                subtitle="How many times has each defendant been referred? (full dataset)",
                fontSize=14,
                subtitleFontSize=11,
                subtitleColor="#777",
                anchor="start",
            ),
            width="container",
            height=300,
        )
        .configure_view(strokeWidth=0)
        .configure_axis(domain=False, grid=False)
    )


# ---------------------------------------------------------------------------
# Chart 3 — Median Days Between First and Second Referral by Year
# ---------------------------------------------------------------------------

def _build_time_between_chart(rcvd_full: pd.DataFrame) -> alt.Chart:
    """
    For defendants with 2+ referrals, compute days between
    their first and second referral, grouped by year of second referral.
    """
    df = rcvd_full.copy()
    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")
    df = df.loc[df["pbk_def_num"].notna() & (df["pbk_def_num"].astype(str).str.strip() != "")]
    df = df.drop_duplicates(subset=["pbk_num"])
    df = df.sort_values(["pbk_def_num", "ref_date", "pbk_num"])

    # Rank each referral per defendant chronologically
    df["referral_rank"] = df.groupby("pbk_def_num").cumcount() + 1

    first  = df.loc[df["referral_rank"] == 1, ["pbk_def_num", "ref_date"]].rename(columns={"ref_date": "date_1"})
    second = df.loc[df["referral_rank"] == 2, ["pbk_def_num", "ref_date"]].rename(columns={"ref_date": "date_2"})

    gap_df = first.merge(second, on="pbk_def_num")
    gap_df["days_between"] = (gap_df["date_2"] - gap_df["date_1"]).dt.days
    gap_df["year"]         = gap_df["date_2"].dt.year

    agg = (
        gap_df.groupby("year")["days_between"]
        .agg(median_days="median", mean_days="mean", n="count")
        .reset_index()
    )
    agg["median_days"] = agg["median_days"].round(0).astype(int)
    agg["mean_days"]   = agg["mean_days"].round(0).astype(int)
    agg["year"]        = agg["year"].astype(str)

    # Melt for dual-line chart
    melted = agg.melt(
        id_vars=["year", "n"],
        value_vars=["median_days", "mean_days"],
        var_name="statistic",
        value_name="days",
    )
    melted["statistic"] = melted["statistic"].map({
        "median_days": "Median",
        "mean_days":   "Mean",
    })

    return (
        alt.Chart(melted)
        .mark_line(point=True)
        .encode(
            x=alt.X("year:O", title="Year of Second Referral", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("days:Q", title="Days Between 1st and 2nd Referral"),
            color=alt.Color(
                "statistic:N",
                title=None,
                scale=alt.Scale(
                    domain=["Median", "Mean"],
                    range=["#4da6ff", "#f28e2b"],
                ),
            ),
            strokeDash=alt.StrokeDash(
                "statistic:N",
                scale=alt.Scale(
                    domain=["Median", "Mean"],
                    range=[[1, 0], [4, 2]],
                ),
            ),
            tooltip=[
                alt.Tooltip("year:O",      title="Year"),
                alt.Tooltip("statistic:N", title="Statistic"),
                alt.Tooltip("days:Q",      title="Days"),
                alt.Tooltip("n:Q",         title="Defendants"),
            ],
        )
        .properties(
            title=alt.TitleParams(
                text="Time Between First and Second Referral",
                subtitle="Median and mean days, by year of second referral (full dataset)",
                fontSize=14,
                subtitleFontSize=11,
                subtitleColor="#777",
                anchor="start",
            ),
            width="container",
            height=300,
        )
        .configure_view(strokeWidth=0)
        .configure_axis(domain=False, grid=False)
    )


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_recidivism(
    rcvd: pd.DataFrame = rcvd,       # filtered via session state
    rcvd_full: pd.DataFrame = RCVD,  # full unfiltered dataset
) -> None:
    """
    Render recidivism / re-referral metrics section.

    rcvd      — responds to sidebar filters (date range, agency, charge cat, etc.)
    rcvd_full — the raw unfiltered table, used for first-seen date computation
                and full-history charts (recurrence dist, time between referrals)
    """
    df = _prepare(rcvd, rcvd_full)

    if df.empty:
        st.info("No valid defendant data available for the current filters.")
        return

    st.header("🔁 Re-Referral Activity")
    st.caption(
        "Tracks defendants referred to this office more than once. "
        "'Prior Referral' indicates the defendant had at least one case "
        "referred before the current period — based on full case history "
        "dating back to 2016."
    )

    # --- Chart 1: New vs Prior by period ---
    view = st.segmented_control(
        label=None,
        options=["Count", "Normalized (%)"],
        default="Count",
        selection_mode="single",
    )
    is_normalized = view == "Normalized (%)"
    st.altair_chart(
        _build_referral_type_chart(df, is_normalized),
        use_container_width=True,
    )

    st.divider()

    # --- Charts 2 & 3 side by side ---
    col1, col2 = st.columns(2)

    with col1:
        st.altair_chart(
            _build_recurrence_chart(rcvd_full),
            use_container_width=True,
        )

    with col2:
        st.altair_chart(
            _build_time_between_chart(rcvd_full),
            use_container_width=True,
        )

render_recidivism()