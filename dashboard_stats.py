import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime 
import altair as alt
import plotly.graph_objects as go


from read_data import RCVD, FLD, NTFLD, DISP, MSHP_CODES, AGENCIES
from session_state import get_filtered_data

# Load filtered data from session_state
rcvd, fld, ntfld, disp = get_filtered_data()

# --- Get last updated date --- 
def post_last_updated(df: pd.DataFrame = rcvd) -> str:
    """
    JCPAO DASHBOARD - Last Updated Date
    * st.sidebar.caption(f"Results based on system data as of {latest_date}.")
    """
    try:
        ref_dates = pd.to_datetime(df["ref_date"], format="%Y-%m-%d", errors="coerce")
        return f' Dashboard based on system data as of {ref_dates.max().strftime("%A, %B %d, %Y")}.'
    except (KeyError, AttributeError):
        return None

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

    today = pd.Timestamp.now()

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

    today = pd.Timestamp.now()

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

    today = pd.Timestamp.now()

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

    today = pd.Timestamp.now()
    current_year = today.year

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
    df["Year"] = [f"{current_year} YTD" if year == current_year else str(year) for year in df["Year"]]

    # Visualize as altair bar chart
    order = ["Received", "Filed", "Not Filed", "Disposed"]

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x="Year:O",
            y=alt.Y("Total Cases:Q", title="Case Volume"),
            color=alt.Color("Case Status:N", sort=order),
            xOffset=alt.XOffset("Case Status:N", sort=order)
        )
        .properties(
            title={
                "text": "Cases Processed by Year",
                "anchor": "middle",
                "fontSize": 24,
                "fontWeight": "bold"
            }
        )
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
    today = pd.Timestamp.now()
    current_year = today.year
    df["Year"] = [f"{current_year} YTD" if year == current_year else str(year) for year in df["Year"]]

    df = df[df["Year"] == f"{current_year} YTD"]

    return df


# --- RCVD DASHBOARD STATS ---

## Remaining cases under review
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


# --- Case Year/Agency Summary (data-only helpers used by main_view.py) ---

def total_by_year(rcvd: pd.DataFrame, fld: pd.DataFrame, ntfld: pd.DataFrame, disp: pd.DataFrame) -> pd.DataFrame:
    """Return a tidy DataFrame of case counts by year and case status for charting."""

    today = pd.Timestamp.now()
    current_year = today.year

    def prep_df(df: pd.DataFrame, date_col: str, status: str) -> pd.DataFrame:
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df["Year"] = df[date_col].dt.year
        df = df.groupby("Year")["pbk_num"].count().reset_index()
        df.rename(columns={"pbk_num": "Total Cases"}, inplace=True)
        df["Case Status"] = status
        return df

    dfs = [
        prep_df(rcvd, "ref_date", "Received"),
        prep_df(fld, "earliest_fld_date", "Filed"),
        prep_df(ntfld, "earliest_ntfld_date", "Not Filed"),
        prep_df(disp, "earliest_disp_date", "Disposed"),
    ]

    df = pd.concat(dfs, ignore_index=True)
    df["Case Status"] = pd.Categorical(
        df["Case Status"],
        categories=["Received", "Filed", "Not Filed", "Disposed"],
        ordered=True,
    )
    df["Year"] = [f"{current_year} YTD" if year == current_year else str(year) for year in df["Year"]]

    return df


# --- Heatmaps ---

_HEATMAP_MONTH_ORDER = [
    "Jan", "Feb", "Mar", "Apr", "May",
    "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

_HEATMAP_CHARTS = [
    {
        "label":         "Cases Received",
        "date_col":      "ref_date",
        "color_scheme":  "blues",
        "tooltip_title": "Avg. received/day",
    },
    {
        "label":         "Cases Filed",
        "date_col":      "earliest_fld_date",
        "color_scheme":  "greens",
        "tooltip_title": "Avg. filed/day",
    },
    {
        "label":         "Cases Not Filed",
        "date_col":      "earliest_ntfld_date",
        "color_scheme":  "oranges",
        "tooltip_title": "Avg. not filed/day",
    },
    {
        "label":         "Cases Disposed",
        "date_col":      "earliest_disp_date",
        "color_scheme":  "purples",
        "tooltip_title": "Avg. disposed/day",
    },
]


def _heatmap_prepare(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """Average cases per (month, day-of-month) cell across all years."""
    out = df[["pbk_num", date_col]].copy()
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    out = out.dropna(subset=[date_col])
    out = out.drop_duplicates(subset=["pbk_num"])

    out["year"]       = out[date_col].dt.year
    out["month_num"]  = out[date_col].dt.month
    out["month_abbr"] = out[date_col].dt.strftime("%b")
    out["day"]        = out[date_col].dt.day

    daily_counts = (
        out.groupby(["year", "month_num", "month_abbr", "day"])["pbk_num"]
        .nunique()
        .reset_index(name="count")
    )
    averaged = (
        daily_counts.groupby(["month_num", "month_abbr", "day"])["count"]
        .mean()
        .reset_index(name="avg_cases")
    )
    averaged["avg_cases"] = averaged["avg_cases"].round(2)
    averaged = averaged.loc[averaged["avg_cases"] > 0].copy()

    return averaged


def _heatmap_build_chart(
    averaged: pd.DataFrame,
    label: str,
    color_scheme: str,
    tooltip_title: str,
) -> alt.Chart | None:
    if averaged.empty:
        return None

    return (
        alt.Chart(averaged)
        .mark_rect(stroke="white", strokeWidth=0.8)
        .encode(
            x=alt.X(
                "day:O",
                title="Day of Month",
                axis=alt.Axis(labelAngle=0, labelFontSize=10, ticks=False, domain=False),
            ),
            y=alt.Y(
                "month_abbr:O",
                sort=_HEATMAP_MONTH_ORDER,
                title=None,
                axis=alt.Axis(labelFontSize=11, ticks=False, domain=False),
            ),
            color=alt.Color(
                "avg_cases:Q",
                title=tooltip_title,
                scale=alt.Scale(scheme=color_scheme),
                legend=alt.Legend(orient="right", titleFontSize=10, labelFontSize=9, gradientLength=100),
            ),
            tooltip=[
                alt.Tooltip("month_abbr:O", title="Month"),
                alt.Tooltip("day:O",        title="Day"),
                alt.Tooltip("avg_cases:Q",  title=tooltip_title, format=".2f"),
            ],
        )
        .properties(
            width="container",
            height=220,
            title=alt.TitleParams(
                text=label,
                subtitle="Average cases per calendar day, across all years in selected date range",
                fontSize=14,
                subtitleFontSize=11,
                subtitleColor="#777",
                anchor="start",
            ),
        )
        .configure_view(strokeWidth=0)
        .configure_axis(domain=False)
    )


def render_heatmaps(
    rcvd: pd.DataFrame,
    fld: pd.DataFrame,
    ntfld: pd.DataFrame,
    disp: pd.DataFrame,
) -> None:
    """Render four stacked calendar heatmaps (received, filed, not filed, disposed)."""
    dataframes = {
        "Cases Received":  (rcvd,  "ref_date"),
        "Cases Filed":     (fld,   "earliest_fld_date"),
        "Cases Not Filed": (ntfld, "earliest_ntfld_date"),
        "Cases Disposed":  (disp,  "earliest_disp_date"),
    }

    for cfg in _HEATMAP_CHARTS:
        label        = cfg["label"]
        df, date_col = dataframes[label]

        averaged = _heatmap_prepare(df, date_col)
        chart    = _heatmap_build_chart(averaged, label, cfg["color_scheme"], cfg["tooltip_title"])

        if chart is None:
            st.info(f"No data available for **{label}** with the current filters.")
        else:
            st.altair_chart(chart, use_container_width=True)

        st.divider()


# --- Treemap ---

def _treemap_prepare(
    rcvd: pd.DataFrame,
    outer: str,
    inner: str,
) -> tuple[list, list, list, list]:
    """Build parallel lists for a two-level Plotly treemap."""
    import plotly.graph_objects as go

    df = rcvd[["pbk_num", outer, inner]].copy()
    df[outer] = df[outer].fillna("Unknown")
    df[inner] = df[inner].fillna("Unknown")

    outer_counts = df.groupby(outer)["pbk_num"].nunique().reset_index(name="count")
    inner_counts = df.groupby([outer, inner])["pbk_num"].nunique().reset_index(name="count")
    total = int(df["pbk_num"].nunique())

    ids     = ["__root__"]
    labels  = ["All Cases"]
    parents = [""]
    values  = [total]

    for _, row in outer_counts.iterrows():
        ids.append(str(row[outer]))
        labels.append(str(row[outer]))
        parents.append("__root__")
        values.append(int(row["count"]))

    for _, row in inner_counts.iterrows():
        ids.append(f"{row[outer]}||{row[inner]}")
        labels.append(str(row[inner]))
        parents.append(str(row[outer]))
        values.append(int(row["count"]))

    return ids, labels, parents, values


def _treemap_build(
    rcvd: pd.DataFrame,
    outer: str,
    inner: str,
    outer_label: str,
    inner_label: str,
    color_scheme: str,
):
    import plotly.graph_objects as go

    ids, labels, parents, values = _treemap_prepare(rcvd, outer, inner)

    fig = go.Figure(go.Treemap(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        root_color="lightgrey",
        maxdepth=2,
        branchvalues="total",
        textinfo="label+value+percent parent",
        textfont=dict(size=13),
        marker=dict(
            colorscale=color_scheme,
            showscale=True,
            colorbar=dict(thickness=14, tickfont=dict(size=10), title=dict(text="Cases", font=dict(size=11))),
        ),
        hovertemplate="<b>%{label}</b><br>Cases: %{value:,}<br>% of group: %{percentParent:.1%}<extra></extra>",
    ))

    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        height=520,
        title=dict(text=f"Case Volume by {outer_label} → {inner_label}", font=dict(size=14), x=0),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def render_treemap(rcvd: pd.DataFrame) -> None:
    """Render an interactive two-level treemap of case volume by agency and charge category."""
    if rcvd.empty:
        st.info("No data available for the current filters.")
        return

    mode = st.radio(
        "Group by",
        options=["Agency → Charge Category", "Charge Category → Agency"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if mode == "Agency → Charge Category":
        fig = _treemap_build(rcvd, "agency_name", "rcvd_lead_category", "Agency", "Charge Category", "Blues")
    else:
        fig = _treemap_build(rcvd, "rcvd_lead_category", "agency_name", "Charge Category", "Agency", "Purples")

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Click any outer tile to drill down into its breakdown. Click the center label to zoom back out.")


# --- Age Distribution ---

_AGE_GROUPS   = ["Juvenile (< 18)", "Young Adult (18–24)", "Adult (25+)"]
_GROUP_COLORS = ["#e15759", "#f28e2b", "#4e79a7"]


def _age_groups_prepare(rcvd: pd.DataFrame) -> pd.DataFrame:
    df = rcvd[["pbk_num", "period", "ref_date", "def_dob"]].copy()

    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")
    df["def_dob"]  = pd.to_datetime(df["def_dob"],  errors="coerce")
    df = df.dropna(subset=["ref_date", "def_dob"])
    df = df.drop_duplicates(subset=["pbk_num"])

    df["age"] = ((df["ref_date"] - df["def_dob"]).dt.days / 365.25).astype(int)
    df = df.loc[df["age"].between(0, 100)].copy()

    df["age_group"] = np.select(
        condlist=[df["age"] < 18, df["age"].between(18, 24), df["age"] >= 25],
        choicelist=_AGE_GROUPS,
        default=_AGE_GROUPS[2],
    )

    total_per_period = df.groupby("period")["pbk_num"].nunique().rename("period_total")

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


def render_age_groups(rcvd: pd.DataFrame) -> None:
    """Render a stacked bar chart of defendant age groups by period."""
    chart_df = _age_groups_prepare(rcvd)

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

    st.header("Defendant Age at Time of Referral")
    st.caption("Breakdown of cases by defendant age group at the time of referral to the prosecuting attorney's office.")
    st.altair_chart(chart, use_container_width=True)


def _age_histogram_prepare(rcvd: pd.DataFrame) -> pd.DataFrame:
    """Compute defendant age at time of referral."""
    df = rcvd[["pbk_num", "ref_date", "def_dob"]].copy()

    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")
    df["def_dob"]  = pd.to_datetime(df["def_dob"],  errors="coerce")
    df = df.dropna(subset=["ref_date", "def_dob"])

    df["age"] = ((df["ref_date"] - df["def_dob"]).dt.days / 365.25).astype(int)
    df = df.loc[df["age"].between(10, 100)].copy()
    df = df.drop_duplicates(subset=["pbk_num"])

    return df[["pbk_num", "age"]]


def _age_histogram_build_chart(df: pd.DataFrame, bin_size: int) -> alt.Chart:
    total      = len(df)
    mean_age   = df["age"].mean()
    median_age = df["age"].median()

    bars = (
        alt.Chart(df)
        .mark_bar(color="#4e79a7", opacity=0.85)
        .encode(
            x=alt.X("age:Q", bin=alt.Bin(step=bin_size), title="Age at Referral", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("count():Q", title="Number of Cases"),
            tooltip=[
                alt.Tooltip("age:Q",     title="Age (bin start)", bin=alt.Bin(step=bin_size)),
                alt.Tooltip("count():Q", title="Cases"),
            ],
        )
    )

    mean_rule = (
        alt.Chart(pd.DataFrame({"age": [mean_age]}))
        .mark_rule(color="#e15759", strokeWidth=2, strokeDash=[4, 3])
        .encode(x="age:Q", tooltip=[alt.Tooltip("age:Q", title="Mean age", format=".1f")])
    )

    median_rule = (
        alt.Chart(pd.DataFrame({"age": [median_age]}))
        .mark_rule(color="#f28e2b", strokeWidth=2, strokeDash=[4, 3])
        .encode(x="age:Q", tooltip=[alt.Tooltip("age:Q", title="Median age", format=".1f")])
    )

    legend_df = pd.DataFrame({
        "age":   [mean_age, median_age],
        "label": [f"Mean: {mean_age:.1f}", f"Median: {median_age:.1f}"],
        "color": ["#e15759", "#f28e2b"],
    })
    legend_text = (
        alt.Chart(legend_df)
        .mark_text(align="left", fontSize=11, fontWeight="bold", dx=4)
        .encode(
            x=alt.X("age:Q"),
            y=alt.value(12),
            text="label:N",
            color=alt.Color("color:N", scale=None),
        )
    )

    return (
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


def render_age_histogram(rcvd: pd.DataFrame) -> None:
    """Render a histogram of defendant age at time of case referral."""
    df = _age_histogram_prepare(rcvd)

    if df.empty:
        st.info("No valid age data available for the current filters.")
        return

    bin_size = st.select_slider(
        "Bin width (years)",
        options=[1, 2, 5, 10],
        value=5,
        help="Adjust the width of each age bracket.",
    )

    chart = _age_histogram_build_chart(df, bin_size)

    st.header("Suspect Age Histogram")
    st.caption("Interactive histogram of suspect age at time of case referral.")
    st.altair_chart(chart, use_container_width=True)


# --- RECIDIVISM ---

def _compute_first_seen(rcvd_full: pd.DataFrame = RCVD) -> pd.DataFrame:
    """
    Using the full unfiltered dataset, compute each defendant's first-ever
    referral date. Returns df with columns: pbk_def_num, first_ref_date.
    """
    df = rcvd_full.copy()
    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")
    df = df.loc[df["pbk_def_num"].notna() & (df["pbk_def_num"].astype(str).str.strip() != "")]
    df = df.sort_values(["ref_date", "pbk_num"], ascending=[True, True])

    # TODO - if we want to get fancy, we could also use the pbk_def_num to link to the fld / ntfld datasets and check for any earlier filed/not filed dates that might predate the earliest received date in the rcvd dataset. But for now we'll just assume that the first received date is the true "first seen" date for each defendant.
    # TODO - also, if we want to be really fancy, we could compute separate "first seen" dates for each defendant in each dataset (rcvd, fld, ntfld) and then merge those together to get a more complete picture of each defendant's history with the prosecuting attorney's office. But again, for now we'll just keep it simple and use the first received date as the "first seen" date for each defendant.
    # TODO - also, we should probably add some error handling here to catch any cases where the pbk_def_num is not unique or where there are multiple received dates for the same defendant. For now we'll just assume that the data is clean and that each defendant has a unique pbk_def_num and a single received date, but in a real-world application we would want to add some checks to ensure data quality and handle any anomalies appropriately.
    # TODO - also, we should probably add some logging here to track how many unique defendants we have in the dataset and how many of them have valid received dates, as well as any cases that are dropped due to missing or invalid data. This would help us monitor the data quality and identify any potential issues with the dataset that might affect our analysis of recidivism rates. For now we'll just keep it simple and focus on the core functionality of computing the first seen dates, but in a production application we would want to add some additional logging and monitoring to ensure that our data is accurate and reliable.
    # TODO - also, we should probably add some documentation here to explain the assumptions we're making about the data and the limitations of our approach to computing recidivism rates based on the received dataset. For example, we might want to note that our analysis is limited to defendants who have a valid pbk_def_num and a valid received date in the rcvd dataset, and that we are not accounting for any defendants who may have been referred to the prosecuting attorney's office but do not have a valid pbk_def_num or received date in the dataset. We might also want to note that our analysis is based on the assumption that the first received date for each defendant represents their true "first seen" date with the prosecuting attorney's office, which may not always be the case if there are data quality issues or if there are defendants with multiple received dates. For now we'll just keep it simple and focus on the core functionality of computing the first seen dates, but in a production application we would want to add some additional documentation to clarify our assumptions and limitations around this analysis.
    first_seen = (
        df.drop_duplicates(subset=["pbk_def_num"], keep="first")[["pbk_def_num", "ref_date"]]
        .rename(columns={"ref_date": "first_ref_date"})
    )
    return first_seen


def _recidivism_prepare(rcvd: pd.DataFrame, rcvd_full: pd.DataFrame) -> pd.DataFrame:
    """Merge first-seen dates onto the filtered dataset and flag new vs prior referrals."""
    df = rcvd.copy()
    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")
    df = df.loc[df["pbk_def_num"].notna() & (df["pbk_def_num"].astype(str).str.strip() != "")]
    df = df.sort_values(["ref_date", "pbk_num"], ascending=[True, True])

    first_seen = _compute_first_seen(rcvd_full)
    df = df.merge(first_seen, on="pbk_def_num", how="left")

    df["referral_type"] = np.where(
        df["ref_date"] == df["first_ref_date"],
        "New Defendant",
        "Prior Referral",
    )
    return df


def _build_referral_type_chart(df: pd.DataFrame, is_normalized: bool) -> alt.Chart:
    type_order  = ["New Defendant", "Prior Referral"]
    type_colors = ["#4da6ff", "#e05c5c"]

    total_per_period = df.groupby("period")["pbk_num"].nunique().rename("period_total")

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


def _build_recurrence_chart(rcvd_full: pd.DataFrame) -> alt.Chart:
    """How many defendants appeared exactly once, twice, three times, etc.?"""
    df = rcvd_full.copy()
    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")
    df = df.loc[df["pbk_def_num"].notna() & (df["pbk_def_num"].astype(str).str.strip() != "")]
    df = df.drop_duplicates(subset=["pbk_num"])

    referral_counts = (
        df.groupby("pbk_def_num")["pbk_num"]
        .nunique()
        .reset_index(name="n_referrals")
    )
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
    dist["pct"]              = (dist["n_defendants"] / total_defs).round(3)
    dist["pct_label"]        = (dist["pct"] * 100).round(1).astype(str) + "%"
    dist["n_defendants_fmt"] = dist["n_defendants"].apply(lambda x: f"{x:,}")

    return (
        alt.Chart(dist)
        .mark_bar(color="#4da6ff", opacity=0.85, cornerRadius=3)
        .encode(
            x=alt.X("n_referrals_label:O", sort=label_order, title="Number of Referrals", axis=alt.Axis(labelAngle=0)),
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


def _build_time_between_chart(rcvd_full: pd.DataFrame) -> alt.Chart:
    """Median/mean days between first and second referral, by year of second referral."""
    df = rcvd_full.copy()
    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")
    df = df.loc[df["pbk_def_num"].notna() & (df["pbk_def_num"].astype(str).str.strip() != "")]
    df = df.drop_duplicates(subset=["pbk_num"])
    df = df.sort_values(["pbk_def_num", "ref_date", "pbk_num"])

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

    melted = agg.melt(
        id_vars=["year", "n"],
        value_vars=["median_days", "mean_days"],
        var_name="statistic",
        value_name="days",
    )
    melted["statistic"] = melted["statistic"].map({"median_days": "Median", "mean_days": "Mean"})

    return (
        alt.Chart(melted)
        .mark_line(point=True)
        .encode(
            x=alt.X("year:O", title="Year of Second Referral", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("days:Q", title="Days Between 1st and 2nd Referral"),
            color=alt.Color(
                "statistic:N",
                title=None,
                scale=alt.Scale(domain=["Median", "Mean"], range=["#4da6ff", "#f28e2b"]),
            ),
            strokeDash=alt.StrokeDash(
                "statistic:N",
                scale=alt.Scale(domain=["Median", "Mean"], range=[[1, 0], [4, 2]]),
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


def render_recidivism(
    rcvd: pd.DataFrame = rcvd,
    rcvd_full: pd.DataFrame = RCVD,
) -> None:
    """
    Render recidivism / re-referral metrics section.

    rcvd      — responds to sidebar filters (date range, agency, charge cat, etc.)
    rcvd_full — the raw unfiltered table, used for first-seen date computation
                and full-history charts (recurrence dist, time between referrals)
    """
    df = _recidivism_prepare(rcvd, rcvd_full)

    if df.empty:
        st.info("No valid defendant data available for the current filters.")
        return

    st.header("Re-Referral Activity")
    st.caption(
        "Tracks defendants referred to this office more than once. "
        "'Prior Referral' indicates the defendant had at least one case "
        "referred before the current period — based on full case history "
        "dating back to 2016."
    )

    view = st.segmented_control(
        label=None,
        options=["Count", "Normalized (%)"],
        default="Count",
        selection_mode="single",
    )
    is_normalized = view == "Normalized (%)"
    st.altair_chart(_build_referral_type_chart(df, is_normalized), use_container_width=True)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.altair_chart(_build_recurrence_chart(rcvd_full), use_container_width=True)
    with col2:
        st.altair_chart(_build_time_between_chart(rcvd_full), use_container_width=True)
