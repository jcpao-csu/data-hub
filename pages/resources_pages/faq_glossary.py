import yaml
import streamlit as st

with open("assets/docs/faq.yaml") as f:
    _CONTENT = yaml.safe_load(f)

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**FAQ & Glossary**")
    st.caption(
        "Frequently asked questions about the prosecutorial process and a glossary "
        "of the stages a criminal case goes through in our Office."
    )

st.markdown("<h1 style='text-align: center;'>FAQ & Glossary</h1>", unsafe_allow_html=True)
st.divider()

st.subheader("Frequently Asked Questions")
for item in _CONTENT["faq"]:
    with st.expander(item["question"]):
        st.markdown(item["answer"])

st.divider()

st.subheader("Glossary — Stages of a Case")
for item in _CONTENT["glossary"]:
    with st.expander(item["term"]):
        st.markdown(item["definition"])
