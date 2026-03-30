"""Main Streamlit page that runs all navigation for JCPAO Dashboard"""

import streamlit as st
from pathlib import Path
from session_state import initialize_session_state

# --- Configure Streamlit page settings --- 

jcpao_logo = Path("assets/logo/jcpao_logo_750x750.png")

st.set_page_config(
    page_title="JCPAO Dashboard", # JCPAO staff-view
    page_icon=jcpao_logo, 
    layout="wide", # "centered" or "wide"
    initial_sidebar_state="expanded",
    menu_items={
        # 'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "mailto:ujcho@jacksongov.org", # To report a bug, please email
        'About': "The JCPAO Dashboard was developed by Joseph Cho (Crime Analyst) and the Crime Strategies Unit (CSU) of the Jackson County Prosecuting Attorney's Office. For questions, suggestions, or bugs, please reach out to Joseph Cho at ujcho@jacksongov.org!"
    }
)

# --- JCPAO Streamlit page logo --- 
st.logo(jcpao_logo, size="large", link="https://www.jacksoncountyprosecutor.com")

# --- Initialize session state ---
initialize_session_state()

# --- Page Navigation ---
pages = {
    "Prosecuting Cases": [
        st.Page("pages/TEMPLATE.py", title="Home"),
        # st.Page("pages/case_pages/main_view.py", title="Overview"),
        # st.Page("pages/case_pages/overview.py", title="Overview2"),
        # st.Page("pages/case_pages/rcvd_cases.py", title="Cases Received"),
        # st.Page("pages/case_pages/fld_cases.py", title="Cases Reviewed"),
        # st.Page("pages/case_pages/ntfld_cases.py", title="Cases Declined"),
        # st.Page("pages/case_pages/disp_cases.py", title="Cases Disposed"),
        # st.Page("pages/case_pages/demo_cases.py", title="Defendant Demographics"),
        st.Page("pages/case_pages/dashboard_faqs.py", title="Frequently Asked Questions")
    ],
    "Defendant Demographics": [
        # st.Page("pages/def_pages/demo_cases.py", title="Breakdown by Race"),
        # st.Page("pages/def_pages/by_sex.py", title="Breakdown by Sex"),
        # st.Page("pages/def_pages/by_age.py", title="Breakdown by Age"),
        st.Page("pages/def_pages/by_zipcode.py", title="Breakdown by ZIP Code"),
        # st.Page("pages/def_pages/prod.py", title="Defendant Production Map"),
    ],
    # "Violent Crime in KCMO": [
    #     st.Page("pages/violence_pages/shoot_review.py", title="Overview")
    # ],
    # "Domestic Violence": [
    #     st.Page("pages/dv_pages/dv_main.py", title="Overview"), # pages/dv_pages/
    #     st.Page("pages/dv_pages/dv_cases.py", title="Domestic Assault Cases"),
    #     st.Page("pages/dv_pages/ipvi_cases.py", title="Intimate Partner Violence (IPV)"),
    #     # st.Page("pages/dv_pages/harassment_cases.py", title="Harassment Cases"),
    #     # st.Page("pages/dv_pages/stalking_cases.py", title="Stalking Cases")
    # ],
    "Family Support Division (FSD)": [
        st.Page("pages/fsd_pages/fsd_main.py", title="Overview"),
        st.Page("pages/fsd_pages/fsd_data.py", title="Explore the Data"),
        st.Page("pages/fsd_pages/fsd_resources.py", title="Resources"),
    ],
    # "Other": [
    #     st.Page("pages/other_pages/blairs_law.py", title="Blair's Law"),
    #     st.Page("pages/other_pages/valentines_law.py", title="Valentine's Law")
    # ],
    "Resources": [
        st.Page("pages/resources_pages/about_jcpao.py", title="About the JCPAO"),
        st.Page("pages/resources_pages/learn_more.py", title="Process of a Case"),
        st.Page("pages/resources_pages/codes_glossary.py", title="Criminal Charge Codes"),
        st.Page("pages/resources_pages/faq_glossary.py", title="FAQ & Glossary"),
        st.Page("pages/resources_pages/report_search.py", title="Check the Status of Your Police Report #"),
    ],
}

pg = st.navigation(pages, position="top")
pg.run()