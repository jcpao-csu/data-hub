import streamlit as st
from maps.rcvd_def_zipcode import render_def_zipcode
from read_data import get_dataframes
from session_state import get_filtered_data, render_sidebar
from stats.last_updated import post_last_updated
# 

RCVD, FLD, NTFLD, DISP, MSHP_CODES, AGENCIES = get_dataframes()

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**Defendant Demographics | Defendant Race**")
    st.caption(post_last_updated(RCVD))
    render_sidebar()

st.markdown("<h1 style='text-align: center;'>Breakdown by Defendant Race</h1>", unsafe_allow_html=True)
st.divider()

rcvd, fld, ntfld, disp = get_filtered_data()

# 