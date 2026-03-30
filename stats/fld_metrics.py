# stats/fld_metrics.py
# Summary metric cards for the filed cases page:
#   (a) file rate % (filed / filed+not-filed, excluding PFI)
#   (b) median days referral → filed (mean in delta)
#   (c) % of filed cases whose lead charge is a felony
#   (d) filed cases with no matching disposition record (still open)

import pandas as pd
import streamlit as st


def _compute_file_rate(fld: pd.DataFrame, ntfld: pd.DataFrame) -> dict:
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    ntfld_clean = ntfld.loc[ntfld["min_ntfld_rank"] != 3]  # exclude PFI
    ntfld_clean = ntfld_clean.loc[~ntfld_clean["pbk_num"].isin(fld["pbk_num"])]  # exclude cases also filed

    n_filed    = fld["pbk_num"].nunique()
    n_notfiled = ntfld_clean["pbk_num"].nunique()
    total      = n_filed + n_notfiled
    rate       = round(n_filed / total * 100, 1) if total else 0.0

    fld_counts   = fld.groupby("period")["pbk_num"].nunique().reindex(full_index, fill_value=0)
    ntfld_counts = ntfld_clean.groupby("period")["pbk_num"].nunique().reindex(full_index, fill_value=0)
    period_total = fld_counts + ntfld_counts
    sparkline    = (
        (fld_counts / period_total * 100)
        .where(period_total > 0, other=0.0)
        .round(1)
        .tolist()
    )

    return {"rate": rate, "n_filed": n_filed, "total": total, "sparkline": sparkline}


def _compute_ref_to_file(fld: pd.DataFrame) -> dict:
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    df = fld.copy()
    df["days"] = (
        pd.to_datetime(df["earliest_fld_date"]) - pd.to_datetime(df["ref_date"])
    ).dt.days
    df = df.loc[df["days"] >= 0]

    overall_median = round(df["days"].median(), 1) if not df.empty else 0.0
    overall_mean   = round(df["days"].mean(),   1) if not df.empty else 0.0

    sparkline = (
        df.groupby("period")["days"]
        .median()
        .reindex(full_index, fill_value=0)
        .round(1)
        .tolist()
    )

    return {"median": overall_median, "mean": overall_mean, "sparkline": sparkline}


def _compute_felony_pct(fld: pd.DataFrame) -> dict:
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    total        = fld["pbk_num"].nunique()
    felony_mask  = fld["fld_lead_sev"] == "F"
    n_felony     = fld.loc[felony_mask, "pbk_num"].nunique()
    pct          = round(n_felony / total * 100, 1) if total else 0.0

    felony_counts = fld.loc[felony_mask].groupby("period")["pbk_num"].nunique().reindex(full_index, fill_value=0)
    total_counts  = fld.groupby("period")["pbk_num"].nunique().reindex(full_index, fill_value=0)
    sparkline = (
        (felony_counts / total_counts * 100)
        .where(total_counts > 0, other=0.0)
        .round(1)
        .tolist()
    )

    return {"pct": pct, "n_felony": n_felony, "total": total, "sparkline": sparkline}


def _compute_still_open(fld: pd.DataFrame, disp_all: pd.DataFrame) -> dict:
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    disposed_ids = set(disp_all["pbk_num"].dropna())
    open_mask    = ~fld["pbk_num"].isin(disposed_ids)

    total  = fld["pbk_num"].nunique()
    n_open = fld.loc[open_mask, "pbk_num"].nunique()
    pct    = round(n_open / total * 100, 1) if total else 0.0

    sparkline = (
        fld.loc[open_mask]
        .groupby("period")["pbk_num"]
        .nunique()
        .reindex(full_index, fill_value=0)
        .tolist()
    )

    return {"n_open": n_open, "pct": pct, "sparkline": sparkline}


def render_fld_metrics(
    fld: pd.DataFrame,
    ntfld: pd.DataFrame,
    disp_all: pd.DataFrame,
) -> None:
    """Render four summary metric cards for filed cases."""
    file_rate  = _compute_file_rate(fld, ntfld)
    ref_to_fld = _compute_ref_to_file(fld)
    felony     = _compute_felony_pct(fld)
    open_cases = _compute_still_open(fld, disp_all)

    st.markdown(
        "<style>[data-testid='stMetricDelta'] svg { display: none; }</style>",
        unsafe_allow_html=True,
    )

    configs = [
        {
            "label": "**File Rate**",
            "value": f"{file_rate['rate']:.1f}%",
            "delta": f"{file_rate['n_filed']:,} of {file_rate['total']:,} cases completed review",
        },
        {
            "label": "**Median Time to File**",
            "value": f"{ref_to_fld['median']:.0f} days",
            "delta": f"Mean: {ref_to_fld['mean']:.1f} days",
        },
        {
            "label": "**Felonies % of Filed Cases**",
            "value": f"{felony['pct']:.1f}%",
            "delta": f"{felony['n_felony']:,} of {felony['total']:,} filed cases",
        },
        {
            "label": "**Still Open**",
            "value": f"{open_cases['n_open']:,} cases",
            "delta": f"~ {open_cases['pct']:.1f}% of filed cases",
        },
    ]
    sparklines = [
        file_rate["sparkline"],
        ref_to_fld["sparkline"],
        felony["sparkline"],
        open_cases["sparkline"],
    ]

    cols = st.columns(4)
    for col, cfg, sparkline in zip(cols, configs, sparklines):
        with col:
            st.metric(
                label=cfg["label"],
                value=cfg["value"],
                delta=cfg["delta"],
                delta_color="off",
                height=185,
                chart_data=sparkline,
                chart_type="area",
                border=True,
            )
