import streamlit as st
from read_data import get_dataframes

RCVD, FLD, NTFLD, DISP, MSHP_CODES, AGENCIES = get_dataframes()

# Page-scoped session state keys (avoids conflict with global sidebar filters)
_DEFAULTS = {
    "glossary_df":        MSHP_CODES,
    "glossary_legacy":    False,
    "glossary_category":  [],
    "glossary_severity":  "All",
}
for key, val in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


def _update_df():
    df = MSHP_CODES.copy()

    if st.session_state["glossary_legacy"]:
        df = df.loc[~df["legacy"]].reset_index(drop=True)

    if st.session_state["glossary_category"]:
        df = df.loc[df["jcpao_category"].isin(st.session_state["glossary_category"])].reset_index(drop=True)

    sev = st.session_state["glossary_severity"]
    if sev != "All":
        if sev == "O":
            df = df.loc[df["severity"].isin(["A", "U"])].reset_index(drop=True)
        else:
            df = df.loc[df["severity"] == sev].reset_index(drop=True)

    st.session_state["glossary_df"] = df


def _reset_filters():
    st.session_state["glossary_legacy"]   = False
    st.session_state["glossary_category"] = []
    st.session_state["glossary_severity"] = "All"
    st.session_state["glossary_df"]       = MSHP_CODES


_SEV_OPTIONS = {
    "All": "All Charge Codes",
    "F":   "Felony",
    "M":   "Misdemeanor",
    "I":   "Infraction",
    "L":   "Ordinance",
    "O":   "Other",
}

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**Missouri Criminal Charge Codes Glossary**")
    st.caption("Learn more about the unique criminal charge codes in the state of Missouri.")

    with st.expander("**Glossary Filters**", expanded=True):
        with st.form("glossary_filters", clear_on_submit=False, border=False):

            st.toggle(
                ":blue-background[:blue[**Active Charge Codes Only**] 🚔]",
                key="glossary_legacy",
                help="Filter to only charge codes that are currently active.",
                width="stretch",
            )

            st.multiselect(
                ":blue-background[:blue[**Charge Code Category ^**] 📖]",
                options=sorted(MSHP_CODES["jcpao_category"].dropna().unique().tolist()),
                default=[],
                key="glossary_category",
                help="Select up to five charge code categories.",
                max_selections=5,
                placeholder="All",
                width="stretch",
            )

            st.selectbox(
                ":blue-background[:blue[**Charge Code Severity**] ⚖️]",
                options=list(_SEV_OPTIONS.keys()),
                format_func=lambda x: _SEV_OPTIONS[x],
                key="glossary_severity",
                help="Filter charge codes by severity.",
                width="stretch",
            )

            st.form_submit_button(
                "Apply Filters",
                icon=":material/filter_alt:",
                type="primary",
                on_click=_update_df,
                use_container_width=True,
            )

    st.button(
        "Reset Filters",
        on_click=_reset_filters,
        type="secondary",
        icon="🔄",
        use_container_width=True,
        help="Restore all filters to their default values.",
    )

    st.divider()
    st.caption(
        "^ Charge codes are manually grouped into categories established by the JCPAO, "
        "derived in part from the National Crime Information Center (NCIC) classification "
        "system maintained by the FBI and adopted by the Missouri State Highway Patrol. "
        "[Reference](https://www.mshp.dps.missouri.gov/CJ08Client/Home/ChargeCode)"
    )

st.markdown("<h1 style='text-align: center;'>MSHP Charge Codes Glossary</h1>", unsafe_allow_html=True)
st.divider()

_DISPLAY_COLS = ["charge_code", "short_desc", "long_desc", "severity", "class", "jcpao_category"]

st.info(f"Displaying {len(st.session_state['glossary_df']):,} charge codes based on current filter selections", icon=":material/info:")
st.dataframe(
    data=st.session_state["glossary_df"][_DISPLAY_COLS],
    use_container_width=True,
    height=1000,
    hide_index=True,
)
