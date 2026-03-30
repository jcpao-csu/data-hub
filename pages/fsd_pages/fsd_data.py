import streamlit as st
from stats.fsd_stats import (
    get_fsd_dataframes,
    fsd_last_updated,
    initialize_fsd_session_state,
    render_fsd_sidebar,
    render_fsd_admin,
    render_fsd_admin_est,
    render_fsd_admin_enf,
    render_fsd_judicial_pat,
    render_fsd_judicial_enf,
)

ADMIN, ADMIN_EST, ADMIN_ENF, JUDICIAL_PAT, JUDICIAL_ENF = get_fsd_dataframes()

initialize_fsd_session_state()

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**Family Support Division (FSD)**")
    st.caption(f"Data as of {fsd_last_updated(ADMIN)}. Updated monthly.")
    period_view, date_range = render_fsd_sidebar()

st.markdown("<h1 style='text-align: center;'>Family Support Division</h1>", unsafe_allow_html=True)
st.divider()

with st.expander("**Administrative Caseload**", expanded=True):
    render_fsd_admin(ADMIN, period_view, date_range)

with st.expander("**Administrative Establishment**"):
    render_fsd_admin_est(ADMIN_EST, period_view, date_range)

with st.expander("**Administrative Enforcement**"):
    render_fsd_admin_enf(ADMIN_ENF, period_view, date_range)

with st.expander("**Judicial Paternity**"):
    render_fsd_judicial_pat(JUDICIAL_PAT, period_view, date_range)

with st.expander("**Judicial Enforcement**"):
    render_fsd_judicial_enf(JUDICIAL_ENF, period_view, date_range)
