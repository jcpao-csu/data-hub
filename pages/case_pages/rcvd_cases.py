import streamlit as st
from read_data import get_dataframes
from session_state import get_filtered_data, render_sidebar
from stats.last_updated import post_last_updated
from stats.rcvd_volume import (
    render_rcvd_volume,
    render_rcvd_status_metrics,
    render_rcvd_status,
    render_under_review,
)
from stats.rcvd_heatmap import render_rcvd_heatmap                                                       
from stats.rcvd_sankey import render_rcvd_sankey

RCVD, FLD, NTFLD, DISP, MSHP_CODES, AGENCIES = get_dataframes()

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**Received Cases**")
    st.caption(post_last_updated(RCVD))
    render_sidebar()

st.markdown("<h1 style='text-align: center;'>Received Cases</h1>", unsafe_allow_html=True)
st.divider()

rcvd, fld, ntfld, disp = get_filtered_data()

render_rcvd_heatmap(RCVD)   
render_rcvd_status_metrics(rcvd, FLD, NTFLD)
render_rcvd_volume(rcvd)
render_rcvd_sankey(rcvd, FLD, NTFLD, DISP)
render_rcvd_status(rcvd, FLD, NTFLD)
render_under_review(RCVD, FLD, NTFLD, DISP)

