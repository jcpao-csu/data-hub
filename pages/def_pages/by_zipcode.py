import streamlit as st
from read_data import get_dataframes
from session_state import get_filtered_data, render_sidebar
from stats.last_updated import post_last_updated
from maps.rcvd_def_zipcode import render_def_zipcode

# Import hardcoded dataframes
RCVD, FLD, NTFLD, DISP, MSHP_CODES, AGENCIES = get_dataframes()

# Initialize sidebar
with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**Defendant Demographics | ZIP Code**")
    st.caption(post_last_updated(RCVD))
    render_sidebar()

# Streamlit page header
st.markdown("<h1 style='text-align: center;'>Breakdown by ZIP Code</h1>", unsafe_allow_html=True)
st.divider()

# Load filtered data
rcvd, fld, ntfld, disp = get_filtered_data()

# ZIP code dashboard component
render_def_zipcode(rcvd)