import streamlit as st
from read_data import get_dataframes
from session_state import get_filtered_data, render_sidebar
from stats.last_updated import post_last_updated
from stats.disp_volume import render_disp_volume
from stats.disp_outcomes import render_disp_outcomes
from stats.disp_trial import render_trial_verdicts
from stats.disp_breakdown import render_disp_breakdown
from stats.disp_sankey import render_disp_sankey
from stats.case_life import render_case_life, render_case_life_by_outcome, render_case_life_log, render_trial_verdict_life

RCVD, FLD, NTFLD, DISP, MSHP_CODES, AGENCIES = get_dataframes()

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**Disposed Cases**")
    st.caption(post_last_updated(RCVD))
    render_sidebar()

st.markdown("<h1 style='text-align: center;'>Disposed Cases</h1>", unsafe_allow_html=True)
st.divider()

rcvd, fld, ntfld, disp = get_filtered_data()

render_disp_outcomes(disp)
render_disp_sankey(disp)
render_disp_breakdown(disp)
render_trial_verdicts(disp)
render_disp_volume(disp)
render_case_life(disp, FLD)
render_case_life_by_outcome(disp, FLD)
render_case_life_log(disp, FLD)
render_trial_verdict_life(disp, FLD)
