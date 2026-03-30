# stats/rcvd_volume.py
# Visualizations for cases received:
#   - render_rcvd_volume          : total cases received by period (bar + line)
#   - render_rcvd_status_metrics  : metric cards — Filed / PFI / Not Filed / Under Review
#   - render_rcvd_status          : stacked bar of current case status (count / normalized)
#   - render_under_review         : Under Review cases by received period (bottleneck view)
#
# Note: fld_all and ntfld_all arguments expect the UNFILTERED DataFrames so that
# status lookups reflect all known outcomes, not just those within the date range filter.
# Only rcvd should be the filtered DataFrame.

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from streamlit_extras.metric_cards import style_metric_cards

_COLOR         = "#4da6ff"  # blue  — received
_UR_COLOR      = "#6b7a99"  # slate — under review
_DAYS_PER_MONTH = 30

_STATUS_ORDER  = ["Filed", "Pending Further Investigation", "Not Filed", "Under Review"]
_STATUS_COLORS = ["#3db87a", "#f28e2b", "#f5c842", "#6b7a99"]


# --- render_rcvd_volume ---

def _prepare_rcvd_volume(rcvd: pd.DataFrame) -> pd.DataFrame:
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    counts = (
        rcvd.groupby("period")["pbk_num"]
        .nunique()
        .reindex(full_index, fill_value=0)
    )
    counts.index.name = "period"
    counts = counts.reset_index().rename(columns={"pbk_num": "total_cases"})
    counts["period"] = counts["period"].astype(str)
    return counts


def _build_rcvd_volume_bar(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(color=_COLOR)
        .encode(
            x=alt.X("period:O", title=None),
            y=alt.Y("total_cases:Q", title=None),
            tooltip=[
                alt.Tooltip("period:O",       title="Period"),
                alt.Tooltip("total_cases:Q",  title="Cases Received", format=","),
            ],
        )
        .properties(width="container", title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"))
    )


def _build_rcvd_volume_line(df: pd.DataFrame) -> alt.Chart:
    hover = alt.selection_point(nearest=True, on="mouseover", fields=["period"], empty=False)
    tooltips = [
        alt.Tooltip("period:O",       title="Period"),
        alt.Tooltip("total_cases:Q",  title="Cases Received", format=","),
    ]
    base = alt.Chart(df).encode(
        x=alt.X("period:O", title="Period"),
        y=alt.Y("total_cases:Q", title="Cases Received"),
        tooltip=tooltips,
    )
    line = base.mark_line(color=_COLOR, strokeWidth=2, interpolate="monotone")
    points = (
        base.mark_point(color=_COLOR, filled=True, size=80)
        .encode(opacity=alt.condition(hover, alt.value(1), alt.value(0)))
        .add_params(hover)
    )
    rule = (
        base.mark_rule(strokeWidth=1)
        .encode(x="period:O", opacity=alt.condition(hover, alt.value(0.3), alt.value(0)))
    )
    return (rule + line + points).properties(width="container")


def render_rcvd_volume(rcvd: pd.DataFrame) -> None:
    df = _prepare_rcvd_volume(rcvd)
    _FREQ_LABEL = {"M": "Monthly", "Q": "Quarterly", "Y": "Yearly"}
    start, end  = st.session_state["date_range_filter"]
    freq        = st.session_state["period_freq_filter"]
    subtitle    = f"{_FREQ_LABEL.get(freq, freq)} totals · {pd.Timestamp(str(start)).strftime('%b %Y')} – {pd.Timestamp(str(end)).strftime('%b %Y')}"
    with st.container(border=True):
        st.header(":material/move_to_inbox: Cases Received")
        tab_bar, tab_line = st.tabs(["Bar Chart", "Line Chart"])
        with tab_bar:
            st.altair_chart(_build_rcvd_volume_bar(df, title="Cases Received", subtitle=subtitle), use_container_width=True)
        with tab_line:
            st.altair_chart(_build_rcvd_volume_line(df), use_container_width=True)


# --- shared prepare for status-based renders ---

def _prepare_rcvd_status(
    rcvd: pd.DataFrame,
    fld_all: pd.DataFrame,
    ntfld_all: pd.DataFrame,
) -> pd.DataFrame:
    """
    Assign each case in rcvd a current status using the full (unfiltered) fld and ntfld
    tables, then aggregate by period. fld_all and ntfld_all must be unfiltered so that
    outcomes outside the selected date range are still reflected correctly.
    """
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    fld_ids   = fld_all["pbk_num"].unique().tolist()
    pfi_ids   = ntfld_all.loc[ntfld_all["min_ntfld_rank"] == 3, "pbk_num"].unique().tolist()
    ntfld_ids = ntfld_all.loc[ntfld_all["min_ntfld_rank"] != 3, "pbk_num"].unique().tolist()

    rcvd = rcvd.copy()
    rcvd["current_status"] = np.select(
        [
            rcvd["pbk_num"].isin(fld_ids),
            rcvd["pbk_num"].isin(pfi_ids),
            rcvd["pbk_num"].isin(ntfld_ids),
        ],
        choicelist=["Filed", "Pending Further Investigation", "Not Filed"],
        default="Under Review",
    )

    # Period totals (reindexed) for % calculation
    total_per_period = (
        rcvd.groupby("period")["pbk_num"]
        .nunique()
        .reindex(full_index, fill_value=0)
        .rename("period_total")
        .rename_axis("period")
        .reset_index()
    )
    total_per_period["period"] = total_per_period["period"].astype(str)

    # Status counts per period
    chart_df = (
        rcvd.groupby(["period", "current_status"])["pbk_num"]
        .nunique()
        .reset_index(name="count")
    )
    chart_df["period"] = chart_df["period"].astype(str)

    # Ensure all period × status combos exist (fills zeros for missing combos)
    all_periods = total_per_period["period"].tolist()
    full_cross = pd.MultiIndex.from_product(
        [all_periods, _STATUS_ORDER], names=["period", "current_status"]
    )
    chart_df = (
        chart_df.set_index(["period", "current_status"])
        .reindex(full_cross, fill_value=0)
        .reset_index()
    )

    chart_df = chart_df.merge(total_per_period, on="period")
    chart_df["pct"] = (
        (chart_df["count"] / chart_df["period_total"])
        .where(chart_df["period_total"] > 0, other=0.0)
        .round(3)
    )
    return chart_df


# --- render_rcvd_status_metrics ---

def render_rcvd_status_metrics(
    rcvd: pd.DataFrame,
    fld_all: pd.DataFrame,
    ntfld_all: pd.DataFrame,
) -> None:
    """Four st.metric cards showing Filed / PFI / Not Filed / Under Review totals."""
    df = _prepare_rcvd_status(rcvd, fld_all, ntfld_all)
    start, end = st.session_state["date_range_filter"]
    days = max((pd.Timestamp(str(end)) - pd.Timestamp(str(start))).days, 1)
    periods = sorted(df["period"].unique())

    st.markdown(
        "<style>[data-testid='stMetricDelta'] svg { display: none; }</style>",
        unsafe_allow_html=True,
    )

    configs = [
        ("Filed",                         "**Filed**"),
        ("Pending Further Investigation", "**Pending Further Investigation**"),
        ("Not Filed",                     "**Not Filed**"),
        ("Under Review",                  "**Under Review**"),
    ]

    cols = st.columns(4)
    for col, (status, label) in zip(cols, configs):
        sub = (
            df[df["current_status"] == status]
            .set_index("period")
            .reindex(periods, fill_value=0)
        )
        total    = int(sub["count"].sum())
        sparkline = sub["count"].tolist()
        rate     = round(total / (days / _DAYS_PER_MONTH))

        with col:
            st.metric(
                label=label,
                value=f"{total:,} cases",
                delta=f"~ {rate:,} cases / month",
                delta_color="off",
                height=185,
                chart_data=sparkline,
                chart_type="area",
                border=True,
            )

    style_metric_cards(
        background_color="#0d1b2a",
        border_left_color="#4da6ff",
    )


# --- render_rcvd_status ---

def _build_rcvd_status_bar(df: pd.DataFrame, is_normalized: bool) -> alt.Chart:
    selection = alt.selection_point(fields=["current_status"], bind="legend")
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("period:O", title="Period", sort=None),
            y=alt.Y(
                "count:Q",
                title="Share of Cases Received" if is_normalized else "Cases Received",
                stack="normalize" if is_normalized else "zero",
                axis=alt.Axis(format=".0%") if is_normalized else alt.Axis(),
            ),
            color=alt.Color(
                "current_status:N",
                title="Case Status",
                scale=alt.Scale(domain=_STATUS_ORDER, range=_STATUS_COLORS),
                sort=_STATUS_ORDER,
            ),
            order=alt.Order("color_current_status_sort_index:Q"),
            opacity=alt.condition(selection, alt.value(1.0), alt.value(0.2)),
            tooltip=[
                alt.Tooltip("period:O",          title="Period"),
                alt.Tooltip("current_status:N",  title="Status"),
                alt.Tooltip("count:Q",           title="Cases",          format=","),
                alt.Tooltip("period_total:Q",    title="Total Received", format=","),
                alt.Tooltip("pct:Q",             title="% of Period",    format=".1%"),
            ],
        )
        .add_params(selection)
        .properties(width="container")
    )


def render_rcvd_status(
    rcvd: pd.DataFrame,
    fld_all: pd.DataFrame,
    ntfld_all: pd.DataFrame,
) -> None:
    df = _prepare_rcvd_status(rcvd, fld_all, ntfld_all)
    with st.container(border=True):
        st.header(":material/account_tree: Status of Cases Received")
        view = st.segmented_control(
            label=None,
            options=["Count", "Normalized (%)"],
            default="Count",
            key="rcvd_status_view",
            selection_mode="single",
        )
        st.altair_chart(
            _build_rcvd_status_bar(df, is_normalized=(view == "Normalized (%)")),
            use_container_width=True,
        )


# --- render_under_review ---

def _apply_ur_shared_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply charge category, agency, race, and sex filters from session state to df."""
    charge = st.session_state.get("charge_category_filter", "All")
    if charge != "All":
        col = "ESCAPE" if charge.upper() == "ESCAPE" else charge.lower().replace(" ", "_")
        if col in df.columns:
            df = df.loc[df[col].fillna(False)].reset_index(drop=True)

    agency = st.session_state.get("police_agency_filter", "All")
    if agency != "All" and "agency_name" in df.columns:
        df = df.loc[df["agency_name"] == agency].reset_index(drop=True)

    race = st.session_state.get("def_race_filter", "All")
    if race != "All" and "def_race" in df.columns:
        df = df.loc[df["def_race"] == race].reset_index(drop=True)

    sex = st.session_state.get("def_sex_filter", "All")
    if sex != "All" and "def_sex" in df.columns:
        df = df.loc[df["def_sex"] == sex].reset_index(drop=True)

    return df


def _prepare_under_review_ts(
    rcvd_all: pd.DataFrame,
    fld_all: pd.DataFrame,
    ntfld_all: pd.DataFrame,
    disp_all: pd.DataFrame,
) -> pd.DataFrame:
    """
    Daily backlog of cases Under Review from 2016-01-01 through today.

    Shared filters (charge category, agency, race, sex) are applied to rcvd_all
    at the onset so the backlog totals reflect those subsets. Closes are
    implicitly filtered via rcvd_pbk, so no separate filtering of fld/ntfld/disp
    is needed.

    The full cumulative is always computed from 2016 to today regardless of the
    sidebar date range — date range is applied after to slice the display window
    only, preserving accurate backlog counts for cases received before the window.

    A case opens (+1) on ref_date and closes (-1) on the earliest date it
    appears in fld, ntfld (including PFI), or disp.
    """
    # Apply shared filters (charge category, agency, race, sex) at onset
    rcvd_all = _apply_ur_shared_filters(rcvd_all.copy())

    # Opens: +1 per unique case on ref_date
    rcvd_base = rcvd_all[["pbk_num", "ref_date"]].drop_duplicates("pbk_num").copy()
    rcvd_base["date"]   = pd.to_datetime(rcvd_base["ref_date"], errors="coerce")
    rcvd_base["change"] = 1
    opens = rcvd_base[["date", "change"]].dropna(subset=["date"])

    rcvd_pbk = set(rcvd_base["pbk_num"])

    # Closes: earliest date across fld, ntfld (incl. PFI), disp
    # Only include cases that appear in rcvd so closes never outnumber opens.
    fld_c = (
        fld_all.loc[fld_all["pbk_num"].isin(rcvd_pbk), ["pbk_num", "earliest_fld_date"]]
        .rename(columns={"earliest_fld_date": "date"})
    )
    ntfld_c = (
        ntfld_all.loc[ntfld_all["pbk_num"].isin(rcvd_pbk), ["pbk_num", "earliest_ntfld_date"]]
        .rename(columns={"earliest_ntfld_date": "date"})
    )
    disp_c = (
        disp_all.loc[disp_all["pbk_num"].isin(rcvd_pbk), ["pbk_num", "earliest_disp_date"]]
        .rename(columns={"earliest_disp_date": "date"})
    )

    closes = (
        pd.concat([fld_c, ntfld_c, disp_c])
        .assign(date=lambda d: pd.to_datetime(d["date"], errors="coerce"))
        .dropna(subset=["date"])
        .sort_values("date")
        .drop_duplicates("pbk_num", keep="first")
        .assign(change=-1)
        [["date", "change"]]
    )

    # Daily delta series over all data
    all_events = (
        pd.concat([opens, closes])
        .assign(date=lambda d: d["date"].dt.normalize())  # floor to midnight
    )

    daily_delta = (
        all_events.groupby("date")["change"]
        .sum()
        .sort_index()
    )


    # Reindex from earliest event to today so cumsum is globally correct
    full_idx = pd.date_range(start=daily_delta.index.min(), end=pd.Timestamp.now().normalize(), freq="D")
    daily_delta = daily_delta.reindex(full_idx, fill_value=0)

    cumulative = daily_delta.cumsum().clip(lower=0)

    start, end = st.session_state["date_range_filter"]
    start_ts = pd.Timestamp(str(start))
    end_ts   = pd.Timestamp(str(end))

    result = cumulative.loc[start_ts:end_ts].reset_index()
    result.columns = ["date", "under_review"]
    result["rolling_avg"] = result["under_review"].rolling(30, min_periods=1).mean().round(1)
    return result


_UR_AVG_COLOR   = "#f28e2b"  # orange — 30-day rolling average
_UR_EVENT_COLOR = "#c9d6e3"  # off-white — history annotations

_HISTORY_EVENTS = pd.DataFrame([
    {"date": pd.Timestamp("2020-03-12"), "label": "1"},
    {"date": pd.Timestamp("2020-04-16"), "label": "2"},
    {"date": pd.Timestamp("2021-07-21"), "label": "3"},
    {"date": pd.Timestamp("2025-01-03"), "label": "4"},
    {"date": pd.Timestamp("2025-01-06"), "label": "5"},
])

_HISTORY_FOOTNOTES = [
    "1  Mar 12, 2020 — Jackson County Courthouse operations suspended (COVID-19).",
    "2  Apr 16, 2020 — Courthouse closures extended (COVID-19).",
    "3  Jul 21, 2021 — Jean Peters Baker announces policy to prioritize violent crime over non-violent drug cases.",
    "4  Jan 3, 2025 — Melesa Johnson sworn into office.",
    "5  Jan 6, 2025 — Melesa Johnson expands prosecution efforts on domestic violence and drug cases.",
]


def _build_under_review_ts(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    hover = alt.selection_point(nearest=True, on="mouseover", fields=["date"], empty=False)

    tooltips = [
        alt.Tooltip("date:T",          title="Date",               format="%b %-d, %Y"),
        alt.Tooltip("under_review:Q",  title="Cases Under Review", format=","),
        alt.Tooltip("rolling_avg:Q",   title="30-Day Avg",         format=",.1f"),
    ]

    base = alt.Chart(df).encode(
        x=alt.X("date:T", title=None,
                axis=alt.Axis(tickCount="year", format="%Y"),
                scale=alt.Scale()),
        y=alt.Y("under_review:Q", title=None),
        tooltip=tooltips,
    )
    area   = base.mark_area(color=_UR_COLOR, opacity=0.2, interpolate="monotone")
    line   = base.mark_line(color=_UR_COLOR, strokeWidth=2, interpolate="monotone")
    points = (
        base.mark_point(color=_UR_COLOR, filled=True, size=80)
        .encode(opacity=alt.condition(hover, alt.value(1), alt.value(0)))
        .add_params(hover)
    )
    rule = (
        base.mark_rule(color="#6b7a99", strokeWidth=1)
        .encode(opacity=alt.condition(hover, alt.value(0.4), alt.value(0)))
    )
    avg_line = (
        alt.Chart(df)
        .mark_line(color=_UR_AVG_COLOR, strokeWidth=1.6, opacity=0.8, interpolate="monotone")
        .encode(
            x=alt.X("date:T", scale=alt.Scale()),
            y=alt.Y("rolling_avg:Q"),
        )
    )

    # History annotation rules and labels — filtered to visible date range
    # Events 4 and 5 are 3 days apart, stagger vertically to avoid overlap
    date_min = df["date"].min()
    date_max = df["date"].max()
    visible_events = _HISTORY_EVENTS[
        (_HISTORY_EVENTS["date"] >= date_min) & (_HISTORY_EVENTS["date"] <= date_max)
    ]
    events_normal  = visible_events[visible_events["label"] != "5"]
    events_stagger = visible_events[visible_events["label"] == "5"]

    event_rules = (
        alt.Chart(visible_events)
        .mark_rule(color=_UR_EVENT_COLOR, strokeWidth=1.2, opacity=0.4)
        .encode(x=alt.X("date:T", scale=alt.Scale()))
    )
    event_text = (
        alt.Chart(events_normal)
        .mark_text(align="left", dx=3, fontSize=10, fontWeight="bold",
                   color=_UR_EVENT_COLOR, opacity=0.6)
        .encode(
            x=alt.X("date:T", scale=alt.Scale()),
            y=alt.value(8),
            text="label:N",
        )
    )
    event_text_stagger = (
        alt.Chart(events_stagger)
        .mark_text(align="left", dx=3, fontSize=10, fontWeight="bold",
                   color=_UR_EVENT_COLOR, opacity=0.6)
        .encode(
            x=alt.X("date:T", scale=alt.Scale()),
            y=alt.value(22),
            text="label:N",
        )
    )

    return (
        area + line + rule + points + avg_line + event_rules + event_text + event_text_stagger
    ).properties(
        width="container",
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def render_under_review(
    rcvd_all: pd.DataFrame,
    fld_all: pd.DataFrame,
    ntfld_all: pd.DataFrame,
    disp_all: pd.DataFrame,
) -> None:
    """
    Running daily backlog of cases Under Review from 2016 to today.
    Ignores all sidebar filters. A case closes when it first appears in
    fld, ntfld (including PFI), or disp.
    """
    df = _prepare_under_review_ts(rcvd_all, fld_all, ntfld_all, disp_all)
    with st.container(border=True):
        st.altair_chart(
            _build_under_review_ts(
                df,
                title="Cases Under Review",
                subtitle=(
                    "Daily backlog of cases received but not yet filed, declined, or disposed. "
                    "Charge category, agency, race, and sex filters apply to the backlog totals. "
                    "Date range controls the display window only — cases received before the "
                    "selected start date are still counted in the running total."
                ),
            ),
            use_container_width=True,
        )
        st.divider()
        for note in _HISTORY_FOOTNOTES:
            st.caption(note)
