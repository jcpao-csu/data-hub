import streamlit as st
import pandas as pd

from session_state import get_filtered_data, render_sidebar
from read_data import get_dataframes

from stats.last_updated import post_last_updated
from stats.case_totals import render_case_totals
from stats.case_overview import render_case_volume
from stats.rcvd_by_agency import render_rcvd_by_agency
# from stats.case_volume import render_case_volume
from stats.case_lifecycle_sankey import render_case_lifecycle_sankey

# --- Page title ---

st.markdown("<h1 style='text-align: center;'>JCPAO Dashboard Overview</h1>", unsafe_allow_html=True)
st.divider()


# --- Load data ---

RCVD, FLD, NTFLD, DISP, MSHP_CODES, AGENCIES = get_dataframes()
TODAY = pd.Timestamp.now()


# --- Sidebar ---

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**JCPAO Dashboard Overview**")
    st.caption(f"Welcome to the JCPAO Dashboard!{post_last_updated(RCVD)}")
    st.caption("Use the filters below to explore the data displayed across the dashboard.")
    render_sidebar()


# --- Load filtered data (after sidebar so st.stop() doesn't block sidebar) ---

rcvd, fld, ntfld, disp = get_filtered_data()


# --- Render dashboard metrics ---
render_case_totals(rcvd, fld, ntfld, disp, RCVD=RCVD, FLD=FLD, NTFLD=NTFLD, DISP=DISP)

render_case_volume(rcvd, fld, ntfld, disp, FLD=FLD, NTFLD=NTFLD, DISP=DISP)
# col_left, col_right = st.columns(2)
# with col_left:
#     render_case_volume(rcvd, fld, ntfld, disp)
# with col_right:
#     render_rcvd_by_agency(rcvd)

# render_case_lifecycle_sankey(rcvd, FLD, NTFLD, DISP)
