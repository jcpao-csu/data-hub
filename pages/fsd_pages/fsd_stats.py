import streamlit as st
import pandas as pd
import altair as alt

from read_data import query_table

# --- Import FSD data ---

ADMIN = query_table("SELECT * FROM fsd_admin")
ADMIN_EST = query_table("SELECT * FROM fsd_admin_est")
ADMIN_ENF = query_table("SELECT * FROM fsd_admin_enf")
JUDICIAL_PAT = query_table("SELECT * FROM fsd_judicial_pat")
JUDICIAL_ENF = query_table("SELECT * FROM fsd_judicial_enf")
# STAFF_TOTALS = query_table("SELECT * FROM fsd_staff_totals")

# --- Initialize requisite objects ---
today = pd.Timestamp.now()
today_date = today.date()
current_year = today.year

year_range = pd.period_range(start="2014", end=today_date, freq="Y")
month_range = pd.period_range(start="2014", end=today_date, freq="M")
quarter_range = pd.period_range(start="2014", end=today_date, freq="Q")
week_range = pd.period_range(start="2014", end=today_date, freq="W") # Mon - Sun (like Shoot Review)

# --- Initialize st.session_state ---

if "fsd_admin" not in st.session_state:
    st.session_state["fsd_admin"] = ADMIN

if "fsd_admin_est" not in st.session_state:
    st.session_state["fsd_admin_est"] = ADMIN_EST

if "fsd_admin_enf" not in st.session_state:
    st.session_state["fsd_admin_enf"] = ADMIN_ENF

if "fsd_judicial_pat" not in st.session_state:
    st.session_state["fsd_judicial_pat"] = JUDICIAL_PAT

if "fsd_judicial_enf" not in st.session_state:
    st.session_state["fsd_judicial_enf"] = JUDICIAL_ENF

# if "fsd_view" not in st.session_state:
#     st.session_state["fsd_view"] = "M"

# if "period_range" not in st.session_state:
#     st.session_state["period_range"] = pd.period_range(start="2014", end=today_date, freq="M")

# if "period_min" not in st.session_state:
#     st.session_state["period_min"] = 0

# if "period_max" not in st.session_state:
#     st.session_state["period_max"] = len(st.session_state["period_range"]) - 1

# dfs = ["fsd_admin", "fsd_admin_est", "fsd_admin_enf", "fsd_judicial_pat", "fsd_judicial_enf"]

# for df in dfs:
#     st.write(df)
#     st.write(st.session_state[df].columns)

# --- Streamlit page title ---

st.markdown("<h1 style='text-align: center;'>Family Support Division</h1>", unsafe_allow_html=True)
st.divider()

# --- Callback functions --- 
def get_period():
    """Changes period range on st.select_slider based on st.selectbox selection"""

    # Reset tables 
    st.session_state["fsd_admin"] = ADMIN.copy()
    st.session_state["fsd_admin_est"] = ADMIN_EST.copy()
    st.session_state["fsd_admin_enf"] = ADMIN_ENF.copy()
    st.session_state["fsd_judicial_pat"] = JUDICIAL_PAT.copy()
    st.session_state["fsd_judicial_enf"] = JUDICIAL_ENF.copy()

    # Establish period_range
    period_range = pd.period_range(start="2014", end=today_date, freq=st.session_state["fsd_view"])
    st.session_state["period_range"] = period_range
    # st.session_state["period_labels"] = period_range.astype(str) # Convert pd.PeriodIndex to str
    # st.session_state["range_min"] = 0
    # st.session_state["range_max"] = len(period_range) - 1

    # Groupby DFs
    dfs = ["fsd_admin", "fsd_admin_est", "fsd_admin_enf", "fsd_judicial_pat", "fsd_judicial_enf"]

    # Agg rules dict 
    df_agg = {
        "fsd_admin": {
            "New Cases Received/Opened": "sum" # int 
        },
        "fsd_admin_est": {
            "BOWs Established (# Of Children)": "sum", # int
            "Notice and Findings (Goal 100)": "sum", # int
            "Genetic Testing Results (Goal 100)": "sum", # int
            "Administrative Orders": "sum" # int
        },
        "fsd_admin_enf": {
            "Income Withholding Orders": "sum", # int
            "Collection": "sum", # $$
            "Percentage of Cases Paying": "mean" # % 
        },
        "fsd_judicial_pat": {
            "New Referrals": "sum", # int
            "BOWs Established (# Of Children)": "sum", # int
            "Judicial Orders (095-34 Only)": "sum" # int
        },
        "fsd_judicial_enf": {
            "New Referrals": "sum", # int
            "Collection": "sum", # $$
            "Civil Contempts Filed": "sum", # int
            "Misdemeanors Filed": "sum", # int
            "Misdemeanor Convictions": "sum", # int
            "Felonies Filed": "sum", # int
            "Felony Convictions": "sum", # int
            "Percentage of Cases Paying": "mean" # %
        }
    }

    for df in dfs:

        # Assign st.session_state to df
        groupby_df = st.session_state[df].copy()
        groupby_df["MonthYr"] = pd.to_datetime(groupby_df["MonthYr"], format="%Y-%m-%d", errors="coerce")
        groupby_df["MonthYr"] = groupby_df["MonthYr"].dt.to_period(st.session_state["fsd_view"])

        # Groupby df 
        groupby_df = (
            groupby_df.groupby(groupby_df["MonthYr"])
            .agg(df_agg[df])
            # .set_index("MonthYr")
            .reindex(period_range.asfreq(st.session_state["fsd_view"]), fill_value=0)
            # .rename_axis("MonthYr")
            .reset_index(names="MonthYr")
        )

        # Re-assign groupby df to st.session_state
        st.session_state[df] = groupby_df

def filter_data():
    """Filters FSD data based on range selected via the st.select_slider"""

    return True

# --- st.sidebar input widgets & functions ---
def initiate_widgets(disabled: bool = False, color: str = "violet"):
    """
    Creates input widgets that help end user explore and interact with the data.
    """

    st.markdown(":green-background[:green[Filter data by:]]")

    # Filter by desired (time-level) view
    time_dict = {
        "M": "by Month",
        "Q": "by Quarter",
        "Y": "by Year"
    }

    # Time Interval (st.selectbox) that changes period_range (pd.PeriodIndex), range_min, and range_max
    filter_view = st.selectbox(
        label=f":{color}-background[:{color}[**Time Interval**] ⏰]", # time period / granularity 
        options=time_dict.keys(),
        index=0,
        format_func=lambda x: time_dict[x],
        key="fsd_view", # st.session_state["fsd_view"]
        help="Select the desired time interval through which you would like to examine the data.",
        on_change=get_period,
        placeholder="Select time interval to filter",
        disabled=disabled,
        label_visibility="visible",
        accept_new_options=False,
        width="stretch"
    )

    # Study period (Start & End)
    def fmt(p: pd.Period):
        view = st.session_state["fsd_view"]  # 'M', 'Q', or 'Y'
        if view == "M":
            return p.strftime("%b %Y")  # e.g., "Jan 2023"
        elif view == "Q":
            return f"Q{p.quarter} {p.year}"  # e.g., "Q2 2024"
        elif view == "Y":
            return str(p.year)  # e.g., "2023"
        else:
            return str(p)

    # Period Range (st.select_slider) that filters the data
    selected_index = st.select_slider( # Slider uses integer indices
        label=f":{color}-background[:{color}[**Time Range**] 🗓️]", # "Period Range"
        options=st.session_state["period_range"],
        value=(st.session_state["period_range"][0], st.session_state["period_range"][-1]),
        format_func=lambda p: fmt(p),
        key="period_view", # st.session_state["period_range"]
        help="Select the time period of which you would like to examine the data.",
        # on_change=,
        disabled=disabled,
        label_visibility="visible",
        width="stretch"
    )

    # # Return the period objects from filter
    # st.write(selected_index)
    # selected_periods = st.session_state["period_range"][selected_index[0] : selected_index[1]+1]


# Define post_last_updated() function
def post_last_updated(
    admin_df: pd.DataFrame
):
    """
    FSD DASHBOARD - Last Updated Date
    * st.sidebar.caption(f"Results based on system data as of {latest_date}.")

    Args:
        admin_df : pd.DataFrame // fsd_admin
    
    Returns:
        latest_date : Most recent 'monthyr' (most recent FSD reported month)
    """

    try:
        df = admin_df.copy()
        df["MonthYr"] = pd.to_datetime(df["MonthYr"], format="%Y-%m-%d", errors="coerce")
    except KeyError:
        latest_date = "N/A"
    else:
        latest_date = df["MonthYr"].max()
        latest_date = latest_date.strftime("%B %Y") # "%A, %B %d, %Y"
    # finally:

    # Returns latest ref_date by JCPAO
    return latest_date

# Define 
# --- FSD Stats ---

# --- Streamlit sidebar --- 

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**Family Support Division (FSD)**")
    st.write("Welcome to the FSD Dashboard! Please use the interactive widgets below to explore the dashboard.")
    st.divider()
    initiate_widgets(color="green")
    st.divider()
    st.caption(f"Results based on system data as of {post_last_updated(ADMIN)}. FSD dashboard data is updated monthly.")


# st.dataframe(st.session_state["fsd_admin"])
# st.dataframe(st.session_state["fsd_admin_est"])
# st.dataframe(st.session_state["fsd_admin_enf"])
# st.dataframe(st.session_state["fsd_judicial_pat"])
# st.dataframe(st.session_state["fsd_judicial_enf"])


### FSD data already comes summarized, so functions are only needed to display the summarized data 

def fsd_stat001(df: pd.DataFrame = st.session_state["fsd_admin"]):
    """
    fsd stat #001 = (admin) new cases received/opened
    how many cases the FSD intakes in a given period (adjustable via user filters)
    """

    df["MonthYr"] = pd.to_datetime(df["MonthYr"], format="%Y-%m-%d", errors="coerce")
    df["period"] = df["MonthYr"].dt.to_period("M") # period("M/Y/Q")
    df["period_start"] = df["period"].dt.start_time  # datetime64[ns]
    df["period_label"] = df["period_start"].dt.strftime("%b %Y")

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("period_start:T", title="Month", axis=alt.Axis(format="%b %Y")),
            y=alt.Y("New Cases Received/Opened:Q", title="Count"),
            tooltip=[
                alt.Tooltip("period_label:N", title="Month"),
                alt.Tooltip("New Cases Received/Opened:Q", title="Count", format=",.0f")
            ]
        )

    )# .interactive()

    st.write("New Cases Received / Opened") # add title to altair chart 
    st.altair_chart(chart, use_container_width=True)

# fsd_stat001()

# import altair as alt

# chart = (
#     alt.Chart(df)
#     .mark_bar()
#     .encode(
#         x=alt.X("period_start:T", title="Month",
#                 axis=alt.Axis(format="%b %Y")),
#         y=alt.Y("value:Q", title="Count"),
#         tooltip=[
#             alt.Tooltip("period_label:N", title="Period"),
#             alt.Tooltip("value:Q", title="Count", format=",.0f"),
#         ],
#     )
# )

# # df has a column 'period' that is Period (M/Q/A) and a column 'value'
# df = df.copy()
# df["period_start"] = df["period"].dt.start_time  # datetime64[ns]
# df["period_label"] = df["period"].astype(str)    # optional label like "2025Q4" or "2025-12"

def fsd_stat002(df: pd.DataFrame = st.session_state["fsd_admin_est"]):
    """
    fsd stat #002 = (administrative establishment) BOWs established (# of children born out of wedlock)
    how many children the FSD has identified as born out of wedlock
    """

    df["MonthYr"] = pd.to_datetime(df["MonthYr"], format="%Y-%m-%d", errors="coerce")
    df["period"] = df["MonthYr"].dt.to_period("M") # period("M/Y/Q")
    # df.groupby("period")
    df["period_start"] = df["period"].dt.start_time  # datetime64[ns]
    df["period_label"] = df["period_start"].dt.strftime("%b %Y")

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("period_start:T", title="Month", axis=alt.Axis(format="%b %Y")),
            y=alt.Y("BOWs Established (# Of Children):Q", title="Count"),
            tooltip=[
                alt.Tooltip("period_label:N", title="Month"),
                alt.Tooltip("BOWs Established (# Of Children):Q", title="Count", format=",.0f")
            ]
        )

    )# .interactive()

    st.write("BOW's (Born out of wedlock) Established") # add title to altair chart 
    st.altair_chart(chart, use_container_width=True)

# fsd_stat002()

def fsd_stat003(df: pd.DataFrame = st.session_state["fsd_admin_est"]):
    """
    fsd stat #003 = (administrative establishment) Notice and Findings (Goal: 100)
    ???
    """

    df["MonthYr"] = pd.to_datetime(df["MonthYr"], format="%Y-%m-%d", errors="coerce")
    df["period"] = df["MonthYr"].dt.to_period("M") # period("M/Y/Q")
    # df.groupby("period")
    df["period_start"] = df["period"].dt.start_time  # datetime64[ns]
    df["period_label"] = df["period_start"].dt.strftime("%b %Y")

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("period_start:T", title="Month", axis=alt.Axis(format="%b %Y")),
            y=alt.Y("Notice and Findings (Goal 100):Q", title="Count"),
            tooltip=[
                alt.Tooltip("period_label:N", title="Month"),
                alt.Tooltip("Notice and Findings (Goal 100):Q", title="Count", format=",.0f")
            ]
        )

    )# .interactive()

    st.write("Notice and Findings (Goal 100)") # add title to altair chart 
    st.altair_chart(chart, use_container_width=True)

# fsd_stat003()

def fsd_stat004(df: pd.DataFrame = st.session_state["fsd_admin_est"]):
    """
    fsd stat #004 = (administrative establishment) Genetic Testing Results (Goal: 100)
    ???
    """

    df["MonthYr"] = pd.to_datetime(df["MonthYr"], format="%Y-%m-%d", errors="coerce")
    df["period"] = df["MonthYr"].dt.to_period("M") # period("M/Y/Q")
    # df.groupby("period")
    df["period_start"] = df["period"].dt.start_time  # datetime64[ns]
    df["period_label"] = df["period_start"].dt.strftime("%b %Y")

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("period_start:T", title="Month", axis=alt.Axis(format="%b %Y")),
            y=alt.Y("Genetic Testing Results (Goal 100):Q", title="Count"),
            tooltip=[
                alt.Tooltip("period_label:N", title="Month"),
                alt.Tooltip("Genetic Testing Results (Goal 100):Q", title="Count", format=",.0f")
            ]
        )

    )# .interactive()

    st.write("Genetic Testing Results (Goal 100)") # add title to altair chart 
    st.altair_chart(chart, use_container_width=True)

# fsd_stat004()

def display_stats(
    df: pd.DataFrame, # target DF with data of interest
    data_col: str, # data col to visualize 
    period_view: str, # st.session_state[""]
    title: str, # title of rendered altair chart
    subtitle: str, # subtitle of rendered altair chart
    threshold_text: str = "", # 
    threshold: int = None, # if threshold given, renders mark_rule 
    date_col: str = "MonthYr", # col to convert to datetime/period
    agg_method: str = "sum", # common agg funcs: sum, mean, median, min, max, count (non-NULL count), size (row count incl. NULLs), std, var
    format_style: str = ",.0f"
):
    """insert function notes here"""

    # df = df[[date_col, data_col]]
    df[date_col] = pd.to_datetime(df[date_col], format="%Y-%m-%d", errors="coerce")
    df["period"] = df[date_col].dt.to_period(period_view) # period dtype
    df = df.groupby("period", as_index=False)[data_col].agg(agg_method) # group by period_view (monthly, quarterly, or yearly)
    df["period_datetime"] = df["period"].dt.to_timestamp(how="start") # converts period dtype to datetime64[ns] --dt.start_time 
    
    # convert datetime to string for label display
    if period_view.upper()=="M":
        x_axis_format="%b %Y"
        df["period_str"] = df["period_datetime"].dt.strftime(x_axis_format)
        x_axis_title="Month"
        
    elif period_view.upper()=="Q":
        df["period_str"] = df["period"].astype(str).str.replace("Q", " Q")   #2F4B7C
        # x_axis_format="%Y Q%q"
        # df["period_str"] = df["period"].dt.strftime(x_axis_format)
        x_axis_title="Quarter"

    elif period_view.upper()=="Y":
        x_axis_format="%Y"
        df["period_str"] = df["period_datetime"].dt.strftime(x_axis_format)
        x_axis_title="Year"
        

    # hover 
    hover = alt.selection_point(on="mouseover", empty="none")

    # declare chart
    chart = (
        alt.Chart(
            df,
            title=alt.TitleParams(
                text=title,
                fontSize=18,
                fontWeight="bold",
                anchor="middle", # start / middle / end
                # color="#2F4B7C",
                subtitle=subtitle, # subtitle
                subtitleFontSize=13,
                # subtitleColor="gray"
            )
        )
        .mark_bar(
            # color="#3BB143", #194e1c
            # stroke="#FFFFFF",
            # strokeWidth=1,
            # size=alt.expr("width / 80")
        ) 
        .encode(
            #  x=alt.X("period_datetime:T", title=x_axis_title, axis=alt.Axis(format=x_axis_format, labelAngle=-45, ticks=False)),
            x=alt.X("period_str:O", title=x_axis_title, sort=None), # , axis=alt.Axis(labelAngle=-45, ticks=False)),
            y=alt.Y(f"{data_col}:Q", title=f"Total {data_col}", axis=alt.Axis(format=format_style)),
            tooltip=[
                alt.Tooltip("period_str:N", title=x_axis_title),
                alt.Tooltip(f"{data_col}:Q", title="Total", format=format_style)
            ],
            # opacity=alt.condition(hover, alt.value(1.0), alt.value(0.3)),
            # strokeWidth=alt.condition(hover, alt.value(2), alt.value(0)),
            # stroke=alt.condition(hover, alt.value("black"), alt.value(None))
            color=alt.condition(hover, alt.value("#3BB143"), alt.value("#194E1C"))
        )
        .add_params(hover)
        # .title(title)
    ) # .interactive()

    rule_avg = alt.Chart(df).mark_rule(color='red').encode(
        y=alt.Y(f"mean({data_col}):Q"), # , title=False
        tooltip=[
            alt.Tooltip(f"mean({data_col}):Q", title=f"{x_axis_title}ly Average", format=format_style)
        ]
    )

    label_avg = rule_avg.mark_text(
        x="width",
        dx=-2,
        align="right",
        baseline="bottom",
        text="Average"
    )

    # labels = alt.Chart(df).mark_text(dy=-5).encode(
    #     x="period_str:O",
    #     y=f"{data_col}:Q",
    #     text=alt.condition(hover, "value:Q", alt.value(""))
    # ).add_params(hover)

    if threshold: # if threshold value given 
        highlight = chart.mark_bar(color="#e45755").encode(
            y2=alt.Y2(datum=threshold)
        ).transform_filter(
            alt.datum.Value > threshold
        )

        rule_th = alt.Chart().mark_rule().encode(
            y=alt.Y(datum=threshold)
        )

        label_th = rule_th.mark_text(
            x="width",
            dx=-2,
            align="right",
            baseline="bottom",
            text=threshold_text
        )

        return (chart + highlight + rule_avg + label_avg + rule_th + label_th) # 'bars' 말고 'chart'

    else:
        return (chart + rule_avg + label_avg) #  + labels


# ["fsd_admin", "fsd_admin_est", "fsd_admin_enf", "fsd_judicial_pat", "fsd_judicial_enf"]

# # Admin
#     - New Cases Received/Opened

chart_01 = display_stats(
    df=st.session_state["fsd_admin"],
    # date_col="MonthYr",
    data_col="New Cases Received/Opened",
    # agg_method="sum",
    period_view="Y", # M / Q / Y
    title="New Cases Received or Opened",
    subtitle="Testing Subtitle" # 
)

# render chart
st.altair_chart(chart_01, use_container_width=True) 

# # Administrative Establishment
#     - BOWs Established (# of Children) - born out of wedlock

chart_02 = display_stats(
    df=st.session_state["fsd_admin_est"],
    # date_col="MonthYr",
    data_col="BOWs Established (# Of Children)",
    period_view="Y",
    title="BOWs Established",
    subtitle="Testing Subtitle"
)

# render chart
st.altair_chart(chart_02, use_container_width=True)

#     - Notice and Findings (Goal 100)

chart_03 = display_stats(
    df=st.session_state["fsd_admin_est"],
    # date_col="MonthYr",
    data_col="Notice and Findings (Goal 100)",
    period_view="Y",
    title="Notice and Findings Made",
    subtitle="Testing Subtitle",
    threshold=100,
    threshold_text="Goal: 100"
)

# render chart
st.altair_chart(chart_03, use_container_width=True)

#     - Genetic Testing Results (Goal 100)

chart_04 = display_stats(
    df=st.session_state["fsd_admin_est"],
    data_col="Genetic Testing Results (Goal 100)",
    period_view="Y",
    title="Genetic Testing Results",
    subtitle="Testing Subtitle",
    threshold=100,
    threshold_text="Goal: 100"
)

# render chart
st.altair_chart(chart_04, use_container_width=True)

#     - Administrative Orders 

chart_05 = display_stats(
    df=st.session_state["fsd_admin_est"],
    data_col="Administrative Orders",
    period_view="Y",
    title="Genetic Testing Results",
    subtitle="Testing Subtitle"
)

# render chart
st.altair_chart(chart_05, use_container_width=True)

# # Administrative Enforcement
#     - Income Withholding Orders 

chart_06 = display_stats(
    df=st.session_state["fsd_admin_enf"],
    data_col="Income Withholding Orders",
    period_view="Y",
    title="Income Withholding Orders",
    subtitle="Testing Subtitle"
)

# render chart
st.altair_chart(chart_06, use_container_width=True)

#     - Collection 

chart_07 = display_stats(
    df=st.session_state["fsd_admin_enf"],
    data_col="Collection",
    period_view="Y",
    title="Collection ($)",
    subtitle="Testing Subtitle",
    format_style="$,.2f"
)

# render chart
st.altair_chart(chart_07, use_container_width=True)

#     - Percentage of Cases Paying

chart_08 = display_stats(
    df=st.session_state["fsd_admin_enf"],
    data_col="Percentage of Cases Paying",
    period_view="Y",
    title="Cases Paying (%)",
    subtitle="Testing Subtitle",
    format_style=".1%",
    agg_method="mean"
)

# render chart
st.altair_chart(chart_08, use_container_width=True)

# # Judicial Paternity
#     - New Referrals

chart_09 = display_stats(
    df=st.session_state["fsd_judicial_pat"],
    data_col="New Referrals",
    period_view="Y",
    title="New Judicial Paternity Referrals",
    subtitle="Testing Subtitle"
)

# render chart
st.altair_chart(chart_09, use_container_width=True)

#     - BOWs Established (# of Children)

chart_10 = display_stats(
    df=st.session_state["fsd_judicial_pat"],
    data_col="BOWs Established (# Of Children)",
    period_view="Y",
    title="BOWs Established",
    subtitle="Testing Subtitle"
)

# render chart
st.altair_chart(chart_10, use_container_width=True)

#     - Judicial Orders (095-34 Only)

# # Judicial Enforcement
#     - New Referrals
#     - Collecton
#     - Civil Contempts Filed
#     - Misdemeanors Filed
#     - Misdemeanor Convictions
#     - Felonies Filed
#     - Felony Convictions
#     - Percentage of Cases Paying