import streamlit as st
import altair as alt

from session_state import get_filtered_data, render_sidebar
from dashboard_stats import post_last_updated, stat1b_total_ytd, total_by_year, total_by_agency

# --- Page title ---

st.markdown("<h1 style='text-align: center;'>JCPAO Dashboard Overview</h1>", unsafe_allow_html=True)
st.divider()

# --- Sidebar ---

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**JCPAO Dashboard Overview**")
    st.divider()
    render_sidebar()

# --- Load filtered data ---

rcvd, fld, ntfld, disp = get_filtered_data()

# --- YTD Metrics ---

st.markdown("<h4 style='text-align: center;'>Criminal Cases Processed Year-to-Date</h4>", unsafe_allow_html=True)
st.write(" ")
ytd_metrics = st.container(horizontal=True)
st.write(" ")

with ytd_metrics:

    rcvd_ytd, fld_ytd, ntfld_ytd, disp_ytd = st.columns(4)

    with rcvd_ytd:
        stat1b_total_ytd(rcvd, "received", "ref_date", "***Total Received (YTD)***")

    with fld_ytd:
        stat1b_total_ytd(fld, "filed", "earliest_fld_date", "***Total Filed (YTD)***")

    with ntfld_ytd:
        stat1b_total_ytd(ntfld, "not filed", "earliest_ntfld_date", "***Total Not Filed (YTD)***", delta_color="inverse")

    with disp_ytd:
        stat1b_total_ytd(disp, "disposed", "earliest_disp_date", "***Total Disposed (YTD)***")

# --- Cases by Year ---

cases_by_year = st.container()

with cases_by_year:
    order = ["Received", "Filed", "Not Filed", "Disposed"]

    chart = (
        alt.Chart(total_by_year(rcvd, fld, ntfld, disp))
        .mark_bar()
        .encode(
            x="Year:O",
            y=alt.Y("Total Cases:Q", title="Case Volume"),
            color=alt.Color("Case Status:N", sort=order),
            xOffset=alt.XOffset("Case Status:N", sort=order)
        )
        .properties(
            title={
                "text": "Cases Processed by Year and Status",
                "anchor": "middle",
                "fontSize": 24,
                "fontWeight": "bold"
            }
        )
    )

    st.altair_chart(chart, width="container")


# --- Cases by Referring Agency ---

cases_by_agency = st.container()

with cases_by_agency:
    order = ["Received", "Filed", "Not Filed", "Disposed"]
    agency_df = total_by_agency(rcvd, fld, ntfld, disp)

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
            color=alt.Color("Case Status:N", sort=order),
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

    st.altair_chart(chart, width="container")
