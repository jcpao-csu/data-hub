import streamlit as st

from read_data import POLICE_REPORTS

# Drop id column if present
_DF = POLICE_REPORTS.drop(columns=["id"], errors="ignore")

with st.sidebar:
    st.title("Jackson County Prosecuting Attorney's Office")
    st.write("**Police Report Search Tool**")
    st.caption(
        "Search for the status of a criminal case submitted to our Office using your "
        "police report number."
    )
    st.divider()
    st.caption(
        "If your case was filed, you can find the latest court information on "
        "[Case.net](https://www.courts.mo.gov/cnet/caseNoSearch.do)."
    )

st.markdown("<h1 style='text-align: center;'>Police Report Search Tool</h1>", unsafe_allow_html=True)
st.divider()

report_number = st.text_input(
    label="Enter your Police Report Number",
    placeholder="e.g. 24-12345",
)

if st.button("Search", icon=":material/search:"):
    if len(report_number) >= 5:
        result = _DF[_DF["Police Report Number"].fillna("").str.lower() == report_number.lower()]

        if not result.empty:
            total_cases = len(result)
            st.write(f"We found {total_cases} case(s) associated with Police Report *#{report_number}*:")

            for counter, (_, row) in enumerate(result.iterrows(), start=1):
                status = row["Case Status"].upper()

                if status == "RECEIVED":
                    st.markdown(
                        f"Case ({counter}/{total_cases}) was :blue[**RECEIVED**] on "
                        f"{row['Date Received'] or 'Date Unknown'} and submitted by the "
                        f"{row['Submitting Agency']}. This case is likely under review and "
                        f"pending criminal charges."
                    )
                elif status == "FILED":
                    url = (
                        f"https://www.courts.mo.gov/cnet/cases/newHeader.do"
                        f"?inputVO.caseNumber={row['Court Number']}"
                        f"&inputVO.courtId=CT16&inputVO.isTicket=false"
                    )
                    st.markdown(
                        f"Case ({counter}/{total_cases}) was :blue[**FILED**] by our Office on "
                        f"{row['Date Filed'] or 'Date Unknown'} and was submitted by the "
                        f"{row['Submitting Agency']} for review on "
                        f"{row['Date Received'] or 'Date Unknown'}. "
                        f"You can find more information on Case.net: "
                        f"[Court Number {row['Court Number']}]({url})."
                    )
                elif status == "NOT FILED":
                    st.markdown(
                        f"The Jackson County Prosecuting Attorney's Office "
                        f":blue[**DECLINED TO FILE CHARGES**] on Case ({counter}/{total_cases}) "
                        f"on {row['Date Not Filed'] or 'Date Unknown'} due to the following "
                        f"reason(s): {row['Reason Not Filed']}. This case was submitted by the "
                        f"{row['Submitting Agency']} for review on "
                        f"{row['Date Received'] or 'Date Unknown'}."
                    )
                elif status == "DISPOSED":
                    url = (
                        f"https://www.courts.mo.gov/cnet/cases/newHeader.do"
                        f"?inputVO.caseNumber={row['Court Number']}"
                        f"&inputVO.courtId=CT16&inputVO.isTicket=false"
                    )
                    st.markdown(
                        f"Case ({counter}/{total_cases}) was :blue[**DISPOSED**] on "
                        f"{row['Date Disposed'] or 'Date Unknown'} with the following "
                        f"outcome(s): {row['Disposed Outcome']}. This case was submitted by the "
                        f"{row['Submitting Agency']} for review on "
                        f"{row['Date Received'] or 'Date Unknown'}. "
                        f"You can find more information on Case.net: "
                        f"[Court Number {row['Court Number']}]({url})."
                    )

            st.dataframe(result.dropna(axis=1, how="all"), hide_index=True)

        else:
            st.info(
                "We could not match your Police Report Number to any cases submitted to our "
                "Office. This means the reported incident may still be under investigation and "
                "has not yet been submitted to our Office, or the incident has been submitted "
                "to another jurisdiction (e.g., municipal, juvenile, or federal court).",
                icon=":material/info:"
            )
    else:
        st.warning("Your report number must be at least five characters long.")
