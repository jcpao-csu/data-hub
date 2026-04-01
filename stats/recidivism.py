import numpy as np
import altair as alt
import pandas as pd
import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards

_DATA_START = pd.Timestamp("2016-01-01").date()


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


# ---------------------------------------------------------------------------
# Core prep — run on FULL dataset to get accurate first-seen dates
# ---------------------------------------------------------------------------

def _compute_first_seen(rcvd_full: pd.DataFrame) -> pd.DataFrame:
    """
    Using the full unfiltered dataset, compute each defendant's
    first-ever referral date. This ensures defendants referred before
    the current filter window are still correctly flagged as prior.

    Returns a df with columns: pbk_def_num, first_ref_date
    """
    df = rcvd_full.copy()

    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")

    # Drop rows with blank/null defendant ID
    df = df.loc[df["pbk_def_num"].notna() & (df["pbk_def_num"].astype(str).str.strip() != "")]

    # Sort by ref_date, then case number (pbk_num) as tiebreaker
    df = df.sort_values(["ref_date", "pbk_num"], ascending=[True, True])

    # First appearance per defendant across entire history
    first_seen = (
        df.drop_duplicates(subset=["pbk_def_num"], keep="first")[["pbk_def_num", "ref_date"]]
        .rename(columns={"ref_date": "first_ref_date"})
    )

    return first_seen


def _prepare(rcvd: pd.DataFrame, rcvd_full: pd.DataFrame) -> pd.DataFrame:
    """
    Merge first-seen dates onto the filtered dataset and flag each
    case as new or prior referral.
    """
    df = rcvd.copy()

    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")

    # Drop blank defendant IDs
    df = df.loc[df["pbk_def_num"].notna() & (df["pbk_def_num"].astype(str).str.strip() != "")]

    # Sort filtered df
    df = df.sort_values(["ref_date", "pbk_num"], ascending=[True, True])

    # Merge in first-seen dates from full history
    first_seen = _compute_first_seen(rcvd_full)
    df = df.merge(first_seen, on="pbk_def_num", how="left")

    # Flag: if this referral IS the first-ever referral, it's new
    df["referral_type"] = np.where(
        df["ref_date"] == df["first_ref_date"],
        "New Defendant",
        "Prior Referral",
    )

    return df


# ---------------------------------------------------------------------------
# Chart 1 — New vs. Prior Referral Rate by Period
# ---------------------------------------------------------------------------

def _build_referral_type_chart(df: pd.DataFrame, is_normalized: bool) -> alt.Chart:
    type_order  = ["New Defendant", "Prior Referral"]
    type_colors = ["#4da6ff", "#e05c5c"]

    total_per_period = (
        df.groupby("period")["pbk_num"]
        .nunique()
        .rename("period_total")
    )

    chart_df = (
        df.groupby(["period", "referral_type"])["pbk_num"]
        .nunique()
        .reset_index(name="count")
        .assign(period=lambda d: d["period"].astype(str))
    )

    chart_df = chart_df.merge(
        total_per_period.reset_index().assign(period=lambda d: d["period"].astype(str)),
        on="period",
    )
    chart_df["pct"] = (chart_df["count"] / chart_df["period_total"]).round(3)

    return (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("period:O", title=None, sort=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y(
                "count:Q",
                title="Share of Cases" if is_normalized else "Cases Referred",
                stack="normalize" if is_normalized else "zero",
                axis=alt.Axis(format=".0%") if is_normalized else alt.Axis(),
            ),
            color=alt.Color(
                "referral_type:N",
                title="Defendant Type",
                scale=alt.Scale(domain=type_order, range=type_colors),
                sort=type_order,
            ),
            order=alt.Order("color_referral_type_sort_index:Q"),
            tooltip=[
                alt.Tooltip("period:O",         title="Period"),
                alt.Tooltip("referral_type:N",  title="Defendant Type"),
                alt.Tooltip("count:Q",          title="Cases"),
                alt.Tooltip("period_total:Q",   title="Total Cases in Period"),
                alt.Tooltip("pct:Q",            title="% of Period", format=".1%"),
            ],
        )
        .properties(
            title=alt.TitleParams(
                "New vs. Previously Referred Defendants by Period",
                subtitle=(
                    "Tracks defendants referred to this office more than once. "
                    "'Prior Referral' indicates the defendant had at least one case "
                    "referred before the current period — based on full case history dating back to 2016."
                ),
                anchor="start",
                subtitleColor="#e8edf2",
            ),
            width="container",
        )
    )


# ---------------------------------------------------------------------------
# Chart 2 — Recurrence Count Distribution
# ---------------------------------------------------------------------------

def _build_recurrence_chart(rcvd_full: pd.DataFrame) -> alt.Chart:
    """
    Across the full dataset, how many defendants appeared exactly
    once, twice, three times, etc.?
    """
    df = rcvd_full.copy()
    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce") # convert ref date to datetime dtype
    df = df.loc[df["pbk_def_num"].notna() & (df["pbk_def_num"].astype(str).str.strip() != "")] # drop null / empty defendant IDs
    df = df.drop_duplicates(subset=["pbk_num"]) # drop dupicate case entries 

    # Count referrals per defendant
    referral_counts = (
        df.groupby("pbk_def_num")["pbk_num"]
        .nunique()
        .reset_index(name="n_referrals")
    )

    # Cap display at 6+ to avoid long tail cluttering the chart
    referral_counts["n_referrals_label"] = referral_counts["n_referrals"].apply(
        lambda x: "5 or more" if x >= 5 else str(x)
    )

    label_order = ["1", "2", "3", "4", "5 or more"]

    dist = (
        referral_counts.groupby("n_referrals_label")["pbk_def_num"]
        .nunique()
        .reindex(label_order, fill_value=0)
        .reset_index(name="n_defendants")
    )

    total_defs = dist["n_defendants"].sum()
    dist["pct"]              = (dist["n_defendants"] / total_defs).round(3)
    dist["pct_label"]        = (dist["pct"] * 100).round(1).astype(str) + "%"
    dist["n_defendants_fmt"] = dist["n_defendants"].apply(lambda x: f"{x:,}")

    return (
        alt.Chart(dist)
        .mark_bar(color="#4da6ff", opacity=0.85) # , cornerRadius=3
        .encode(
            x=alt.X(
                "n_referrals_label:O",
                sort=label_order,
                title="Number of Referrals",
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y("n_defendants:Q", title="Number of Defendants"),
            tooltip=[
                alt.Tooltip("n_referrals_label:O", title="Referrals"),
                alt.Tooltip("n_defendants_fmt:N",  title="Defendants"),
                alt.Tooltip("pct_label:N",         title="% of All Defendants"),
            ],
        )
        .properties(
            title=alt.TitleParams(
                text="Referral Frequency Distribution",
                subtitle="How many times has each defendant been referred? (full dataset)",
                fontSize=14,
                subtitleFontSize=11,
                subtitleColor="#777",
                anchor="start",
            ),
            width="container",
            height=300,
        )
        .configure_view(strokeWidth=0)
        .configure_axis(domain=False, grid=False)
    )


# ---------------------------------------------------------------------------
# Chart 3 — Median Days Between First and Second Referral by Year
# ---------------------------------------------------------------------------

def _build_time_between_chart(rcvd_full: pd.DataFrame) -> alt.Chart:
    """
    For defendants with 2+ referrals, compute days between
    their first and second referral, grouped by year of second referral.
    """
    df = rcvd_full.copy()
    df["ref_date"] = pd.to_datetime(df["ref_date"], errors="coerce")
    df = df.loc[df["pbk_def_num"].notna() & (df["pbk_def_num"].astype(str).str.strip() != "")]
    df = df.drop_duplicates(subset=["pbk_num"])
    df = df.sort_values(["pbk_def_num", "ref_date", "pbk_num"])

    # Rank each referral per defendant chronologically
    df["referral_rank"] = df.groupby("pbk_def_num").cumcount() + 1

    first  = df.loc[df["referral_rank"] == 1, ["pbk_def_num", "ref_date"]].rename(columns={"ref_date": "date_1"})
    second = df.loc[df["referral_rank"] == 2, ["pbk_def_num", "ref_date"]].rename(columns={"ref_date": "date_2"})

    gap_df = first.merge(second, on="pbk_def_num")
    gap_df["days_between"] = (gap_df["date_2"] - gap_df["date_1"]).dt.days
    gap_df["year"]         = gap_df["date_2"].dt.year

    agg = (
        gap_df.groupby("year")["days_between"]
        .agg(median_days="median", mean_days="mean", n="count")
        .reset_index()
    )
    agg["median_days"] = agg["median_days"].round(0).astype(int)
    agg["mean_days"]   = agg["mean_days"].round(0).astype(int)
    agg["year"]        = agg["year"].astype(str)

    # Melt for dual-line chart
    melted = agg.melt(
        id_vars=["year", "n"],
        value_vars=["median_days", "mean_days"],
        var_name="statistic",
        value_name="days",
    )
    melted["statistic"] = melted["statistic"].map({
        "median_days": "Median",
        "mean_days":   "Mean",
    })

    return (
        alt.Chart(melted)
        .mark_line(point=True)
        .encode(
            x=alt.X("year:O", title="Year of Second Referral", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("days:Q", title="Days Between 1st and 2nd Referral"),
            color=alt.Color(
                "statistic:N",
                title=None,
                scale=alt.Scale(
                    domain=["Median", "Mean"],
                    range=["#4da6ff", "#f28e2b"],
                ),
            ),
            strokeDash=alt.StrokeDash(
                "statistic:N",
                scale=alt.Scale(
                    domain=["Median", "Mean"],
                    range=[[1, 0], [4, 2]],
                ),
            ),
            tooltip=[
                alt.Tooltip("year:O",      title="Year"),
                alt.Tooltip("statistic:N", title="Statistic"),
                alt.Tooltip("days:Q",      title="Days"),
                alt.Tooltip("n:Q",         title="Defendants"),
            ],
        )
        .properties(
            title=alt.TitleParams(
                text="Time Between First and Second Referral",
                subtitle="Median and mean days, by year of second referral (full dataset)",
                fontSize=14,
                subtitleFontSize=11,
                subtitleColor="#777",
                anchor="start",
            ),
            width="container",
            height=300,
        )
        .configure_view(strokeWidth=0)
        .configure_axis(domain=False, grid=False)
    )


# ---------------------------------------------------------------------------
# Defendant donut chart — first-time vs. returning, unique defendant count
# ---------------------------------------------------------------------------

_DEF_TYPE_ORDER  = ["First-Time", "Returning"]
_DEF_TYPE_COLORS = ["#4da6ff", "#e05c5c"]


def _prepare_defendant_donut(df_prepared: pd.DataFrame) -> pd.DataFrame:
    """
    Classify unique defendants as First-Time or Returning relative to the
    current filter window start. A defendant is First-Time if their first_ref_date
    (across all history) falls on or after the filter start — regardless of how
    many cases they have within the window.
    """
    start, _ = st.session_state["date_range_filter"]
    filter_start = pd.Timestamp(str(start))

    def_df = (
        df_prepared
        .drop_duplicates("pbk_def_num")[["pbk_def_num", "first_ref_date"]]
        .copy()
    )
    def_df["first_ref_date"] = pd.to_datetime(def_df["first_ref_date"])
    def_df["defendant_type"] = np.where(
        def_df["first_ref_date"] >= filter_start,
        "First-Time",
        "Returning",
    )

    counts = (
        def_df.groupby("defendant_type")["pbk_def_num"]
        .nunique()
        .reindex(_DEF_TYPE_ORDER, fill_value=0)
        .reset_index(name="count")
    )
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total * 100).round(1) if total else 0.0
    return counts


def _build_defendant_donut(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    """Donut chart — unique defendants broken down by first-time vs. returning."""
    total = int(df["count"].sum())

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=alt.Color(
            "defendant_type:N",
            sort=_DEF_TYPE_ORDER,
            scale=alt.Scale(domain=_DEF_TYPE_ORDER, range=_DEF_TYPE_COLORS),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("defendant_type:N", title="Defendant Type"),
            alt.Tooltip("count:Q",          title="Defendants", format=","),
            alt.Tooltip("pct:Q",            title="% of Total", format=".1f"),
        ],
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    center_df = pd.DataFrame({"top": [f"{total:,}"], "sub": ["unique defendants"]})
    center_total = (
        alt.Chart(center_df)
        .mark_text(size=18, fontWeight="bold", color="#e8edf2", dy=-9)
        .encode(text="top:N", tooltip=alt.value(None))
    )
    center_sub = (
        alt.Chart(center_df)
        .mark_text(size=11, color="#6b7a99", dy=9)
        .encode(text="sub:N", tooltip=alt.value(None))
    )

    return (arc + center_total + center_sub).properties(
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


# ---------------------------------------------------------------------------
# Defendant metric cards — totals, % new, % returning
# ---------------------------------------------------------------------------

def _classify_defendants(
    df_prepared: pd.DataFrame,
    window_start: pd.Timestamp,
) -> tuple[int, int, int]:
    """
    Classify unique defendants as new or returning relative to window_start.

    A defendant is 'new' if their first_ref_date (across all history) falls on or
    after window_start — meaning we had never seen them before this window opened.
    A defendant is 'returning' if their first_ref_date is before window_start.

    Deduplicates to one row per defendant so n_new + n_returning == total.
    """
    def_df = (
        df_prepared
        .drop_duplicates("pbk_def_num")[["pbk_def_num", "first_ref_date"]]
        .copy()
    )
    def_df["first_ref_date"] = pd.to_datetime(def_df["first_ref_date"])
    total       = len(def_df)
    n_new       = int((def_df["first_ref_date"] >= window_start).sum())
    n_returning = int((def_df["first_ref_date"] <  window_start).sum())
    return total, n_new, n_returning


def _prepare_defendant_totals(
    df_prepared: pd.DataFrame,
    rcvd_full: pd.DataFrame,
) -> dict:
    """
    Compute defendant count metrics and prior-period comparisons.

    df_prepared — result of _prepare(rcvd, rcvd_full); has first_ref_date and period columns.
    rcvd_full   — unfiltered RCVD; used for prior-period lookup and first-seen dates.

    Classification: a defendant is 'new' if first_ref_date >= filter_start_date (never seen
    before the window), 'returning' otherwise. This guarantees n_new + n_returning == total,
    and selecting the full dataset from 2016 produces 0% returning.
    """
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    filter_start = pd.Timestamp(str(start))

    total, n_new, n_returning = _classify_defendants(df_prepared, filter_start)
    pct_new       = round(n_new       / total * 100, 1) if total > 0 else 0.0
    pct_returning = round(n_returning / total * 100, 1) if total > 0 else 0.0

    # Sparklines — one row per (pbk_def_num, period), classified by first_ref_date vs. period start
    full_index = pd.period_range(start=start, end=end, freq=freq)

    def_period = (
        df_prepared
        .drop_duplicates(["pbk_def_num", "period"])[["pbk_def_num", "period", "first_ref_date"]]
        .copy()
    )
    def_period["first_ref_date"] = pd.to_datetime(def_period["first_ref_date"])
    def_period["period_start"]   = def_period["period"].apply(lambda p: pd.Timestamp(p.start_time))
    def_period["is_new"]         = def_period["first_ref_date"] >= def_period["period_start"]

    period_total     = def_period.groupby("period")["pbk_def_num"].nunique().reindex(full_index, fill_value=0)
    period_new       = def_period[def_period["is_new"]].groupby("period")["pbk_def_num"].nunique().reindex(full_index, fill_value=0)
    period_returning = period_total - period_new

    _safe = period_total.replace(0, float("nan"))
    period_pct_new       = (period_new       / _safe).fillna(0).round(3)
    period_pct_returning = (period_returning / _safe).fillna(0).round(3)

    sparkline_total         = period_total.tolist()
    sparkline_pct_new       = (period_pct_new       * 100).tolist()
    sparkline_pct_returning = (period_pct_returning * 100).tolist()

    # Prior period
    start_d = pd.Timestamp(str(start)).date()
    end_d   = pd.Timestamp(str(end)).date()
    span        = end_d - start_d
    prior_end   = start_d - pd.Timedelta(days=1)
    prior_start = prior_end - span
    show_delta  = prior_start >= _DATA_START

    prior_total = prior_n_new = prior_n_returning = None
    if show_delta:
        prior_raw = _apply_non_date_filters(rcvd_full).copy()
        prior_raw["ref_date"] = pd.to_datetime(prior_raw["ref_date"], errors="coerce")
        mask      = (prior_raw["ref_date"].dt.date >= prior_start) & (prior_raw["ref_date"].dt.date <= prior_end)
        prior_raw = prior_raw.loc[mask]

        if not prior_raw.empty:
            prior_prep        = _prepare(prior_raw, rcvd_full)
            prior_filter_start = pd.Timestamp(str(prior_start))
            prior_total, prior_n_new, prior_n_returning = _classify_defendants(prior_prep, prior_filter_start)

    return {
        "total":       total,
        "n_new":       n_new,
        "n_returning": n_returning,
        "pct_new":       pct_new,
        "pct_returning": pct_returning,
        "sparkline_total":         sparkline_total,
        "sparkline_pct_new":       sparkline_pct_new,
        "sparkline_pct_returning": sparkline_pct_returning,
        "prior_total":       prior_total,
        "prior_n_new":       prior_n_new,
        "prior_n_returning": prior_n_returning,
        "show_delta":  show_delta,
    }


def render_defendant_totals(rcvd: pd.DataFrame, rcvd_full: pd.DataFrame) -> None:
    """Render three metric cards: total defendants, % first-time, % returning."""
    df = _prepare(rcvd, rcvd_full)

    if df.empty:
        st.info("No valid defendant data available for the current filters.")
        return

    data = _prepare_defendant_totals(df, rcvd_full)

    start_d, end_d = st.session_state["date_range_filter"]
    start_d = pd.Timestamp(str(start_d)).date()
    end_d   = pd.Timestamp(str(end_d)).date()
    span        = end_d - start_d
    prior_end   = start_d - pd.Timedelta(days=1)
    prior_start = prior_end - span

    if data["show_delta"]:
        st.info(
            f"Compares the selected date range to the preceding "
            f"{span.days + 1:,}-day period "
            f"({prior_start.strftime('%b %-d, %Y')} – {prior_end.strftime('%b %-d, %Y')}).",
            icon=":material/info:",
        )

    cols = st.columns(3)

    # Card (a) — total unique defendants
    with cols[0]:
        total = data["total"]
        prior = data["prior_total"]
        if prior is not None and data["show_delta"]:
            diff      = total - prior
            pct       = (diff / prior * 100) if prior > 0 else 0.0
            delta_str = f"{pct:+.1f}% ({diff:+,} defendants)"
            d_color   = "normal"
        else:
            delta_str = None
            d_color   = "off"
        st.metric(
            label="**Unique Defendants**",
            value=f"{total:,}",
            delta=delta_str,
            delta_color=d_color,
            chart_data=data["sparkline_total"],
            chart_type="area",
        )

    # Card (b) — % first-time defendants
    with cols[1]:
        pct_new = data["pct_new"]
        prior_n = data["prior_n_new"]
        prior_t = data["prior_total"]
        if prior_n is not None and prior_t is not None and data["show_delta"]:
            prior_pct  = round(prior_n / prior_t * 100, 1) if prior_t > 0 else 0.0
            pp_diff    = pct_new - prior_pct
            delta_str  = f"{pp_diff:+.1f} pp vs. prior period"
            d_color    = "normal"
        else:
            delta_str = None
            d_color   = "off"
        st.metric(
            label="**First-Time Defendants**",
            value=f"{pct_new:.1f}%",
            delta=delta_str,
            delta_color=d_color,
            help="Defendants with no prior referral to this office since 2016.",
            chart_data=data["sparkline_pct_new"],
            chart_type="area",
        )

    # Card (c) — % returning defendants
    with cols[2]:
        pct_ret  = data["pct_returning"]
        prior_nr = data["prior_n_returning"]
        prior_t  = data["prior_total"]
        if prior_nr is not None and prior_t is not None and data["show_delta"]:
            prior_pct = round(prior_nr / prior_t * 100, 1) if prior_t > 0 else 0.0
            pp_diff   = pct_ret - prior_pct
            delta_str = f"{pp_diff:+.1f} pp vs. prior period"
            d_color   = "normal"
        else:
            delta_str = None
            d_color   = "off"
        st.metric(
            label="**Returning Defendants**",
            value=f"{pct_ret:.1f}%",
            delta=delta_str,
            delta_color=d_color,
            help="Defendants referred to this office at least once before the selected period.",
            chart_data=data["sparkline_pct_returning"],
            chart_type="area",
        )

    style_metric_cards(
        background_color="#0d1b2a",
        border_left_color="#4da6ff",
    )


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_recidivism(rcvd: pd.DataFrame, rcvd_full: pd.DataFrame) -> None:
    """
    Render recidivism / re-referral metrics section.

    rcvd      — filtered via session state (responds to sidebar filters)
    rcvd_full — the raw unfiltered table, used for first-seen date computation
                and full-history charts (recurrence dist, time between referrals)
    """
    df = _prepare(rcvd, rcvd_full)

    if df.empty:
        st.info("No valid defendant data available for the current filters.")
        return

    # --- Chart 1: New vs Prior by period (bar) + defendant breakdown (donut) ---
    view = st.segmented_control(
        label=None,
        options=["Count", "Normalized (%)"],
        default="Count",
        selection_mode="single",
    )
    is_normalized = view == "Normalized (%)"

    col_bar, col_donut = st.columns([3, 2])
    with col_bar:
        st.altair_chart(_build_referral_type_chart(df, is_normalized))
    with col_donut:
        st.altair_chart(_build_defendant_donut(
            _prepare_defendant_donut(df),
            title="Defendants by Referral History",
            subtitle="Unique defendants in the selected date range",
        ))

    st.divider()

    # --- Charts 2 & 3 side by side ---
    col1, col2 = st.columns(2)

    with col1:
        st.altair_chart(_build_recurrence_chart(rcvd_full))

    with col2:
        st.altair_chart(_build_time_between_chart(rcvd_full))
