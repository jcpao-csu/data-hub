import yaml
import streamlit as st
from pathlib import Path
from read_data import get_dataframes
from session_state import get_filtered_data, render_sidebar
from stats.last_updated import post_last_updated
from stats.case_totals import render_case_totals
from stats.special_laws import render_law_volume

_other = yaml.safe_load(Path("assets/docs/other.yaml").read_text())
_BLAIRS_NOTES = next(e["notes"] for e in _other["page"] if e["name"] == "About Blair's Law")

RCVD, FLD, NTFLD, DISP, MSHP_CODES, AGENCIES = get_dataframes()

RCVD_BL  = RCVD[RCVD["blairs_law"] == True]
FLD_BL   = FLD[FLD["blairs_law"] == True]
NTFLD_BL = NTFLD[NTFLD["blairs_law"] == True]
DISP_BL  = DISP[DISP["blairs_law"] == True]

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**Blair's Law**")
    st.caption(
        post_last_updated(RCVD_BL) +
        " Blair's Law (RSMo §571.031) took effect August 28, 2024. "
        "Data reflects cases referred from 2016 onwards."
    )
    render_sidebar()

st.markdown("<h1 style='text-align: center;'>Blair's Law</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>RSMo §571.031 — Celebratory Gunfire</h3>", unsafe_allow_html=True)
st.write(" ")

with st.expander("About Blair's Law", expanded=False, icon="📋"):
    st.markdown(_BLAIRS_NOTES)

rcvd, fld, ntfld, disp = get_filtered_data()

rcvd_bl  = rcvd[rcvd["blairs_law"] == True]
fld_bl   = fld[fld["blairs_law"] == True]
ntfld_bl = ntfld[ntfld["blairs_law"] == True]
disp_bl  = disp[disp["blairs_law"] == True]

render_case_totals(
    rcvd_bl, fld_bl, ntfld_bl, disp_bl,
    RCVD=RCVD_BL, FLD=FLD_BL, NTFLD=NTFLD_BL, DISP=DISP_BL,
)

with st.container(border=True):
    render_law_volume(RCVD_BL, FLD_BL, NTFLD_BL, DISP_BL, "Blair's Law")

from stats.case_overview import render_case_volume
render_case_volume(rcvd_bl, fld_bl, ntfld_bl, disp_bl, FLD=FLD_BL, NTFLD=NTFLD_BL, DISP=DISP_BL)