# stats/fsd_stats.py
# Family Support Division charts and sidebar.
#
# Charts organized by source table:
#   fsd_admin        : New Cases Received/Opened
#   fsd_admin_est    : BOWs Established, Notices & Findings, Genetic Testing, Administrative Orders
#   fsd_admin_enf    : Income Withholding Orders, Collection, % Cases Paying
#   fsd_judicial_pat : New Referrals, BOWs Established, Judicial Orders (095-34)
#   fsd_judicial_enf : New Referrals, Collection, Civil Contempts,
#                      Misdemeanors/Felonies Filed & Convicted, % Cases Paying

import altair as alt
import pandas as pd
import streamlit as st

from read_data import query_table


ADMIN        = query_table("SELECT * FROM fsd_admin")
ADMIN_EST    = query_table("SELECT * FROM fsd_admin_est")
ADMIN_ENF    = query_table("SELECT * FROM fsd_admin_enf")
JUDICIAL_PAT = query_table("SELECT * FROM fsd_judicial_pat")
JUDICIAL_ENF = query_table("SELECT * FROM fsd_judicial_enf")

_BAR_COLOR  = "#3db87a"
_AVG_COLOR  = "#f28e2b"
_GOAL_COLOR = "#e05c5c"


# --- Data access ---

def get_fsd_dataframes():
    return ADMIN, ADMIN_EST, ADMIN_ENF, JUDICIAL_PAT, JUDICIAL_ENF


def fsd_last_updated(admin_df: pd.DataFrame) -> str:
    try:
        dates = pd.to_datetime(admin_df["MonthYr"], errors="coerce")
        return dates.max().strftime("%B %Y")
    except Exception:
        return "N/A"


# --- Session state & sidebar ---

def _on_fsd_submit() -> None:
    """On form submit: rebuild period range and reset date range if view frequency changed."""
    view   = st.session_state["fsd_view"]
    pr     = st.session_state["fsd_period_range"]
    dates  = pd.to_datetime(ADMIN["MonthYr"], errors="coerce").dropna()
    new_pr = pd.period_range(start=dates.min(), end=dates.max(), freq=view)
    if new_pr.freqstr != pr.freqstr:
        st.session_state["fsd_period_range"] = new_pr
        st.session_state["fsd_date_range"]   = (str(new_pr[0]), str(new_pr[-1]))


def _reset_fsd_filters() -> None:
    """Reset FSD filters to defaults (yearly, full date range)."""
    dates  = pd.to_datetime(ADMIN["MonthYr"], errors="coerce").dropna()
    pr     = pd.period_range(start=dates.min(), end=dates.max(), freq="Y")
    st.session_state["fsd_view"]         = "Y"
    st.session_state["fsd_period_range"] = pr
    st.session_state["fsd_date_range"]   = (str(pr[0]), str(pr[-1]))


def initialize_fsd_session_state() -> None:
    if "fsd_view" not in st.session_state:
        st.session_state["fsd_view"] = "Y"
    if "fsd_period_range" not in st.session_state:
        view  = st.session_state["fsd_view"]
        dates = pd.to_datetime(ADMIN["MonthYr"], errors="coerce").dropna()
        pr    = pd.period_range(start=dates.min(), end=dates.max(), freq=view)
        st.session_state["fsd_period_range"] = pr
    if "fsd_date_range" not in st.session_state:
        pr = st.session_state["fsd_period_range"]
        st.session_state["fsd_date_range"] = (str(pr[0]), str(pr[-1]))


def _fmt_period(p) -> str:
    """Format a period for display — accepts Period objects or strings."""
    if isinstance(p, str):
        try:
            p = pd.Period(p)
        except Exception:
            return p
    view = st.session_state.get("fsd_view", "M")
    if view == "M":
        return p.strftime("%b %Y")
    elif view == "Q":
        return f"Q{p.quarter} {p.year}"
    return str(p.year)


def render_fsd_sidebar() -> tuple[str, tuple]:
    """Renders FSD-specific sidebar widgets. Returns (period_view, (start_str, end_str))."""
    pr      = st.session_state["fsd_period_range"]
    options = [str(p) for p in pr]

    # Validate date_range against current period options; always derive s, e as locals
    try:
        s, e = st.session_state["fsd_date_range"]
        if s not in options or e not in options:
            raise ValueError
    except Exception:
        s, e = options[0], options[-1]
        st.session_state["fsd_date_range"] = (s, e)

    with st.expander("**Dashboard Filters**", expanded=True):
        st.selectbox(
            ":green-background[:green[**Time Interval**] ⏰]",
            options=["M", "Q", "Y"],
            format_func=lambda x: {"M": "by Month", "Q": "by Quarter", "Y": "by Year"}[x],
            key="fsd_view",
            on_change=_on_fsd_submit,
            help="Select the desired time interval.",
        )
        st.select_slider(
            ":green-background[:green[**Time Range**] 🗓️]",
            options=options,
            value=(s, e),
            format_func=_fmt_period,
            key="fsd_date_range",
            help="Select the start and end of the time range.",
        )

    st.button(
        "Reset Filters",
        on_click=_reset_fsd_filters,
        type="secondary",
        icon="🔄",
        width="container",
        help="Restore all filters to their default values.",
    )

    st.divider()

    return st.session_state["fsd_view"], st.session_state["fsd_date_range"]


# --- Shared prepare / build / render ---

def _prepare_fsd_metric(
    df: pd.DataFrame,
    data_col: str,
    agg_method: str,
    date_range: tuple,
    period_view: str,
) -> pd.DataFrame:
    d = df[["MonthYr", data_col]].copy()
    d["MonthYr"] = pd.to_datetime(d["MonthYr"], errors="coerce")
    d["period"] = d["MonthYr"].dt.to_period(period_view)

    start, end = date_range
    # Convert strings to Period, then coerce to period_view frequency
    start_p = pd.Period(start) if isinstance(start, str) else start
    end_p   = pd.Period(end)   if isinstance(end,   str) else end
    start   = pd.Period(start_p.start_time, period_view)
    end     = pd.Period(end_p.end_time,     period_view)
    d = d[(d["period"] >= start) & (d["period"] <= end)]

    grouped = d.groupby("period")[data_col].agg(agg_method)
    full_index = pd.period_range(start=start, end=end, freq=period_view)
    grouped = grouped.reindex(full_index, fill_value=0)
    grouped.index.name = "period"
    grouped = grouped.reset_index()

    if period_view == "M":
        grouped["period_label"] = grouped["period"].dt.start_time.dt.strftime("%b %Y")
    elif period_view == "Q":
        grouped["period_label"] = (
            grouped["period"].astype(str).str.replace(r"(\d{4})Q(\d)", r"\1 Q\2", regex=True)
        )
    else:
        grouped["period_label"] = grouped["period"].dt.start_time.dt.strftime("%Y")

    return grouped


def _build_fsd_bar(
    df: pd.DataFrame,
    data_col: str,
    format_style: str,
    threshold: int | None,
    title: str = "",
    subtitle: str = "",
    show_value_labels: bool = True,
) -> alt.Chart:
    bars = (
        alt.Chart(df)
        .mark_bar(color=_BAR_COLOR)
        .encode(
            x=alt.X("period_label:O", title=None, sort=None, axis=alt.Axis(
                labelAngle=0,
                labelExpr="indexof(domain('x'), datum.value) % 2 === 0 ? datum.value : ''",
            )),
            y=alt.Y(f"{data_col}:Q", title=None, axis=alt.Axis(format=format_style)),
            tooltip=[
                alt.Tooltip("period_label:O", title="Period"),
                alt.Tooltip(f"{data_col}:Q", title=data_col, format=format_style),
            ],
        )
    )

    labels = (
        alt.Chart(df)
        .mark_text(dy=-10, size=10, color="#c9d6e3")
        .encode(
            x=alt.X("period_label:O", sort=None),
            y=alt.Y(f"{data_col}:Q"),
            text=alt.Text(f"{data_col}:Q", format=format_style),
        )
    )

    # Mean reference line — dashed orange, label on left above the line
    # x/y for labels are set as mark properties (not encoding) so "width" and
    # integer pixel positions are valid Vega-Lite signal references.
    rule_avg = (
        alt.Chart(df)
        .mark_rule(color=_AVG_COLOR, strokeDash=[5, 4], strokeWidth=2)
        .encode(
            y=alt.Y(f"mean({data_col}):Q"),
            tooltip=[alt.Tooltip(f"mean({data_col}):Q", title="Mean", format=format_style)],
        )
    )
    label_avg = rule_avg.mark_text(
        x="width", dx=-2, align="right", baseline="bottom", dy=-4,
        fontSize=11, fontWeight="bold", color=_AVG_COLOR, text="Mean",
    )

    chart = bars + (labels if show_value_labels else alt.layer()) + rule_avg + label_avg

    if threshold is not None:
        thresh_df = pd.DataFrame({"threshold": [threshold]})

        # Solid red goal line, label on right below the line
        rule_th = (
            alt.Chart(thresh_df)
            .mark_rule(color=_GOAL_COLOR, strokeWidth=2)
            .encode(
                y=alt.Y("threshold:Q"),
                tooltip=[alt.Tooltip("threshold:Q", title="Goal")],
            )
        )
        label_th = rule_th.mark_text(
            x="width", dx=-2, align="right", baseline="top", dy=4,
            fontSize=11, color=_GOAL_COLOR, text=f"GOAL: {threshold}",
        )
        chart = chart + rule_th + label_th

    return chart.properties(
        width="container",
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def render_fsd_metric(
    df: pd.DataFrame,
    data_col: str,
    title: str,
    caption: str,
    date_range: tuple,
    period_view: str,
    threshold: int | None = None,
    format_style: str = ",.0f",
    agg_method: str = "sum",
    show_value_labels: bool = True,
) -> None:
    prepared = _prepare_fsd_metric(df, data_col, agg_method, date_range, period_view)
    chart    = _build_fsd_bar(prepared, data_col, format_style, threshold, title=title, subtitle=caption, show_value_labels=show_value_labels)
    with st.container(border=True):
        st.altair_chart(chart, width="container")


# --- Section renderers ---

def render_fsd_admin(admin_df: pd.DataFrame, period_view: str, date_range: tuple) -> None:
    render_fsd_metric(
        admin_df,
        "New Cases Received/Opened",
        "New Cases Received / Opened",
        "Total new cases received or opened by the Family Support Division",
        date_range, period_view,
    )


_GOAL_MULTIPLIER = {"M": 1, "Q": 3, "Y": 12}


def render_fsd_admin_est(admin_est_df: pd.DataFrame, period_view: str, date_range: tuple) -> None:
    goal = 100 * _GOAL_MULTIPLIER[period_view]
    render_fsd_metric(
        admin_est_df,
        "BOWs Established (# Of Children)",
        "BOWs Established",
        "Born out of wedlock (BOW) cases where paternity and/or support has been administratively established",
        date_range, period_view,
    )
    render_fsd_metric(
        admin_est_df,
        "Notice and Findings (Goal 100)",
        "Notices and Findings",
        f"Notices and findings processed (Monthly goal: 100)",
        date_range, period_view,
        threshold=goal,
    )
    render_fsd_metric(
        admin_est_df,
        "Genetic Testing Results (Goal 100)",
        "Genetic Testing Results",
        f"Genetic testing results processed for paternity determinations (Monthly goal: 100)",
        date_range, period_view,
        threshold=goal,
    )
    render_fsd_metric(
        admin_est_df,
        "Administrative Orders",
        "Administrative Orders",
        "Administrative child support orders established",
        date_range, period_view,
    )


def render_fsd_admin_enf(admin_enf_df: pd.DataFrame, period_view: str, date_range: tuple) -> None:
    render_fsd_metric(
        admin_enf_df,
        "Income Withholding Orders",
        "Income Withholding Orders",
        "Income withholding orders issued to enforce child support obligations",
        date_range, period_view,
    )
    render_fsd_metric(
        admin_enf_df,
        "Collection",
        "Collection ($)",
        "Total child support collected (in nominal dollars) through administrative enforcement",
        date_range, period_view,
        format_style="$,.2f",
        show_value_labels=False,
    )
    render_fsd_metric(
        admin_enf_df,
        "Percentage of Cases Paying",
        "Cases Paying (%)",
        "Percentage of active enforcement cases where a payment was received (Always displayed as monthly)",
        date_range, "M",
        format_style=".1%",
        agg_method="mean",
        show_value_labels=False,
    )


def render_fsd_judicial_pat(judicial_pat_df: pd.DataFrame, period_view: str, date_range: tuple) -> None:
    render_fsd_metric(
        judicial_pat_df,
        "New Referrals",
        "New Referrals",
        "New paternity cases referred to judicial proceedings",
        date_range, period_view,
    )
    render_fsd_metric(
        judicial_pat_df,
        "BOWs Established (# Of Children)",
        "Judicial BOWs Established",
        "Born out of wedlock (BOW) cases established through judicial proceedings",
        date_range, period_view,
    )
    render_fsd_metric(
        judicial_pat_df,
        "Judicial Orders (095-34 Only)",
        "095-34 Judicial Orders",
        "095-34 Judicial child support orders entered",
        date_range, period_view,
    )


def render_fsd_judicial_enf(judicial_enf_df: pd.DataFrame, period_view: str, date_range: tuple) -> None:
    render_fsd_metric(
        judicial_enf_df,
        "New Referrals",
        "New Referrals",
        "New enforcement cases referred to judicial proceedings",
        date_range, period_view,
    )
    render_fsd_metric(
        judicial_enf_df,
        "Collection",
        "Collection ($)",
        "Child support collected (in nominal dollars) through judicial enforcement",
        date_range, period_view,
        format_style="$,.2f",
        show_value_labels=False,
    )
    render_fsd_metric(
        judicial_enf_df,
        "Misdemeanors Filed",
        "Misdemeanors Filed",
        "Misdemeanor non-support charges filed",
        date_range, period_view,
    )
    render_fsd_metric(
        judicial_enf_df,
        "Misdemeanor Convictions",
        "Misdemeanor Convictions",
        "Misdemeanor non-support convictions",
        date_range, period_view,
    )
    render_fsd_metric(
        judicial_enf_df,
        "Civil Contempts Filed",
        "Civil Contempts Filed",
        "Civil contempt actions filed for failure to pay child support",
        date_range, period_view,
    )
    render_fsd_metric(
        judicial_enf_df,
        "Percentage of Cases Paying",
        "Cases Paying (%)",
        "Percentage of active judicial enforcement cases where a payment was received (Always displayed as monthly)",
        date_range, "M",
        format_style=".1%",
        agg_method="mean",
        show_value_labels=False,
    )
