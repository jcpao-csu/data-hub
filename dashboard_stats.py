import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime 

import altair as alt
import plotly.graph_objects as go

from read_data import RCVD, FLD, NTFLD, DISP


# --- Initialize requisite objects ---
# today = datetime.now() 
# today_date = today.date()
# current_year = today.year

today = pd.Timestamp.now()
today_date = today.date()
current_year = today.year
year_range = pd.period_range(start="2016", end=today_date, freq="Y")
month_range = pd.period_range(start="2016", end=today_date, freq="M")
quarter_range = pd.period_range(start="2016", end=today_date, freq="Q")
week_range = pd.period_range(start="2016", end=today_date, freq="W") # Mon - Sun (like Shoot Review)

# --- Get last updated date --- 
def post_last_updated(
    rcvd_df: pd.DataFrame
):
    """
    JCPAO DASHBOARD - Last Updated Date
    * st.sidebar.caption(f"Results based on system data as of {latest_date}.")

    Args:
        rcvd_df : pd.DataFrame // RCVD data report
    
    Returns:
        latest_date : Most recent 'ref_date' (date of the most recent case received by the JCPAO)
    """

    try:
        df = rcvd_df.copy()
        df["ref_date"] = pd.to_datetime(df["ref_date"], format="%Y-%m-%d", errors="coerce")
    except KeyError:
        latest_date = "N/A"
    else:
        latest_date = df["ref_date"].max()
        latest_date = latest_date.strftime("%A, %B %d, %Y")
    # finally:

    # Returns latest ref_date by JCPAO
    return latest_date


# --- Define functions for dashboard statistics ---

## STAT #1A - Total Processed Cases
def stat1a_total(
    df: pd.DataFrame,
    case_type: str,
    date_col: str,
    period: str,
    period_range: pd.PeriodIndex,
    metric_label: str,
    chart_type: str = "area",
    delta_color: str = "off",
):
    """
    JCPAO DASHBOARD STAT #1A - Total Processed Cases

    Args:
        df : pd.DataFrame // (i.e. RCVD / FLD / NTFLD / DISP)
        case_type : str // string for stat summary (see return) (i.e., "recevied", "filed", "not filed", "disposed")
        date_col : str // (i.e. ref_date / earliest_fld_date / earliest_ntfld_date / earliest_disp_date)
        period : str // (i.e. 'Y' / 'M' / 'Q' / 'W' / 'D' / 'H')
        period_range : pd.PeriodIndex // period range from 2016 - current year (YTD)
        metric_label : str // title of st.metric card
        chart_type : str // (i.e. "line" [default], "area", "bar")
        delta_color : str // (i.e. "normal" [default], "inverse", "off")

    Returns:
        Displays st.metric
        Returns stat summary

    """

    # Convert date col to datetime
    df[date_col] = pd.to_datetime(df[date_col])

    # Group by
    period_count = df.groupby(df[date_col].dt.to_period(period))["pbk_num"].count()
    period_count = period_count.reindex(period_range, fill_value=0).reset_index()

    # Sparkline: total cases processed over the years 
    sparkline_data = period_count["pbk_num"].tolist()
    case_text = "cases" if sparkline_data[-1] != 1 else "case"

    # Delta: reported change
    if period.upper()=="Y": # processed cases / month
        total_days = today.strftime("%j") # day (of 365) in current year 
        cases_per_month = sparkline_data[-1] / int(total_days) * 30
        cases_per_month_prev_yr = sparkline_data[-2] / 12
        delta_pct = f"{((cases_per_month - cases_per_month_prev_yr) / cases_per_month_prev_yr * 100):+.1f}%"
    elif period.upper()=="Q": # processed cases 
        print("True") # update
    elif period.upper()=="M":
        print("True") # update
    elif period.upper()=="W":
        print("True") # update

    # Display metric card
    st.metric(
        label=metric_label,
        value=f"{sparkline_data[-1]} {case_text}",
        delta=f"{cases_per_month} cases per month", # ({last_total} YTD {current_year - 1})
        delta_color=delta_color,
        height=185, 
        # width="content",
        chart_data=sparkline_data,
        chart_type=chart_type,
        border=True
    )

    # Return stat summary
    return f"The JCPAO has {case_type} {sparkline_data[-1]} cases as of {today.strftime('%B %d, %Y')}, roughly averaging {cases_per_month} cases per month, compared to {cases_per_month_prev_yr} cases per month in the previous year ({delta_pct}% difference)." 


## STAT #1b - Total Processed Cases YTD (Year-over-Year comparison)
def stat1b_total_ytd(
    df: pd.DataFrame, 
    case_type: str,
    date_col: str, 
    metric_label: str, 
    chart_type: str = "area", 
    delta_color: str = "normal",
):
    """
    JCPAO DASHBOARD STAT #1B - Total Processed Cases Year-to-Date (YTD)

    Args:
        df : pd.DataFrame // (i.e. RCVD / FLD / NTFLD / DISP)
        case_type : str // string for stat summary (see return) (i.e., "recevied", "filed", "not filed", "disposed")
        date_col : str // (i.e. ref_date / earliest_fld_date / earliest_ntfld_date / earliest_disp_date)
        metric_label : str // title of st.metric card 
        chart_type : str // (i.e. "line" [default], "area", "bar")
        delta_color : str // (i.e. "normal" [default], "inverse", "off")

    Returns: 
        Displays st.metric 
        Returns stat summary

    """

    # Prepare DF for groupby
    df[date_col] = pd.to_datetime(df[date_col])
    df["year"] = df[date_col].dt.year # .dt.to_period("Y") -- convert datetime column to 'period' object / a time interval, rather than a timestamp: 'Y' / 'M' / 'Q' / 'W' / 'D' / 'H'

    # Filter DF to cases processed as of today's date 
    ytd_mask = (
        (df[date_col].dt.month < today.month) |
        ((df[date_col].dt.month == today.month) & (df[date_col].dt.day <= today.day))
    )

    df = df[ytd_mask]

    # Group by
    annual_count = df.groupby("year")["pbk_num"].count().reset_index()
    annual_count.rename(columns={"pbk_num": "total_cases"}, inplace=True)

    # Sparkline: total cases processed over the years 
    sparkline_data = annual_count["total_cases"].tolist()

    # Delta: current (latest) year vs prior year
    delta = sparkline_data[-1] - sparkline_data[-2]

    # Calculate % difference
    if sparkline_data[-2] == 0: # prior year total is zero 
        delta_pct = "N/A"
    else:
        delta_pct = f"{(delta / sparkline_data[-2] * 100):+.1f}%"

    # Display metric card
    st.metric(
        label=metric_label,
        value=f"{sparkline_data[-1]} cases",
        delta=f"{delta} (YoY) | {delta_pct}", # ({last_total} YTD {current_year - 1})
        delta_color=delta_color,
        height=185, 
        # width="content",
        chart_data=sparkline_data,
        chart_type=chart_type,
        border=True
    )

    # Return stat summary
    return f"The JCPAO has {case_type} {sparkline_data[-1]} cases as of {today.strftime('%B %d, %Y')}, a {delta_pct}% change from the same time last year ({sparkline_data[-2]} cases)." 

## STAT #1c - Total Processed Cases by Month-Year
def stat1c_total_month(
    df: pd.DataFrame, 
    case_type: str,
    date_col: str, 
    metric_label: str, 
    chart_type: str = "bar", 
    delta_color: str = "normal",
):
    """
    JCPAO DASHBOARD STAT #1C - Total Processed Cases (Month-Year Comparison)

    Args:
        df : pd.DataFrame // (i.e. RCVD / FLD / NTFLD / DISP)
        case_type : str // string for stat summary (see return) (i.e., "recevied", "filed", "not filed", "disposed")
        date_col : str // (i.e. ref_date / earliest_fld_date / earliest_ntfld_date / earliest_disp_date)
        metric_label : str // title of st.metric card 
        chart_type : str // (i.e. "line" [default], "area", "bar")
        delta_color : str // (i.e. "normal" [default], "inverse", "off")

    Returns: 
        Displays st.metric 
        Returns stat summary

    """

    # Prepare DF for groupby
    df[date_col] = pd.to_datetime(df[date_col])
    df["month_year"] = df[date_col].dt.to_period("M").astype(str) # .dt.to_period("Y") -- convert datetime column to 'period' object / a time interval, rather than a timestamp: 'Y' / 'M' / 'Q' / 'W' / 'D' / 'H'

    # Group by month-year
    monthly_count = (
        df.groupby("month_year")["pbk_num"].count().reset_index()
        .rename(columns={"pbk_num": "total_cases"})
    )

    # Sort chronologically
    monthly_count["month_year"] = pd.to_datetime(monthly_count["month_year"])
    monthly_count = monthly_count.sort_values("month_year")

    # Sparkline data
    sparkline_data = monthly_count["total_cases"].tolist()

    # Identify current and prior month-year
    current_period = monthly_count["month_year"].iloc[-1]
    prior_period = current_period - pd.DateOffset(years=1)

    # Get current and prior totals
    current_total = monthly_count.loc[
        monthly_count["month_year"] == current_period, "total_cases"
    ].values[0]

    prior_total = monthly_count.loc[
        monthly_count["month_year"] == prior_period, "total_cases"
    ].values[0] if (monthly_count["month_year"] == prior_period).any() else 0

    # Compute deltas
    delta = current_total - prior_total
    delta_pct = "N/A" if prior_total == 0 else f"{(delta / prior_total * 100):+.1f}%"

    # Display metric card
    st.metric(
        label=metric_label,
        value=f"{current_total:,} cases",
        delta=f"{delta} (MoY) | {delta_pct}",
        delta_color=delta_color,
        height=185,
        chart_data=sparkline_data,
        chart_type=chart_type,
        border=True,
    )

    # Return summary text
    return (
        f"As of {today.strftime('%B %d, %Y')}, the JCPAO has {case_type} "
        f"{current_total:,} cases in {current_period.strftime('%B %Y')}, "
        f"a {delta_pct} change from {prior_period.strftime('%B %Y')} "
        f"({prior_total:,} cases)."
    )

"""
# YTD Metrics

st.markdown("<h4 style='text-align: center;'>Criminal Cases Processed Year-to-Date</h4>", unsafe_allow_html=True)
st.write(" ")
ytd_metrics = st.container(horizontal=True)
st.write(" ")

with ytd_metrics:

    rcvd_ytd, fld_ytd, ntfld_ytd, disp_ytd = st.columns(4)

    with rcvd_ytd:
        total_ytd(RCVD, "ref_date", "***Total Received (YTD)***", "area")
    
    with fld_ytd:
        total_ytd(FLD, "earliest_fld_date", "***Total Filed (YTD)***", "area")

    with ntfld_ytd:
        total_ytd(NTFLD, "earliest_ntfld_date", "***Total Not Filed (YTD)***", "area", "inverse")
    
    with disp_ytd:
        total_ytd(DISP, "earliest_disp_date", "***Total Disposed (YTD)***", "area")

"""

## STAT #2a - Total Processed Cases by Year (Bar Chart)
def stat2a_total_by_year(
    rcvd_df: pd.DataFrame, 
    fld_df: pd.DataFrame, 
    ntfld_df: pd.DataFrame, 
    disp_df: pd.DataFrame
) -> pd.DataFrame:
    """
    JCPAO DASHBOARD STAT #2A - Total Processed Cases by Year (Bar Chart)

    Args:
        rcvd_df : pd.DataFrame // Dataframe of received cases 
        fld_df : pd.DataFrame // Dataframe of filed cases
        ntfld_df : pd.DataFrame // Dataframe of not filed cases
        disp_df : pd.DataFrame // Dataframe of disposed cases

    Returns: 
        Displays st.altair_chart
        Returns stat summary
    """

    # Define prep_df() to get summary totals by case status and year
    def prep_df(df: pd.DataFrame, date_col: str, status: str) -> pd.DataFrame:
        """Returns summarized DF of total cases by year with custom 'Case Status' column"""

        # Prepare DF for groupby
        df[date_col] = pd.to_datetime(df[date_col])
        df["Year"] = df[date_col].dt.year # .dt.to_period("Y") -- convert datetime column to 'period' object / a time interval, rather than a timestamp: 'Y' / 'M' / 'Q' / 'W' / 'D' / 'H'
        df["Month"] = df[date_col].dt.month

        # Group by
        df = df.groupby("Year")["pbk_num"].count().reset_index()
        df.rename(columns={"pbk_num": "Total Cases"}, inplace=True)

        df["Case Status"] = status

        return df

    # Create list of DFs
    rcvd = prep_df(rcvd_df, "ref_date", "Received")
    fld = prep_df(fld_df, "earliest_fld_date", "Filed")
    ntfld = prep_df(ntfld_df, "earliest_ntfld_date", "Not Filed")
    disp = prep_df(disp_df, "earliest_disp_date", "Disposed")

    # List of DFs
    dfs = [rcvd, fld, ntfld, disp]

    # Concatenate DFs (should be 2016 - 2025 YTD)
    df = pd.concat(dfs, ignore_index=True)

    # Final cleaning
    df["Case Status"] = pd.Categorical(df["Case Status"], categories=["Received", "Filed", "Not Filed", "Disposed"], ordered=True)
    df = df.sort_values(["Year", "Case Status"], ascending=[False, True], ignore_index=True)
    df["Year"] = ["2025 YTD" if year == 2025 else str(year) for year in df["Year"]]

    # Visualize as altair bar chart
    order = ["Received", "Filed", "Not Filed", "Disposed"]

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x="Year:O",
            y=alt.Y("Total Cases:Q", title="Case Volume"),
            color=alt.Color("Case Status:N", sort=order),  # 👈 enforce order
            xOffset=alt.XOffset("Case Status:N", sort=order)
        )
        .properties(
            title={
                "text": "Cases Processed by Year",
                "anchor": "middle",
                "fontSize": 24,
                "fontWeight": "bold"
            }
        ) # .interactive()
    )

    st.altair_chart(chart, use_container_width=True)

    # Return summary stats
    return (
        f"As of {today.strftime('%B %d, %Y')}, the JCPAO has "
        f"received {df.loc[('YTD' in df['Year']) & (df['Case Status']=='Received')]} cases, "
        f"filed {df.loc[('YTD' in df['Year']) & (df['Case Status']=='Filed')]} cases, "
        f"not filed {df.loc[('YTD' in df['Year']) & (df['Case Status']=='Not Filed')]} cases, "
        f"and disposed {df.loc[('YTD' in df['Year']) & (df['Case Status']=='Disposed')]} cases."
    )

"""# Bar Chart of Processed Cases by Year
cases_by_year = st.container()

with cases_by_year:
    # stat2a_total_by_year(RCVD, FLD, NTFLD, DISP)
    # st.dataframe(total_by_year(RCVD, FLD, NTFLD, DISP))
    # st.bar_chart(total_by_year(RCVD, FLD, NTFLD, DISP), x="Year", y="Total Cases", color="Case Status", stack=False)
"""

## STAT #2b - Total Processed Cases by Month (Bar Chart)
def stat2b_total_by_month(
    rcvd_df: pd.DataFrame, 
    fld_df: pd.DataFrame, 
    ntfld_df: pd.DataFrame, 
    disp_df: pd.DataFrame
) -> pd.DataFrame:
    """
    JCPAO DASHBOARD STAT #2B - Total Processed Cases by Month (Bar Chart)

    Args:
        rcvd_df : pd.DataFrame // Dataframe of received cases 
        fld_df : pd.DataFrame // Dataframe of filed cases
        ntfld_df : pd.DataFrame // Dataframe of not filed cases
        disp_df : pd.DataFrame // Dataframe of disposed cases

    Returns: 
        Displays st.altair_chart
        Returns stat summary
    """

    # Datetime objects 
    current_month = today.strftime('%Y-%m')
    current_period = pd.to_datetime(current_month, format='%Y-%m') # convert to timestamp
    previous_month = (current_period - pd.DateOffset(years=1)).strftime('%Y-%m') # Subtract one year

    # Define prep_df() to get summary totals by case status and year
    def prep_df(df: pd.DataFrame, date_col: str, status: str) -> pd.DataFrame:
        """Returns summarized DF of total cases by year with custom 'Case Status' column"""

        # Prepare DF for groupby
        df[date_col] = pd.to_datetime(df[date_col])
        df["month_year"] = df[date_col].dt.to_period("M").astype(str)

        # Group by month-year
        monthly_count = (
            df.groupby("month_year")["pbk_num"].count().reset_index()
            .rename(columns={"pbk_num": "total_cases"})
        )

        # Sort chronologically
        monthly_count["month_year"] = pd.to_datetime(monthly_count["month_year"])
        monthly_count = monthly_count.sort_values("month_year")

        # Add 'Case Status' col
        monthly_count["Case Status"] = status

        return monthly_count

    # Create list of DFs 
    rcvd = prep_df(rcvd_df, "ref_date", "Received")
    fld = prep_df(fld_df, "earliest_fld_date", "Filed")
    ntfld = prep_df(ntfld_df, "earliest_ntfld_date", "Not Filed")
    disp = prep_df(disp_df, "earliest_disp_date", "Disposed")

    # List of DFs
    dfs = [rcvd, fld, ntfld, disp]

    # Concatenate DFs (should be 2016 - 2025 YTD)
    df = pd.concat(dfs, ignore_index=True)

    # Final cleaning
    df["Case Status"] = pd.Categorical(df["Case Status"], categories=["Received", "Filed", "Not Filed", "Disposed"], ordered=True)
    df = df.sort_values(["month_year", "Case Status"], ascending=[False, True], ignore_index=True)
    df["month_year"] = df["month_year"].dt.to_period("M").astype(str)

    # Visualize as altair bar chart
    order = ["Received", "Filed", "Not Filed", "Disposed"]

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("month_year:O", title="Year-Month"),
            y=alt.Y("Total Cases:Q", title="Case Volume"),
            color=alt.Color("Case Status:N", sort=order),  # 👈 enforce order
            xOffset=alt.XOffset("Case Status:N", sort=order)
        )
        .properties(
            title={
                "text": "Cases Processed by Year-Month",
                "anchor": "middle",
                "fontSize": 24,
                "fontWeight": "bold"
            }
        ) # .interactive()
    )

    st.altair_chart(chart, use_container_width=True)

    # Return summary stats
    return (
        f"In {today.strftime('%B %Y')}, the JCPAO has "
        f"received {df.loc[(df['month_year']==current_month) & (df['Case Status']=='Received')]} cases, "
        f"filed {df.loc[(df['month_year']==current_month) & (df['Case Status']=='Filed')]} cases, "
        f"not filed {df.loc[(df['month_year']==current_month) & (df['Case Status']=='Not Filed')]} cases, "
        f"and disposed {df.loc[(df['month_year']==current_month) & (df['Case Status']=='Disposed')]} cases "
        f"as of {today.strftime('%B %d, %Y')}.\n"
        f"On the other hand, in {today.strftime('%B')} {today.strftime('%Y') - 1}, the JCPAO has "
        f"received {df.loc[(df['month_year']==previous_month) & (df['Case Status']=='Received')]} cases, "
        f"filed {df.loc[(df['month_year']==previous_month) & (df['Case Status']=='Filed')]} cases, "
        f"not filed {df.loc[(df['month_year']==previous_month) & (df['Case Status']=='Not Filed')]} cases, "
        f"and disposed {df.loc[(df['month_year']==previous_month) & (df['Case Status']=='Disposed')]} cases."  
    )


# Most Common Charge Categories by Year 

# Cases by Referring Agency and Category 

def total_by_agency(rcvd: pd.DataFrame, fld: pd.DataFrame, ntfld: pd.DataFrame, disp: pd.DataFrame) -> pd.DataFrame:

    # Define current period (YTD)
    today = pd.Timestamp.today()
    current_year = today.year

    def prep_df(df: pd.DataFrame, date_col: str, status: str) -> pd.DataFrame:

        # Prepare DF for groupby
        df[date_col] = pd.to_datetime(df[date_col])
        df["Year"] = df[date_col].dt.year # .dt.to_period("Y") -- convert datetime column to 'period' object / a time interval, rather than a timestamp: 'Y' / 'M' / 'Q' / 'W' / 'D' / 'H'
        df["Month"] = df[date_col].dt.month

        # Group by
        df = df.groupby(["Year", "agency_name"])["pbk_num"].count().reset_index()
        df.rename(columns={"pbk_num": "Total Cases"}, inplace=True)

        df["Case Status"] = status

        return df

    # Create list of DFs 
    rcvd = prep_df(rcvd, "ref_date", "Received")
    fld = prep_df(fld, "earliest_fld_date", "Filed")
    ntfld = prep_df(ntfld, "earliest_ntfld_date", "Not Filed")
    disp = prep_df(disp, "earliest_disp_date", "Disposed")

    # List of DFs
    dfs = [rcvd, fld, ntfld, disp]

    # Concatenate DFs (should be 2016 - 2025 YTD)
    df = pd.concat(dfs, ignore_index=True)

    # Final cleaning
    df["Case Status"] = pd.Categorical(df["Case Status"], categories=["Received", "Filed", "Not Filed", "Disposed"], ordered=True)
    df["Year"] = ["2025 YTD" if year == 2025 else str(year) for year in df["Year"]]

    df = df[df["Year"]=="2025 YTD"]

    return df

# Bar Chart of Processed Cases by Referring Agency
cases_by_agency = st.container()

with cases_by_agency:
    # st.dataframe(total_by_agency(RCVD, FLD, NTFLD, DISP))
    # st.bar_chart(total_by_agency(RCVD, FLD, NTFLD, DISP), x="agency_name", y="Total Cases", color="Case Status", stack=False)

    order = ["Received", "Filed", "Not Filed", "Disposed"]
    agency_df = total_by_agency(RCVD, FLD, NTFLD, DISP)

    top_ten_agencies = (
        agency_df.groupby("agency_name", as_index=False)["Total Cases"]
        .sum()
        .sort_values("Total Cases", ascending=False)
        .head(10)
    )

    df_top10 = agency_df[agency_df["agency_name"].isin(top_ten_agencies["agency_name"])]

    chart = (
        alt.Chart(df_top10)
        .mark_bar()
        .encode(
            y=alt.Y("agency_name:O", title="Police Agency", sort=top_ten_agencies["agency_name"].tolist()),
            x=alt.X("Total Cases:Q", title="Case Volume"),
            color=alt.Color("Case Status:N", sort=order),  # 👈 enforce order
            yOffset=alt.YOffset("Case Status:N", sort=order),
            tooltip=[
                alt.Tooltip("agency_name:N", title="Agency"),
                alt.Tooltip("Case Status:N", title="Status"),
                alt.Tooltip("Total Cases:Q", title="Total Cases")
            ]
        )
        .properties(
            title={
                "text": "Cases Processed by Referring Police Agency and Status",
                "anchor": "middle",
                "fontSize": 24,
                "fontWeight": "bold"
            }
        )
    )

    st.altair_chart(chart, use_container_width=True)

    test_df = agency_df

    # Sort by Year ascending, then Case Status descending
    sorted_df = test_df.sort_values(by=["Case Status", "Total Cases"], ascending=[True, False])
    # cols = st.columns(4)
    # with cols[0]:
    #     st.write(sorted_df[sorted_df['Case Status']=="Received"]['agency_name'].tolist())
    # with cols[1]:
    #     st.write(sorted_df[sorted_df['Case Status']=="Filed"]['agency_name'].tolist())
    # with cols[2]:
    #     st.write(sorted_df[sorted_df['Case Status']=="Not Filed"]['agency_name'].tolist())
    # with cols[3]:
    #     st.write(sorted_df[sorted_df['Case Status']=="Disposed"]['agency_name'].tolist())


# --- RCVD DASHBOARD STATS --- 

## RCVD cases broken down by: under review / completed review (i.e. filed / not filed)

## 

## Remaining cases under review 
def under_review_time_series(
    rcvd_df: pd.DataFrame,
    fld_df: pd.DataFrame,
    ntfld_df: pd.DataFrame,
):

    # Import requisite DFs for timeseries DF output
    rcvd = rcvd_df[["pbk_num", "ref_date"]].copy()
    fld = fld_df[["pbk_num", "earliest_fld_date"]].copy()
    ntfld = ntfld_df[["pbk_num", "earliest_ntfld_date"]].copy()

    # Merge DFs
    df = rcvd.merge(fld, how="left", on="pbk_num") # merge onto RCVD DF
    df = df.merge(ntfld, how="left", on="pbk_num")

    # Reassign column names
    df = df.assign(
        date_received=pd.to_datetime(df["ref_date"]),
        date_filed=pd.to_datetime(df["earliest_fld_date"]),
        date_not_filed=pd.to_datetime(df["earliest_ntfld_date"]),
    )

    # Define your date range (from first received to today)
    date_range = pd.date_range(df["date_received"].min(), today, freq="D") # min date should be 2016-01-01 / max date should be pd.Timestamp.today()

    # For each date, count how many are open
    results = []
    for d in date_range:
        open_mask = (
            (df["date_received"] <= d) & # if ref date is prior to select date
            (
                (df["date_filed"].isna() | (df["date_filed"] > d)) & # if not yet filed by select date
                (df["date_not_filed"].isna() | (df["date_not_filed"] > d)) # if not yet NOT filed by select date
            )
        )
        count_open = open_mask.sum()
        results.append({"date": d, "open_cases": count_open})

    # Produce time series DF
    time_series = pd.DataFrame(results)

    # Streamlit display 

    # Return summary stats
    return f""


def under_review_time_series(
    rcvd_df: pd.DataFrame,
    fld_df: pd.DataFrame,
    ntfld_df: pd.DataFrame,
):
    """
    Generate a time series showing the number of cases under review (received but
    not yet filed or not filed) and visualize it with a rolling average overlay.

    Args:
        rcvd_df : pd.DataFrame
            Contains `pbk_num` and `ref_date` (case received date)
        fld_df : pd.DataFrame
            Contains `pbk_num` and `earliest_fld_date`
        ntfld_df : pd.DataFrame
            Contains `pbk_num` and `earliest_ntfld_date`

    Returns:
        time_series : pd.DataFrame
            DataFrame with columns ['date', 'open_cases', 'rolling_avg']
    """

    today = pd.Timestamp.today().normalize()

    # Import requisite DFs
    rcvd = rcvd_df[["pbk_num", "ref_date"]].copy()
    fld = fld_df[["pbk_num", "earliest_fld_date"]].copy()
    ntfld = ntfld_df[["pbk_num", "earliest_ntfld_date"]].copy()

    # Merge all
    df = (
        rcvd
        .merge(fld, how="left", on="pbk_num")
        .merge(ntfld, how="left", on="pbk_num")
        .assign(
            date_received=pd.to_datetime(rcvd["ref_date"]),
            date_filed=pd.to_datetime(fld["earliest_fld_date"]),
            date_not_filed=pd.to_datetime(ntfld["earliest_ntfld_date"])
        )
    )

    # Define range
    date_range = pd.date_range(df["date_received"].min(), today, freq="D")

    # Count open cases
    results = []
    for d in date_range:
        open_mask = (
            (df["date_received"] <= d)
            & ((df["date_filed"].isna()) | (df["date_filed"] > d))
            & ((df["date_not_filed"].isna()) | (df["date_not_filed"] > d))
        )
        results.append({"date": d, "open_cases": open_mask.sum()})

    # Build time series
    time_series = pd.DataFrame(results)

    # Compute 30-day rolling average
    time_series["rolling_avg"] = (
        time_series["open_cases"]
        .rolling(window=30, min_periods=1)
        .mean()
    )

    # --- ALTAIR CHART ---
    base = alt.Chart(time_series).encode(x=alt.X("date:T", title="Date"))

    area = (
        base.mark_area(
            line={"color": "#0072B5"},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="#0072B5", offset=0),
                    alt.GradientStop(color="white", offset=1)
                ],
                x1=1, x2=1, y1=1, y2=0
            ),
        )
        .encode(
            y=alt.Y("open_cases:Q", title="Open Cases Under Review"),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("open_cases:Q", title="Open Cases", format=","),
                alt.Tooltip("rolling_avg:Q", title="30-Day Avg", format=",.0f")
            ],
        )
    )

    rolling_line = (
        base.mark_line(color="#FF7F0E", strokeWidth=2)
        .encode(y="rolling_avg:Q")
    )

    chart = (
        (area + rolling_line)
        .properties(
            title="Active Cases Under Review",
            width="container",
            height=350,
        )
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)

    # return time_series

    # Return summary stats
    return f""

## Time from case received to case filed / not filed 

import pandas as pd
import altair as alt
import streamlit as st

def avg_days_to_file_chart(
    df: pd.DataFrame, # fld df 
    received_col: str = "ref_date",
    filed_col: str = "earliest_fld_date",
):
    """
    Generate an Altair chart showing the average number of days between
    'case received' and 'case filed' over time (by year and month-year).

    Args:
        df : pd.DataFrame
            DataFrame with at least received and filed date columns.
        received_col : str
            Column name for 'date received'
        filed_col : str
            Column name for 'date filed'

    Returns:
        time_summary : pd.DataFrame
            Summary DataFrame with avg days grouped by year and month-year.
    """

    # --- PREP ---
    df = df.copy()
    df[received_col] = pd.to_datetime(df[received_col], errors="coerce")
    df[filed_col] = pd.to_datetime(df[filed_col], errors="coerce")

    # Compute difference in days
    df["days_to_file"] = (df[filed_col] - df[received_col]).dt.days

    # Drop invalid or negative values
    df = df[df["days_to_file"].ge(0)]

    # Extract period info
    df["year"] = df[received_col].dt.year
    df["month_year"] = df[received_col].dt.to_period("M").dt.to_timestamp()

    # --- GROUPED SUMMARIES ---
    year_summary = (
        df.groupby("year")["days_to_file"]
        .mean()
        .reset_index()
        .assign(level="Year")
    )

    month_summary = (
        df.groupby("month_year")["days_to_file"]
        .mean()
        .reset_index()
        .assign(level="Month-Year")
    )

    # --- CHARTS ---
    chart_year = (
        alt.Chart(year_summary)
        .mark_bar(color="#0072B5")
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y("days_to_file:Q", title="Avg Days to File"),
            tooltip=[
                alt.Tooltip("year:O", title="Year"),
                alt.Tooltip("days_to_file:Q", title="Avg Days", format=".1f"),
            ],
        )
        .properties(title="Average Days to File (by Year)", height=250)
    )

    chart_month = (
        alt.Chart(month_summary)
        .mark_line(color="#FF7F0E", point=True)
        .encode(
            x=alt.X("month_year:T", title="Month-Year"),
            y=alt.Y("days_to_file:Q", title="Avg Days to File"),
            tooltip=[
                alt.Tooltip("month_year:T", title="Month-Year"),
                alt.Tooltip("days_to_file:Q", title="Avg Days", format=".1f"),
            ],
        )
        .properties(title="Average Days to File (by Month)", height=300)
        .interactive()
    )

    # --- DISPLAY ---
    st.altair_chart(chart_year, use_container_width=True)
    st.altair_chart(chart_month, use_container_width=True)

    # Return combined summary
    return {
        "year_summary": year_summary,
        "month_summary": month_summary,
    }





## Time from case filed to case disposed 

