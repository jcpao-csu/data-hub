import yaml
import streamlit as st
from pathlib import Path
from read_data import get_dataframes
from session_state import get_filtered_data, render_sidebar
from stats.last_updated import post_last_updated
from stats.case_totals import render_case_totals
from stats.special_laws import render_law_volume

_other = yaml.safe_load(Path("assets/docs/other.yaml").read_text())
_VALENTINES_NOTES = next(e["notes"] for e in _other["page"] if e["name"] == "About Valentine's Law")

RCVD, FLD, NTFLD, DISP, MSHP_CODES, AGENCIES = get_dataframes()

RCVD_VL  = RCVD[RCVD["valentines_law"] == True]
FLD_VL   = FLD[FLD["valentines_law"] == True]
NTFLD_VL = NTFLD[NTFLD["valentines_law"] == True]
DISP_VL  = DISP[DISP["valentines_law"] == True]

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**Valentine's Law**")
    st.caption(
        post_last_updated(RCVD_VL) +
        " Valentine's Law (RSMo §575.151) took effect August 28, 2024. "
        "Data reflects cases referred from 2016 onwards."
    )
    render_sidebar()

st.markdown("<h1 style='text-align: center;'>Valentine's Law</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>RSMo §575.151 — Aggravated Fleeing a Stop or Detention</h3>", unsafe_allow_html=True)
st.write(" ")

with st.expander("About Valentine's Law", expanded=False, icon="📋"):
    st.markdown(_VALENTINES_NOTES)

rcvd, fld, ntfld, disp = get_filtered_data()

rcvd_vl  = rcvd[rcvd["valentines_law"] == True]
fld_vl   = fld[fld["valentines_law"] == True]
ntfld_vl = ntfld[ntfld["valentines_law"] == True]
disp_vl  = disp[disp["valentines_law"] == True]

render_case_totals(
    rcvd_vl, fld_vl, ntfld_vl, disp_vl,
    RCVD=RCVD_VL, FLD=FLD_VL, NTFLD=NTFLD_VL, DISP=DISP_VL,
)

with st.container(border=True):
    render_law_volume(RCVD_VL, FLD_VL, NTFLD_VL, DISP_VL, "Valentine's Law")
st.space(size="xxsmall")
from stats.case_overview import render_case_volume
render_case_volume(rcvd_vl, fld_vl, ntfld_vl, disp_vl, FLD=FLD_VL, NTFLD=NTFLD_VL, DISP=DISP_VL)

