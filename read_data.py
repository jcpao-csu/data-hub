import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Engine
from dotenv import load_dotenv
import os

load_dotenv("../jcpao-csu.env", override=True)  # points up to parent directory


# --- Local .env file ---
# from dotenv import load_dotenv
# import os
# load_dotenv(override=True)
# conn_string = os.getenv("DATABASE_URL")


# --- Initialize database connection pool ---

# SQLALCHEMY - Define get_engine()
@st.cache_resource
def get_engine(database_url):
    return create_engine(
        database_url, # st.secrets["sqlalchemy"]["database_url"]
        pool_size=10,
        max_overflow=5,
        pool_pre_ping=True,
        pool_timeout=60,
    )

# Establish NEON database connection (via sqlalchemy)
try:
    database_url = st.secrets["sqlalchemy"]["database_url"]
except Exception:
    database_url = os.getenv("SQLALCHEMY_DATABASE_URL")

# Attempt connection
try:
    engine = get_engine(database_url)
except Exception as e:
    print(f"{e}")
    st.stop()

# SQLALCHEMY: Read tables from NeonDB
@st.cache_data(show_spinner="Loading data, please wait...") # ttl=3600*24*7, 
def query_table(sql_query: str, _engine: Engine = engine) -> pd.DataFrame:
    if _engine is None:
        return pd.DataFrame()

    try:
        if isinstance(_engine, Engine):
            return pd.read_sql(sql_query, _engine)

        else:
            return pd.read_sql(sql_query, _engine)

    except Exception as e:
        st.error(f"Database query failed: {e}")
        return pd.DataFrame()


# --- Filter FLD pbk_num from NTFLD df ---
@st.cache_data(show_spinner="Loading data, please wait...") # ttl=3600*24*7
def filter_ntfld(ntfld: pd.DataFrame, fld: pd.DataFrame) -> pd.DataFrame:
    fld_cases = fld['pbk_num'].unique().tolist()
    return ntfld[~ntfld['pbk_num'].isin(fld_cases)]


# Query tables 
RCVD = query_table("SELECT * FROM karpel_rcvd")
FLD = query_table("SELECT * FROM karpel_fld")
# NTFLD = filter_ntfld(query_table("SELECT * FROM karpel_ntfld"), FLD)
NTFLD = query_table("SELECT * FROM karpel_ntfld")
DISP = query_table("SELECT * FROM karpel_disp")

AGENCIES = query_table("SELECT * FROM agencies")
MSHP_CODES = query_table("SELECT * FROM mshp_charge_codes")
POLICE_REPORTS = query_table("SELECT * FROM police_reports")

# Return static dataframes (for use in other pages)
def get_dataframes():
    return RCVD, FLD, NTFLD, DISP, MSHP_CODES, AGENCIES