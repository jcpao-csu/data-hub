import streamlit as st
from read_data import get_dataframes
from session_state import get_filtered_data, render_sidebar
from stats.last_updated import post_last_updated
from stats.fld_volume import render_fld_volume, render_file_rate, render_decision_time
from stats.fld_metrics import render_fld_metrics
from stats.fld_sevclass import render_fld_sevclass
from stats.fld_category import render_fld_category

RCVD, FLD, NTFLD, DISP, MSHP_CODES, AGENCIES = get_dataframes()

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**Filed Cases**")
    st.caption(post_last_updated(RCVD))
    render_sidebar()

st.markdown("<h1 style='text-align: center;'>Filed Cases</h1>", unsafe_allow_html=True)
st.divider()

# Equal-height bordered containers inside column pairs
st.markdown(
    "<style>div[data-testid='stHorizontalBlock'] [data-testid='stVerticalBlockBorderWrapper']"
    " { height: 100%; }</style>",
    unsafe_allow_html=True,
)

rcvd, fld, ntfld, disp = get_filtered_data()

render_fld_metrics(fld, ntfld, DISP)
render_fld_volume(fld)

col_rate, col_time = st.columns(2)
with col_rate:
    render_file_rate(fld, ntfld)
with col_time:
    render_decision_time(fld, ntfld)

col_sev, col_cat = st.columns(2)
with col_sev:
    render_fld_sevclass(fld)
with col_cat:
    render_fld_category(fld)


