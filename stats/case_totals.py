# stats/case_totals.py
# Total cases processed — received, filed, not filed, and disposed.
# Renders four st.metric cards with per-period sparkline and prior-period delta.

import pandas as pd
import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards

_DATA_START = pd.Timestamp("2016-01-01").date()

# Maps period_freq_filter → (days per period, rate label)
_FREQ_RATE = {
    "M": (365.25 / 12, "cases/mo"),
    "Q": (365.25 / 4,  "cases/qtr"),
    "Y": (365.25,      "cases/yr")
}

def _apply_non_date_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all session state filters except date range."""
    ss = st.session_state
    df = df.copy()

    charge = ss.get("charge_category_filter", "All")
    if charge != "All":
        col = "ESCAPE" if charge.upper() == "ESCAPE" else charge.lower().replace(" ", "_")
        if col in df.columns:
            df = df.loc[df[col].fillna(False)].reset_index(drop=True)

    agency = ss.get("police_agency_filter", "All")
    if agency != "All" and "agency_name" in df.columns:
        df = df.loc[df["agency_name"] == agency].reset_index(drop=True)

    race = ss.get("def_race_filter", "All")
    if race != "All" and "def_race" in df.columns:
        df = df.loc[df["def_race"] == race].reset_index(drop=True)

    sex = ss.get("def_sex_filter", "All")
    if sex != "All" and "def_sex" in df.columns:
        df = df.loc[df["def_sex"] == sex].reset_index(drop=True)

    return df


def _prepare_totals(
    df: pd.DataFrame,
    df_raw: pd.DataFrame | None,
    date_col: str | None,
) -> dict:
    """
    Compute total case count, per-period sparkline, and prior-period comparison.

    df: filtered DataFrame with 'period' column (from get_filtered_data).
    df_raw: unfiltered raw DataFrame used for prior-period lookup (optional).
    date_col: primary date column name in df_raw for prior-period filtering.
    """
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]

    total = df["pbk_num"].nunique()

    period_counts = df.groupby("period")["pbk_num"].nunique()
    full_index = pd.period_range(start=start, end=end, freq=freq)
    period_counts = period_counts.reindex(full_index, fill_value=0)
    sparkline = period_counts.tolist()

    days = max((pd.Timestamp(str(end)) - pd.Timestamp(str(start))).days, 1)
    days_per_period, rate_label = _FREQ_RATE.get(freq, (365.25 / 12, "cases/mo"))
    rate = round(total / (days / days_per_period))

    # Prior period comparison
    prior_count = None
    if df_raw is not None and date_col is not None:
        start_d = pd.Timestamp(str(start)).date()
        end_d   = pd.Timestamp(str(end)).date()
        span    = end_d - start_d
        prior_end   = start_d - pd.Timedelta(days=1)
        prior_start = prior_end - span

        if prior_start >= _DATA_START:
            filtered_raw = _apply_non_date_filters(df_raw)
            filtered_raw = filtered_raw.copy()
            filtered_raw[date_col] = pd.to_datetime(filtered_raw[date_col], errors="coerce")
            mask = (
                (filtered_raw[date_col].dt.date >= prior_start)
                & (filtered_raw[date_col].dt.date <= prior_end)
            )
            prior_count = filtered_raw.loc[mask, "pbk_num"].nunique()

    return {"total": total, "sparkline": sparkline, "rate": rate, "rate_label": rate_label, "prior_count": prior_count}


def render_case_totals(
    rcvd: pd.DataFrame,
    fld: pd.DataFrame,
    ntfld: pd.DataFrame,
    disp: pd.DataFrame,
    RCVD: pd.DataFrame | None = None,
    FLD: pd.DataFrame | None = None,
    NTFLD: pd.DataFrame | None = None,
    DISP: pd.DataFrame | None = None,
) -> None:
    """Render four st.metric cards: total received, filed, not filed, and disposed."""

    configs = [
        (rcvd,  RCVD,  "ref_date",            "**Total Received**"),
        (fld,   FLD,   "earliest_fld_date",   "**Total Filed**"),
        (ntfld, NTFLD, "earliest_ntfld_date", "**Total Not Filed**"),
        (disp,  DISP,  "earliest_disp_date",  "**Total Disposed**"),
    ]

    # Compute prior period date info once for the st.info banner
    start_d, end_d = st.session_state["date_range_filter"]
    start_d = pd.Timestamp(str(start_d)).date()
    end_d   = pd.Timestamp(str(end_d)).date()
    span    = end_d - start_d
    prior_end   = start_d - pd.Timedelta(days=1)
    prior_start = prior_end - span
    show_delta  = prior_start >= _DATA_START

    if show_delta:
        st.info(
            f"Compares the selected date range to the preceding "
            f"{span.days + 1:,}-day period "
            f"({prior_start.strftime('%b %-d, %Y')} – {prior_end.strftime('%b %-d, %Y')}).",
            icon=":material/info:",
        )

    cols = st.columns(4)
    for col, (df, df_raw, date_col, label) in zip(cols, configs):
        data = _prepare_totals(df, df_raw, date_col)
        total = data["total"]
        prior = data["prior_count"]

        rate       = data["rate"]
        rate_label = data["rate_label"]
        if prior is not None and show_delta:
            diff      = total - prior
            pct       = (diff / prior * 100) if prior > 0 else 0.0
            delta_str = f"{pct:+.1f}% ({diff:+,}) | ~{rate:,} {rate_label}"
            d_color   = "normal"
        else:
            delta_str = f"~ {rate:,} {rate_label}"
            d_color   = "off"

        with col:
            st.metric(
                label=label,
                value=f"{total:,} cases",
                delta=delta_str,
                delta_color=d_color,
                # height=180,
                chart_data=data["sparkline"],
                chart_type="area"
            )

        style_metric_cards(
            background_color="#0d1b2a",
            border_left_color="#4da6ff",
        )
