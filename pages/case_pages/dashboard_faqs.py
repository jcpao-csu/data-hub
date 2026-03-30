"""
dashboard_faqs.py
Frequently Asked Questions that are organized into a single space for easier viewability 
"""

import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
from datetime import date

from read_data import get_dataframes
from session_state import get_filtered_data, render_sidebar, MSHP_CODES



RCVD, FLD, NTFLD, DISP, MSHP_CODES, AGENCIES = get_dataframes()

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**Frequently Asked Questions**")
    render_sidebar()

# Load filtered data (after sidebar — see session_state.py)
rcvd, fld, ntfld, disp = get_filtered_data()

st.write("""# :material/forum: Frequently Asked Questions""")
st.caption("Use the dashboard filters and find answers to frequently asked questions about how our Office is prosecuting criminal cases.")
st.divider()




    


# Sankey diagram - status of received cases (fld/ntfld/PFI/under review) -- # / % 


# Total Cases Not Filed

# Total Cases Disposed
# conviction rate = guilty plea or guilty verdict / total cases disposed 
# Disposed Reasons
# Total Cases Convicted (break down into guilty plea, guilty verdict)
# Total Cases to Trial 


# f"Total {charge_type} cases referred from {agency} against {race/sex defendants} from {date_range} to {date_range}, broken down {period}"
# st.caption(f"Total cases received from {date_range[0]} to {date_range[1]}, broken down {_PERIOD_OPTIONS[select_period].tolower()}")

# Build the full period range from the date filter (validation already done by get_filtered_data above)
date_range = st.session_state["date_range_filter"]
freq = st.session_state["period_freq_filter"]
full_index = pd.period_range(start=date_range[0], end=date_range[1], freq=freq)

# Total Cases Received
def cases_rcvd(rcvd: pd.DataFrame = rcvd):

    # Tidy pandas DataFrame — now includes zero-case periods
    chart_df = (
        rcvd.groupby("period")["pbk_num"]
        .nunique() # sum of unique pbk_num (karpel case number)
        .reindex(full_index, fill_value=0) # reindex with full_index
        .reset_index(name="total_cases") # convert index to column
        .rename(columns={"index": "period"})
        .assign(period=lambda df: df["period"].astype(str))
    )

    # Render altair bar chart
    chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("period:O", title="Period", sort=None),
            y=alt.Y("total_cases:Q", title="Total Cases Received"),
            tooltip=["period", "total_cases"],
        )
        # .properties(title="Cases Received by Period", width="container")
    )

    # Output
    st.header("📁 Cases Received")
    st.caption("Cases referred by law enforcement agencies to the prosecuting attorney's office over the selected period.")
    # st.badge() #  # PPI # Justice Counts # Measures for Justice | # View-only 
    # st.divider()
    # st.markdown()
    st.altair_chart(chart, use_container_width=True)
    # st.write_stream("hello...")

# Status of Received cases
def rcvd_cases_status(rcvd: pd.DataFrame = rcvd, fld: pd.DataFrame = fld, ntfld: pd.DataFrame = ntfld):

    # Load lists
    fld_ids  = fld["pbk_num"].unique().tolist()
    pfi_ids  = ntfld.loc[ntfld["min_ntfld_rank"] == 3, "pbk_num"].unique().tolist()
    ntfld_ids = ntfld.loc[ntfld["min_ntfld_rank"] != 3, "pbk_num"].unique().tolist()

    # Add status col to rcvd
    rcvd = rcvd.copy()
    rcvd["current_status"] = np.select(
        [
            rcvd["pbk_num"].isin(fld_ids),
            rcvd["pbk_num"].isin(pfi_ids),
            rcvd["pbk_num"].isin(ntfld_ids),
        ],
        choicelist=["Filed", "Pending Further Investigation", "Not Filed"],
        default="Under Review",
    )

    # Tidy df
    total_per_period = (
        rcvd.groupby("period")["pbk_num"]
        .nunique()
        .rename("period_total")
    )

    chart_df = (
        rcvd.groupby(["period", "current_status"])["pbk_num"]
        .nunique()
        .reset_index(name="count")
        .assign(period=lambda df: df["period"].astype(str))
    )

    chart_df = chart_df.merge(
        total_per_period.reset_index().assign(period=lambda df: df["period"].astype(str)),
        on="period",
    )

    chart_df["pct"] = (chart_df["count"] / chart_df["period_total"]).round(3)

    # Status order and colors
    status_order  = ["Filed", "Pending Further Investigation", "Not Filed", "Under Review"]
    status_colors = ["#2166ac", "#f4a582", "#d6604d", "#bababa"]

    view = st.segmented_control(
        key="rcvd_status_segmented_control",
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
                "current_status:N",
                title="Case Status",
                scale=alt.Scale(domain=status_order, range=status_colors),
                sort=status_order,
            ),
            order=alt.Order("color_current_status_sort_index:Q"),
            tooltip=[
                alt.Tooltip("period:O",         title="Period"),
                alt.Tooltip("current_status:N", title="Status"),
                alt.Tooltip("count:Q",          title="Cases"),
                alt.Tooltip("period_total:Q",   title="Total Cases"),
                alt.Tooltip("pct:Q",            title="% of Period", format=".1%"),
            ],
        )
        .properties(
            title="Status of Cases Received by Period" + (" (Normalized)" if is_normalized else ""),
            width="container",
        )
    )

    # Output
    st.header("📁 Current Status of Cases Received")
    st.caption("Of the cases referred by law enforcement agencies to the prosecuting attorney's office, where along the prosecution process are they?")
    st.altair_chart(chart, use_container_width=True)


# Case file rate = # cases filed / (# cases completed review-> filed+ntfld)
def file_rate(fld: pd.DataFrame = fld, ntfld: pd.DataFrame = ntfld):

    # Tidy dataframes
    fld = fld.copy()
    fld["file_status"] = "Filed"

    ntfld = ntfld.copy()
    ntfld = ntfld.loc[ntfld["min_ntfld_rank"] != 3]
    ntfld["file_status"] = "Not Filed"

    # Combine and count unique cases per period + status
    combined = pd.concat([
        fld[["period", "pbk_num", "file_status"]],
        ntfld[["period", "pbk_num", "file_status"]],
    ], ignore_index=True)

    chart_df = (
        combined.groupby(["period", "file_status"])["pbk_num"]
        .nunique()
        .reset_index(name="count")
        .assign(period=lambda df: df["period"].astype(str))
    )

    # Pivot to compute filing rate per period
    chart_df = (
        chart_df.pivot_table(index="period", columns="file_status", values="count", fill_value=0)
        .reset_index()
        .rename_axis(None, axis=1)
    )
    chart_df["total_reviewed"] = chart_df["Filed"] + chart_df["Not Filed"]
    chart_df["file_rate"] = (chart_df["Filed"] / chart_df["total_reviewed"]).round(3)

    # Altair line + point chart
    base = alt.Chart(chart_df).encode(
        x=alt.X("period:O", title="Period", sort=None),
        tooltip=[
            alt.Tooltip("period:O",          title="Period"),
            alt.Tooltip("Filed:Q",           title="Cases Filed"),
            alt.Tooltip("Not Filed:Q",       title="Cases Not Filed"),
            alt.Tooltip("total_reviewed:Q",  title="Total Reviewed"),
            alt.Tooltip("file_rate:Q",       title="Filing Rate", format=".1%"),
        ],
    )

    line = base.mark_line(color="#2166ac", strokeWidth=2).encode(
        y=alt.Y("file_rate:Q", title="Filing Rate", axis=alt.Axis(format=".0%"),
                scale=alt.Scale(domain=[0, 1])),
    )

    points = base.mark_point(color="#2166ac", filled=True, size=60).encode(
        y=alt.Y("file_rate:Q", scale=alt.Scale(domain=[0, 1])),
    )

    chart = (
        (line + points)
        .properties(title="Case Filing Rate by Period", width="container")
    )

    # Output
    st.header("📁 Filing Rate")
    st.caption("Of the cases that have completed review, what % have been filed with the court?")
    st.altair_chart(chart, use_container_width=True)

# Review time (avg/median; file vs not file)
def decision_time(rcvd: pd.DataFrame = rcvd, fld: pd.DataFrame = fld, ntfld: pd.DataFrame = ntfld):

    # --- Filed ---
    fld = fld.copy()
    # fld = fld.merge(rcvd[["pbk_num", "ref_date"]], on="pbk_num", how="left")
    fld["days_to_decision"] = (
        pd.to_datetime(fld["earliest_fld_date"]) - pd.to_datetime(fld["ref_date"])
    ).dt.days
    fld["outcome"] = "Filed"

    # --- Not Filed (exclude PFI) ---
    ntfld = ntfld.copy()
    ntfld = ntfld.loc[ntfld["min_ntfld_rank"] != 3]
    # ntfld = ntfld.merge(rcvd[["pbk_num", "ref_date"]], on="pbk_num", how="left")
    ntfld["days_to_decision"] = (
        pd.to_datetime(ntfld["earliest_ntfld_date"]) - pd.to_datetime(ntfld["ref_date"])
    ).dt.days
    ntfld["outcome"] = "Not Filed"

    # --- Combine, drop anomalies ---
    combined = pd.concat([
        fld[["period",  "outcome", "days_to_decision", "ref_date"]],
        ntfld[["period", "outcome", "days_to_decision", "ref_date"]],
    ], ignore_index=True)
    combined = combined.loc[combined["days_to_decision"] >= 0]

    # --- Aggregate: both median and mean per period + outcome ---
    chart_df = (
        combined.groupby(["period", "outcome"])["days_to_decision"]
        .agg(median_days="median", mean_days="mean")
        .reset_index()
        .assign(
            period=lambda df: df["period"].astype(str),
            median_days=lambda df: df["median_days"].round(1),
            mean_days=lambda df: df["mean_days"].round(1),
        )
    )

    # --- Melt to long format so both stats share the same encoding ---
    chart_df = chart_df.melt(
        id_vars=["period", "outcome"],
        value_vars=["median_days", "mean_days"],
        var_name="statistic",
        value_name="days",
    ).replace({
        "median_days": "Median",
        "mean_days": "Mean",
    })

    # --- Altair ---
    color_scale = alt.Scale(
        domain=["Filed", "Not Filed"],
        range=["#2166ac", "#d6604d"],
    )

    dash_scale = alt.Scale(
        domain=["Median", "Mean"],
        range=[[1, 0], [6, 4]],   # solid vs dashed
    )

    base = alt.Chart(chart_df).encode(
        x=alt.X("period:O", title="Period", sort=None),
        y=alt.Y("days:Q", title="Days from Referral to Decision"),
        color=alt.Color("outcome:N", title="Outcome", scale=color_scale),
        strokeDash=alt.StrokeDash("statistic:N", title="Statistic", scale=dash_scale),
        tooltip=[
            alt.Tooltip("period:O",    title="Period"),
            alt.Tooltip("outcome:N",   title="Outcome"),
            alt.Tooltip("statistic:N", title="Statistic"),
            alt.Tooltip("days:Q",      title="Days", format=".1f"),
        ],
    )

    chart = (
        (base.mark_line(strokeWidth=2) + base.mark_point(filled=True, size=60))
        .properties(title="Days from Referral to Decision by Period", width="container")
    )

    st.header("📁 Duration of Case Review")
    st.caption("Length of time between case referral and charging decision (file vs. decline), both mean and median.")
    st.altair_chart(chart, use_container_width=True)

# Total Cases Filed
def cases_fld(fld: pd.DataFrame = fld):

    # Tidy pandas DataFrame — now includes zero-case periods
    chart_df = (
        fld.groupby("period")["pbk_num"]
        .nunique() # sum of unique pbk_num (karpel case number)
        .reindex(full_index, fill_value=0) # reindex with full_index
        .reset_index(name="total_cases") # convert index to column
        .rename(columns={"index": "period"})
        .assign(period=lambda df: df["period"].astype(str))
    )

    # Render altair bar chart
    chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("period:O", title="Period", sort=None),
            y=alt.Y("total_cases:Q", title="Total Cases Filed"),
            tooltip=["period", "total_cases"],
        )
        .properties(title="Cases Filed by Period", width="container")
    )

    # Output
    st.header("📁 Cases Filed")
    st.caption("Cases filed by the prosecuting attorney's office over the selected period.")
    # st.badge() #  # PPI # Justice Counts # Measures for Justice | # View-only 
    # st.divider()
    # st.markdown()
    st.altair_chart(chart, use_container_width=True)
    # st.write_stream("hello...")

# Total Cases Not Filed
def cases_ntfld(ntfld: pd.DataFrame = ntfld):

    # Tidy pandas DataFrame — now includes zero-case periods
    chart_df = (
        ntfld.groupby("period")["pbk_num"]
        .nunique() # sum of unique pbk_num (karpel case number)
        .reindex(full_index, fill_value=0) # reindex with full_index
        .reset_index(name="total_cases") # convert index to column
        .rename(columns={"index": "period"})
        .assign(period=lambda df: df["period"].astype(str))
    )

    # Render altair bar chart
    chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("period:O", title="Period", sort=None),
            y=alt.Y("total_cases:Q", title="Total Cases Not Filed"),
            tooltip=["period", "total_cases"],
        )
        .properties(title="Cases Not Filed by Period", width="container")
    )

    # Output
    st.header("📁 Cases Not Filed")
    st.caption("Cases the prosecuting attorney's office declined to file over the selected period.")
    # st.badge() #  # PPI # Justice Counts # Measures for Justice | # View-only 
    # st.divider()
    # st.markdown()
    st.altair_chart(chart, use_container_width=True)
    # st.write_stream("hello...")

# Total Cases Disposed
def cases_disp(disp: pd.DataFrame = disp):

    # Tidy pandas DataFrame — now includes zero-case periods
    chart_df = (
        disp.groupby("period")["pbk_num"]
        .nunique() # sum of unique pbk_num (karpel case number)
        .reindex(full_index, fill_value=0) # reindex with full_index
        .reset_index(name="total_cases") # convert index to column
        .rename(columns={"index": "period"})
        .assign(period=lambda df: df["period"].astype(str))
    )

    # Render altair bar chart
    chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("period:O", title="Period", sort=None),
            y=alt.Y("total_cases:Q", title="Total Cases Disposed"),
            tooltip=["period", "total_cases"],
        )
        .properties(title="Cases Disposed by Period", width="container")
    )

    # Output
    st.header("📁 Cases Disposed")
    st.caption("Cases disposed by the prosecuting attorney's office over the selected period.")
    # st.badge() #  # PPI # Justice Counts # Measures for Justice | # View-only 
    # st.divider()
    # st.markdown()
    st.altair_chart(chart, use_container_width=True)
    # st.write_stream("hello...")


# st.expander 

from stats.ytd_totals import render_ytd_metric
with st.expander("How many cases has the JCPAO processed year-to-date?", expanded=False, icon=None, width="stretch"):
    render_ytd_metric(RCVD, FLD, NTFLD, DISP)

with st.expander("How many cases has the Office received?", expanded=False, icon=None, width="stretch"):
    cases_rcvd()

with st.expander("What is the status of cases the Office received?", expanded=False, icon=None, width="stretch"):
    rcvd_cases_status()

with st.expander("How many cases has the Office filed?", expanded=False, icon=None, width="stretch"):
    cases_fld()

with st.expander("What is the Office's filing rate (%)?", expanded=False, icon=None, width="stretch"):
    file_rate()
    st.latex(r"\text{Filing Rate (\%)} = \frac{\text{Cases Filed}}{\text{Cases Filed} + \text{Cases Not Filed}}")

with st.expander("How many cases has the Office not filed?", expanded=False, icon=None, width="stretch"):
    cases_ntfld()

with st.expander("How long does the Office take to review a case?", expanded=False, icon=None, width="stretch"):
    decision_time()

with st.expander("How many cases has the Office disposed?", expanded=False, icon=None, width="stretch"):
    cases_disp()


# Unique defendants referred each period

# Breakdown of felony / misdemeanor / class type 



# st.write(f"""
#     Not Filed ranking:
#     {
#         (
#             ntfld[["min_ntfld_rank", "min_ntfld_category"]].drop_duplicates(subset="min_ntfld_rank")
#             .sort_values("min_ntfld_rank", ascending=True)
#             .reset_index(drop=True)
#         )
#     }
# """)


