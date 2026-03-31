# overview.py
# JCPAO Dashboard — Overview Page
#
# Displays YTD metrics, cases by year, and cases by referring agency.
# All charts respond to sidebar filters via session state.

import altair as alt
import pandas as pd
import streamlit as st

from session_state import get_filtered_data, render_sidebar
from dashboard_stats import post_last_updated
from read_data import RCVD  # only used for "last updated" timestamp

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.markdown("<h1 style='text-align: center;'>JCPAO Dashboard Overview</h1>", unsafe_allow_html=True)
st.divider()

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**JCPAO Dashboard Overview**")
    st.write(
        f"Welcome to the JCPAO Dashboard! Results based on system data as of "
        f"{post_last_updated(RCVD)}."
    )
    st.divider()
    render_sidebar()

# ---------------------------------------------------------------------------
# Load filtered data
# ---------------------------------------------------------------------------

rcvd, fld, ntfld, disp = get_filtered_data()

# ---------------------------------------------------------------------------
# YTD Metrics
# ---------------------------------------------------------------------------

def _ytd_counts(df: pd.DataFrame, date_col: str) -> list[int]:
    """
    For each year in the data, count cases up to today's month/day.
    Returns a list of annual YTD counts ordered by year (used as sparkline).
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])

    today = pd.Timestamp.today()
    mask = (
        (df[date_col].dt.month < today.month) |
        (
            (df[date_col].dt.month == today.month) &
            (df[date_col].dt.day <= today.day)
        )
    )
    df = df[mask].copy()
    df["year"] = df[date_col].dt.year

    annual = (
        df.groupby("year")["pbk_num"]
        .nunique()
        .sort_index()
    )
    return annual.tolist()


def render_ytd_metric(
    df: pd.DataFrame,
    date_col: str,
    label: str,
    chart_type: str,
    delta_color: str = "normal",
) -> None:
    counts = _ytd_counts(df, date_col)

    if len(counts) < 2:
        st.metric(label=label, value=f"{counts[-1] if counts else 0} cases")
        return

    delta     = counts[-1] - counts[-2]
    delta_pct = (
        f"{(delta / counts[-2] * 100):+.1f}%"
        if counts[-2] != 0 else "N/A"
    )

    st.metric(
        label=label,
        value=f"{counts[-1]:,} cases",
        delta=f"{delta:+,} (YoY) | {delta_pct}",
        delta_color=delta_color,
        height=185,
        chart_data=counts,
        chart_type=chart_type,
        border=True,
    )


st.markdown(
    "<h4 style='text-align: center;'>Criminal Cases Processed Year-to-Date</h4>",
    unsafe_allow_html=True,
)
st.write(" ")

with st.container():
    rcvd_col, fld_col, ntfld_col, disp_col = st.columns(4)

    with rcvd_col:
        render_ytd_metric(rcvd,  "ref_date",            "***Total Received (YTD)***",  "area")
    with fld_col:
        render_ytd_metric(fld,   "earliest_fld_date",   "***Total Filed (YTD)***",     "area")
    with ntfld_col:
        render_ytd_metric(ntfld, "earliest_ntfld_date", "***Total Not Filed (YTD)***", "area", delta_color="inverse")
    with disp_col:
        render_ytd_metric(disp,  "earliest_disp_date",  "***Total Disposed (YTD)***",  "area")

st.write(" ")

# ---------------------------------------------------------------------------
# Cases by Year and Status
# ---------------------------------------------------------------------------

def _build_by_year(
    rcvd: pd.DataFrame,
    fld: pd.DataFrame,
    ntfld: pd.DataFrame,
    disp: pd.DataFrame,
) -> pd.DataFrame:

    today = pd.Timestamp.today()

    def _prep(df: pd.DataFrame, date_col: str, status: str) -> pd.DataFrame:
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df["Year"] = df[date_col].dt.year
        out = df.groupby("Year")["pbk_num"].nunique().reset_index(name="Total Cases")
        out["Case Status"] = status
        out["Year"] = out["Year"].apply(
            lambda y: f"{today.year} YTD" if y == today.year else str(y)
        )
        return out

    df = pd.concat([
        _prep(rcvd,  "ref_date",            "Received"),
        _prep(fld,   "earliest_fld_date",   "Filed"),
        _prep(ntfld, "earliest_ntfld_date", "Not Filed"),
        _prep(disp,  "earliest_disp_date",  "Disposed"),
    ], ignore_index=True)

    status_order = ["Received", "Filed", "Not Filed", "Disposed"]
    df["Case Status"] = pd.Categorical(df["Case Status"], categories=status_order, ordered=True)

    return df


_STATUS_ORDER  = ["Received", "Filed", "Not Filed", "Disposed"]
_STATUS_COLORS = ["#4da6ff", "#3db87a", "#e05c5c", "#9b72e6"]

by_year_df = _build_by_year(rcvd, fld, ntfld, disp)

year_chart = (
    alt.Chart(by_year_df)
    .mark_bar()
    .encode(
        x=alt.X("Year:O", title="Year"),
        y=alt.Y("Total Cases:Q", title="Case Volume"),
        color=alt.Color(
            "Case Status:N",
            sort=_STATUS_ORDER,
            scale=alt.Scale(domain=_STATUS_ORDER, range=_STATUS_COLORS),
        ),
        xOffset=alt.XOffset("Case Status:N", sort=_STATUS_ORDER),
        tooltip=[
            alt.Tooltip("Year:O",         title="Year"),
            alt.Tooltip("Case Status:N",  title="Status"),
            alt.Tooltip("Total Cases:Q",  title="Cases", format=","),
        ],
    )
    .properties(
        title=alt.TitleParams(
            text="Cases Processed by Year and Status",
            anchor="middle",
            fontSize=18,
            fontWeight="bold",
        ),
        # width="stretch",
    )
)

st.altair_chart(year_chart)

# ---------------------------------------------------------------------------
# Cases by Referring Agency (Top 10, current year YTD)
# ---------------------------------------------------------------------------

def _build_by_agency(
    rcvd: pd.DataFrame,
    fld: pd.DataFrame,
    ntfld: pd.DataFrame,
    disp: pd.DataFrame,
) -> pd.DataFrame:

    today = pd.Timestamp.today()

    def _prep(df: pd.DataFrame, date_col: str, status: str) -> pd.DataFrame:
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df["Year"] = df[date_col].dt.year
        out = (
            df.groupby(["Year", "agency_name"])["pbk_num"]
            .nunique()
            .reset_index(name="Total Cases")
        )
        out["Case Status"] = status
        out["Year"] = out["Year"].apply(
            lambda y: f"{today.year} YTD" if y == today.year else str(y)
        )
        return out

    df = pd.concat([
        _prep(rcvd,  "ref_date",            "Received"),
        _prep(fld,   "earliest_fld_date",   "Filed"),
        _prep(ntfld, "earliest_ntfld_date", "Not Filed"),
        _prep(disp,  "earliest_disp_date",  "Disposed"),
    ], ignore_index=True)

    status_order = ["Received", "Filed", "Not Filed", "Disposed"]
    df["Case Status"] = pd.Categorical(df["Case Status"], categories=status_order, ordered=True)

    # Limit to current year YTD
    df = df[df["Year"] == f"{today.year} YTD"]

    return df


agency_df = _build_by_agency(rcvd, fld, ntfld, disp)

top_10 = (
    agency_df.groupby("agency_name", as_index=False)["Total Cases"]
    .sum()
    .sort_values("Total Cases", ascending=False)
    .head(10)
)
agency_df_top10 = agency_df[agency_df["agency_name"].isin(top_10["agency_name"])]

agency_chart = (
    alt.Chart(agency_df_top10)
    .mark_bar()
    .encode(
        y=alt.Y(
            "agency_name:O",
            title="Police Agency",
            sort=top_10["agency_name"].tolist(),
        ),
        x=alt.X("Total Cases:Q", title="Case Volume"),
        color=alt.Color(
            "Case Status:N",
            sort=_STATUS_ORDER,
            scale=alt.Scale(domain=_STATUS_ORDER, range=_STATUS_COLORS),
        ),
        yOffset=alt.YOffset("Case Status:N", sort=_STATUS_ORDER),
        tooltip=[
            alt.Tooltip("agency_name:N", title="Agency"),
            alt.Tooltip("Case Status:N", title="Status"),
            alt.Tooltip("Total Cases:Q", title="Cases", format=","),
        ],
    )
    .properties(
        title=alt.TitleParams(
            text=f"Top 10 Referring Agencies by Case Volume (YTD)",
            anchor="middle",
            fontSize=18,
            fontWeight="bold",
        ),
        # width="stretch",
    )
)

st.altair_chart(agency_chart)

# ---------------------------------------------------------------------------
# Filing rate formula
# ---------------------------------------------------------------------------

st.markdown(r"""
$$
\text{Case Filing Rate (\%)} \;=\;
\frac{\text{Total Cases Filed}}{\text{Total Cases Completed Review}}
$$
""")