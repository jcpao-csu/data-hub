# session_state.py
# JCPAO Public Dashboard — Session state, filter logic, and sidebar widgets
#
# USAGE (in app.py, before st.navigation):
#
#   from session_state import initialize_session_state, render_sidebar
#   initialize_session_state()
#   with st.sidebar:
#       render_sidebar()
#
# USAGE (in any page file):
#
#   from session_state import get_filtered_data
#   rcvd, fld, ntfld, disp = get_filtered_data()

import streamlit as st
from pathlib import Path
from datetime import date
import pandas as pd

# Data loading
# Imported here so session_state.py is the single source of truth for raw data.
# Pages should never import from read_data.py directly — always use
# get_filtered_data() below.

from read_data import RCVD, FLD, NTFLD, DISP, AGENCIES, MSHP_CODES

# Constants

_DATA_START = date(2016, 1, 1)

_PERIOD_OPTIONS: dict[str, str] = {
    "Y": "Annually", # by year
    "Q": "Quarterly", # by quarter
    "M": "Monthly", # by month
    "W": "Weekly", # by week
    "D": "Daily", # by day
}

_AGENCY_OPTIONS: dict[str, str] = {
    "All": "All Agencies",
    "Blue Springs PD": "Blue Springs PD",
    "Buckner PD": "Buckner PD",
    "Grain Valley PD": "Grain Valley PD",
    "Grandview PD": "Grandview PD",
    "Greenwood PD": "Greenwood PD",
    "Independence PD": "Independence PD",
    "Jackson County Sheriff": "Jackson County Sheriff",
    "JCDTF": "Jackson County Drug Task Force",
    "KCPD": "KCPD",
    "Lake Lotawana PD": "Lake Lotawana PD",
    "Lake Tapawingo PD": "Lake Tapawingo PD",
    "Lee's Summit PD": "Lee's Summit PD",
    "Lone Jack PD": "Lone Jack PD",
    "Missouri State Highway Patrol": "Missouri State Highway Patrol",
    "Oak Grove PD": "Oak Grove PD",
    "Raytown PD": "Raytown PD",
    "Sugar Creek PD": "Sugar Creek PD",
    "Other In-County": "Other In-County Agencies",
    "Other In-State": "Other In-State Agencies",
    "Out-of-State": "Out-of-State Agencies",
    "State Agencies": "State Agencies",
    "Federal Agencies": "Federal Agencies",
    "Other": "Other Agencies",
}

_RACE_OPTIONS: dict[str, str] = {
    "All": "All",
    "A": "Asian",
    "B": "Black / African American",
    "H": "Hispanic",
    "I": "American Indian / Alaska Native",
    "M": "Multiple",
    "P": "Pacific Islander",
    "W": "White (Non-Latino) / Caucasian",
    "U": "Unknown",
}

_SEX_OPTIONS: dict[str, str] = {
    "All": "All",
    "F": "Female",
    "M": "Male",
    "O": "Other",
    "U": "Unknown",
}

# Codebook

_CHARGE_CATEGORIES: list[str] = ["All"] + sorted(
    MSHP_CODES["jcpao_category"].dropna().unique().tolist()
)

# Default filter values

def _default_date_range() -> tuple[date, date]:
    today = date.today()
    return (date(today.year - 1, today.month, today.day), today)


_FILTER_DEFAULTS: dict = {
    "date_range_filter": _default_date_range,   # callable — evaluated at init time
    "period_freq_filter": "Y",
    "charge_category_filter": "All",
    "police_agency_filter": "All",
    "def_race_filter": "All",
    "def_sex_filter": "All",
}

# Session state initialization

def initialize_session_state() -> None:
    """
    Initialize all session state keys with their default values.
    Safe to call multiple times — only sets keys that don't already exist.
    Call this once in app.py before st.navigation().
    """
    for key, default in _FILTER_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default() if callable(default) else default

# Filtering logic

def _apply_date_filter(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """Filter a dataframe to the selected date range using the given date column."""
    date_range = st.session_state["date_range_filter"]

    # Guard: st.date_input returns a 1-tuple while user is mid-selection
    if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
        # return df
        st.warning("Incomplete date range. Please select a start and end date to filter the dashboard.")
        st.stop()

    start, end = date_range
    df[date_col] = pd.to_datetime(df[date_col], format="%Y-%m-%d", errors="coerce")
    mask = (df[date_col].dt.date >= start) & (df[date_col].dt.date <= end)
    return df.loc[mask].reset_index(drop=True)


def _apply_period_column(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """Add a 'period' column derived from the selected frequency and the given date column."""
    freq = st.session_state["period_freq_filter"]
    if freq:
        df = df.copy()
        df["period"] = df[date_col].dt.to_period(freq)
    return df


def _apply_shared_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply charge category, police agency, race, and sex filters (shared across all tables)."""

    # Charge category
    charge = st.session_state["charge_category_filter"]
    if charge != "All":
        col = "ESCAPE" if charge.upper() == "ESCAPE" else charge.lower().replace(" ", "_")
        if col in df.columns:
            df = df.loc[df[col].fillna(False)].reset_index(drop=True)

    # Police agency
    agency = st.session_state["police_agency_filter"]
    if agency != "All":
        if "agency_name" in df.columns:
            df = df.loc[df["agency_name"] == agency].reset_index(drop=True)

    # Defendant race
    race = st.session_state["def_race_filter"]
    if race != "All":
        if "def_race" in df.columns:
            df = df.loc[df["def_race"] == race].reset_index(drop=True)

    # Defendant sex
    sex = st.session_state["def_sex_filter"]
    if sex != "All":
        if "def_sex" in df.columns:
            df = df.loc[df["def_sex"] == sex].reset_index(drop=True)

    return df


def get_filtered_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Return (RCVD, FLD, NTFLD, DISP) filtered and annotated per the current
    session state filter selections.

    Call this at the top of any dashboard page:

        rcvd, fld, ntfld, disp = get_filtered_data()

    Each returned dataframe includes a 'period' column for use in Altair charts.
    """
    # Each table has a different primary date column
    table_configs = [
        (RCVD,  "ref_date"), # load_rcvd()
        (FLD,   "earliest_fld_date"), # load_fld()
        (NTFLD, "earliest_ntfld_date"), # load_ntfld()
        (DISP,  "earliest_disp_date"), # load_disp()
    ]

    results = []
    for df, date_col in table_configs:
        df = _apply_date_filter(df, date_col)
        df = _apply_period_column(df, date_col)
        df = _apply_shared_filters(df)
        results.append(df)

    return tuple(results)  # (rcvd, fld, ntfld, disp)

# Reset

def reset_filters() -> None:
    """Reset all filter session state keys to their defaults. Use as on_click callback."""
    for key, default in _FILTER_DEFAULTS.items():
        st.session_state[key] = default() if callable(default) else default

# Sidebar widget rendering

def render_sidebar(
    date_range_disabled: bool = False, 
    period_freq_disabled: bool = False, 
    charge_category_disabled: bool = False, 
    police_agency_disabled: bool = False, 
    def_race_disabled: bool = False, 
    def_sex_disabled: bool = False, 
    submit_button_disabled: bool = False,
    reset_button_disabled: bool = False,
    color: str = "blue"
) -> None:
    """
    Render all dashboard filter widgets into whatever container this is called from.
    Intended to be called inside `with st.sidebar:` in app.py.

    Widgets are wrapped in a form so filters are applied together on submit,
    avoiding unnecessary reruns while the user is adjusting multiple filters.

    Args:
        disabled:   Pass True to disable all widgets (e.g., on a loading screen).
        color:      Streamlit color name for widget label styling.
    """

    def _label(text: str, icon: str) -> str:
        return f":{color}-background[:{color}[**{text}**] {icon}]"

    with st.expander("**Dashboard Filters**", expanded=True):
        with st.form("sidebar_filters", clear_on_submit=False, border=False):

            # -- Date range --
            st.date_input(
                _label("Date Range", "📆"),
                value=st.session_state["date_range_filter"],
                min_value=_DATA_START,
                max_value=date.today(),
                format="MM/DD/YYYY",
                key="date_range_filter",
                help="View selected date range. Available data begins January 2016.",
                disabled=date_range_disabled,
            )

            # -- Period frequency --
            st.selectbox(
                _label("Period View", "⏳"),
                options=list(_PERIOD_OPTIONS.keys()),
                format_func=lambda x: _PERIOD_OPTIONS[x],
                index=list(_PERIOD_OPTIONS.keys()).index(
                    st.session_state["period_freq_filter"]
                ),
                key="period_freq_filter",
                help="View by selected time granularity (e.g. annually, monthly).",
                disabled=period_freq_disabled,
            )

            # -- Charge category --
            st.selectbox(
                _label("Charge Code Category^", "📖"),
                options=_CHARGE_CATEGORIES,
                index=_CHARGE_CATEGORIES.index(
                    st.session_state["charge_category_filter"]
                ),
                key="charge_category_filter",
                help="View cases containing at least one charge under the selected category.",
                disabled=charge_category_disabled,
            )

            # -- Police agency --
            st.selectbox(
                _label("Referring Police Agency", "🚔"),
                options=list(_AGENCY_OPTIONS.keys()),
                format_func=lambda x: _AGENCY_OPTIONS[x],
                index=list(_AGENCY_OPTIONS.keys()).index(
                    st.session_state["police_agency_filter"]
                ),
                key="police_agency_filter",
                help="View cases referred by the selected police agency.",
                disabled=police_agency_disabled,
            )

            # -- Defendant race --
            st.selectbox(
                _label("Defendant Race", "👤"),
                options=list(_RACE_OPTIONS.keys()),
                format_func=lambda x: _RACE_OPTIONS[x],
                index=list(_RACE_OPTIONS.keys()).index(
                    st.session_state["def_race_filter"]
                ),
                key="def_race_filter",
                help="View cases where the suspect/defendant matches the selected race.",
                disabled=def_race_disabled,
            )

            # -- Defendant sex --
            st.selectbox(
                _label("Defendant Sex", "🚻"),
                options=list(_SEX_OPTIONS.keys()),
                format_func=lambda x: _SEX_OPTIONS[x],
                index=list(_SEX_OPTIONS.keys()).index(
                    st.session_state["def_sex_filter"]
                ),
                key="def_sex_filter",
                help="View cases where the suspect/defendant matches the selected sex.",
                disabled=def_sex_disabled,
            )

            # -- Submit --
            st.form_submit_button(
                label="Apply Filters",
                icon=":material/filter_alt:",
                type="primary",
                disabled=submit_button_disabled,
                use_container_width=True,
            )

    # Reset button lives outside the form so it's always clickable
    st.button(
        "Reset Filters",
        on_click=reset_filters,
        type="secondary",
        icon="🔄",
        disabled=reset_button_disabled,
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
