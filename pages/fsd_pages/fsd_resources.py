import streamlit as st

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**FSD Resources**")
    st.caption(
        "Information on how to make child support payments and personal & professional "
        "development resources available for FSD participants."
    )

st.markdown("<h1 style='text-align: center;'>Resources</h1>", unsafe_allow_html=True)
st.divider()

with open('pages/fsd_pages/child_support.md', 'r', encoding='utf-8') as f:
    child_support = f.read()

with open('pages/fsd_pages/development.md', 'r', encoding='utf-8') as f:
    development = f.read() 

col_left, col_right = st.columns(2)

with col_left:
    st.markdown(child_support)

with col_right:
    st.markdown(development)

