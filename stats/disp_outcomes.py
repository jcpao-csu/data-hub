# stats/disp_outcomes.py
# Disposed case outcome metric cards — guilty plea, trial, diverted, nolle prosequi.
# Uses any_guilty_plea and any_trial booleans (independent counts, not mutually exclusive),
# min_disp_rank == 4 for diverted (Nolle — Diversion), and
# min_disp_rank in [5..11] excluding 7.5 for nolle prosequi (excludes diversion and acquittals).

import pandas as pd
import streamlit as st

_DAYS_PER_MONTH = 30


def _prepare_outcome_metric(disp: pd.DataFrame, mask: pd.Series) -> dict:
    """
    Compute total unique cases matching mask, a per-period sparkline, and
    30-day processing rate. Reindexes to the full period range so empty
    periods appear as 0 in the sparkline.
    """
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    subset = disp.loc[mask]
    total  = subset["pbk_num"].nunique()

    counts   = subset.groupby("period")["pbk_num"].nunique()
    counts   = counts.reindex(full_index, fill_value=0)
    sparkline = counts.tolist()

    days = max((pd.Timestamp(str(end)) - pd.Timestamp(str(start))).days, 1)
    rate = round(total / (days / _DAYS_PER_MONTH))

    return {"total": total, "sparkline": sparkline, "rate": rate}


_NOLLE_RANKS = {5, 6, 7, 8, 9, 10, 11}  # excludes 4 (diversion) and 7.5 (acquittal)


def render_disp_outcomes(disp: pd.DataFrame) -> None:
    """Render four st.metric cards: guilty plea, went to trial, diverted, nolle prosequi."""
    total_disp = disp["pbk_num"].nunique()

    guilty_plea = _prepare_outcome_metric(disp, disp["any_guilty_plea"] == True)
    trial       = _prepare_outcome_metric(disp, disp["any_trial"]       == True)
    diverted    = _prepare_outcome_metric(disp, disp["min_disp_rank"]   == 4)
    nolle       = _prepare_outcome_metric(disp, disp["min_disp_rank"].isin(_NOLLE_RANKS))

    def _pct(n: int) -> float:
        return round(n / total_disp * 100, 1) if total_disp else 0.0

    st.markdown(
        "<style>[data-testid='stMetricDelta'] svg { display: none; }</style>",
        unsafe_allow_html=True,
    )

    configs = [
        (guilty_plea, "***Guilty Plea***"),
        (trial,       "***Went to Trial***"),
        (diverted,    "***Diverted***"),
        (nolle,       "***Nolle Prosequi***"),
    ]

    cols = st.columns(4)
    for col, (data, label) in zip(cols, configs):
        pct = _pct(data["total"])
        with col:
            st.metric(
                label=label,
                value=f"{data['total']:,} cases",
                delta=f"~ {pct:.1f}% of disposed",
                delta_color="off",
                height=185,
                chart_data=data["sparkline"],
                chart_type="area",
                border=True,
            )
