# stats/ytd_totals.py
# Total cases processed year-to-date, with YoY difference and sparkline of annual YTD (comparative) totals

import pandas as pd
import streamlit as st

from great_tables import GT, loc
from great_tables.style import text

from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.great_tables import great_tables

from stats.gt_theme import apply_dark_theme, GT_GREEN, GT_RED


def _ytd_counts(df: pd.DataFrame, date_col: str) -> pd.Series:
    """
    For each year in the data, count cases up to today's month/day.
    Returns a Series of annual YTD counts indexed by year (used as sparkline).
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])

    today = pd.Timestamp.today()
    mask = (
        (df[date_col].dt.month < today.month) |
        (
            (df[date_col].dt.month == today.month) &
            (df[date_col].dt.day <= today.day)
        )
    )
    df = df[mask].copy()
    df["year"] = df[date_col].dt.year

    full_years = range(2016, today.year + 1)

    return (
        df.groupby("year")["pbk_num"]
        .nunique()
        .reindex(full_years, fill_value=0)
        .sort_index()
    )


def _prepare_ytd_table(data: pd.Series) -> pd.DataFrame:
    """Wrangle annual YTD counts into a table-ready DataFrame with % change column."""
    df = data.reset_index().copy()
    df["percent_change"] = (df["pbk_num"].pct_change() * 100).round(1)
    return df


def _build_gt_table(df: pd.DataFrame, table_name: str) -> GT:
    current_year = pd.Timestamp.today().year
    gt = (
        GT(df)
        .tab_header(
            title=f"Total Cases {table_name}",
            subtitle="YTD totals with YOY % Change",
        )
        .cols_label(
            year="Year",
            pbk_num="Total Cases",
            percent_change="% Change (YoY)",
        )
        .fmt_integer(columns="pbk_num")
        .fmt_number(columns="percent_change", decimals=1, force_sign=True)
        .sub_missing(columns="percent_change", missing_text="—")
        .tab_style(
            style=text(color=GT_GREEN, weight="bold"),
            locations=loc.body(columns="percent_change", rows=lambda df: df["percent_change"] > 0),
        )
        .tab_style(
            style=text(color=GT_RED, weight="bold"),
            locations=loc.body(columns="percent_change", rows=lambda df: df["percent_change"] < 0),
        )
        .tab_style(
            style=text(style="italic", weight="bold"),
            locations=loc.body(rows=lambda df: df["year"] == current_year),
        )
    )
    return apply_dark_theme(gt)


def render_ytd_metric(
    RCVD: pd.DataFrame | None = None,
    FLD: pd.DataFrame | None = None,
    NTFLD: pd.DataFrame | None = None,
    DISP: pd.DataFrame | None = None,
) -> None:
    """Render four st.metric cards with GT tables for YTD totals."""

    configs = [
        (RCVD,  "ref_date",            "**Total Received (YTD)**",  "Received"),
        (FLD,   "earliest_fld_date",   "**Total Filed (YTD)**",     "Filed"),
        (NTFLD, "earliest_ntfld_date", "**Total Not Filed (YTD)**", "Not Filed"),
        (DISP,  "earliest_disp_date",  "**Total Disposed (YTD)**",  "Disposed"),
    ]

    st.markdown(":orange-badge[⚠️ Unresponsive to filters]")
    cols = st.columns(4)
    for col, (df, date_col, label, table_name) in zip(cols, configs):
        data = _ytd_counts(df, date_col)
        table_data = _prepare_ytd_table(data)
        counts = data.tolist()

        if len(counts) < 2:
            with col:
                st.metric(label=label, value=f"{counts[-1] if counts else 0} cases")
            continue

        delta = counts[-1] - counts[-2]
        delta_pct = (
            f"{(delta / counts[-2] * 100):+.1f}%"
            if counts[-2] != 0 else "N/A"
        )

        with col:
            st.metric(
                label=label,
                value=f"{counts[-1]:,} cases",
                delta=f"{delta:+,} (YoY) | {delta_pct}",
                delta_color="normal",
                height=185,
                chart_data=counts,
                chart_type="area",
                border=True,
            )
            great_tables(_build_gt_table(table_data, table_name))

    style_metric_cards(
        background_color="#0d1b2a",
        border_left_color="#4da6ff",
    )
