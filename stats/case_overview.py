# stats/case_overview.py
# Cases processed by period — single status selected via st.selectbox.
# Renders a single-color bar chart with a click-driven detail panel to the right.
# Clicking a "Received" bar shows a donut breakdown of cases by agency for that period.

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from great_tables import GT, loc
from great_tables.style import borders, text
from streamlit_extras.great_tables import great_tables

from stats.gt_theme import apply_dark_theme
from stats.fld_sevclass import _DOMAIN as _SEVCLASS_DOMAIN, _COLOR_MAP as _SEVCLASS_COLOR_MAP, _map_sevclass

_DISP_RANK_LABELS = {
    1:   "Trial — Guilty",
    2:   "Guilty Plea",
    3:   "Plea Deal",
    4:   "Nolle — Diversion",
    5:   "Nolle — Defendant Deceased",
    6:   "Nolle — Admin",
    7:   "Nolle — Other Jurisdiction",
    7.5: "Trial — Not Guilty",
    8:   "Nolle — DPNPSD / Self Defense",
    9:   "Nolle — Statute of Limitations",
    10:  "Nolle — Lack of Evidence",
    11:  "Nolle — NP-Other",
}

_DISP_RANK_CATEGORY = {
    1:   "Conviction",
    2:   "Conviction",
    3:   "Conviction",
    4:   "Diversion", # Nolle (Resolved)
    5:   "Nolle prosequi", # Nolle (Resolved)
    6:   "Nolle prosequi", # Pending Nolle
    7:   "Nolle prosequi",
    7.5: "Acquittal",
    8:   "Nolle prosequi", # Nolle (Self Defense / DPNPSD)
    9:   "Nolle prosequi", # Nolle (Statute of Limitations)
    10:  "Nolle prosequi", # Nolle (Lack of Evidence)
    11:  "Nolle prosequi", # Nolle (Other)
}

_STATUS_MAP = {
    "Received":  "#4da6ff",
    "Filed":     "#3db87a",
    "Not Filed": "#f5c842",
    "Disposed":  "#e05c5c",
}

# Available breakdown options per status (displayed in right-column selectbox)
_DETAIL_OPTIONS = {
    "Received": [
        "By Referring Agency", 
        "By Review Status", 
        "By Arrest Status", 
        "By Referring Lead Charge Severity-Class", 
        "By Referring Lead Charge Category", 
        "By Defendant Race", 
        "By Defendant Sex"
    ],
    "Filed": [
        "By Referring Agency", 
        "By Open Case Status", 
        "By Filed Lead Charge Severity-Class", 
        "By Filed Lead Charge Category", 
        "By File Rate", 
        "By Defendant Race", 
        "By Defendant Sex"
    ],
    "Not Filed": [
        "By Referring Agency", 
        "By Referring Lead Charge Severity-Class", 
        "By Referring Lead Charge Category", 
        "By Not Filed Reason", 
        "By Re-Filing Status", 
        "By Defendant Race", 
        "By Defendant Sex"
    ],
    "Disposed": [
        "By Referring Agency", 
        "By Disposed Lead Charge Severity-Class", 
        "By Disposed Lead Charge Category", 
        "By Conviction Rate", 
        "By Disposition Outcome", 
        "By Guilty Plea", 
        "By Defendant Race", 
        "By Defendant Sex"
    ],
}

_REVIEW_STATUS_ORDER  = ["Filed", "Not Filed", "Pending Further Investigation", "Under Review"]
_REVIEW_STATUS_COLORS = ["#3db87a", "#f5c842", "#f28e2b", "#6b7a99"]

_ARREST_STATUS_ORDER  = ["In Custody", "Anytime"]
_ARREST_STATUS_COLORS = ["#e05c5c", "#6b7a99"]

_OPEN_STATUS_ORDER  = ["Still Open", "Disposed"]
_OPEN_STATUS_COLORS = ["#3db87a", "#e05c5c"]

_REFILED_STATUS_ORDER  = ["Eventually Filed", "Stayed Not Filed"]
_REFILED_STATUS_COLORS = ["#3db87a", "#6b7a99"]

_FILE_RATE_ORDER  = ["Filed", "Not Filed"]
_FILE_RATE_COLORS = ["#3db87a", "#f5c842"]

_CONV_STATUS_ORDER  = ["Convicted", "Not Convicted"]
_CONV_STATUS_COLORS = ["#3db87a", "#6b7a99"]

# Unique category values from _DISP_RANK_CATEGORY
_DISP_OUTCOME_ORDER = [
    "Conviction",
    "Diversion",
    "Acquittal",
    "Nolle prosequi",
]
_DISP_OUTCOME_COLORS = [
    "#3db87a",  # Conviction
    "#a78bfa",  # Diversion
    "#e05c5c",  # Acquittal
    "#6b7a99",  # Nolle prosequi
]

_GUILTY_PLEA_RANKS  = {2, 3}  # Guilty Plea, Plea Deal
_GUILTY_PLEA_ORDER  = ["Guilty Plea", "Other"]
_GUILTY_PLEA_COLORS = ["#4da6ff", "#6b7a99"]

_SEVERITY_ORDER  = ["Felony", "Misdemeanor", "Other"]
_SEVERITY_COLORS = ["#e05c5c", "#f5c842", "#6b7a99"]
_SEVERITY_MAP    = {"F": "Felony", "M": "Misdemeanor"}

_CATEGORY_PALETTE = [
    "#4da6ff",
    "#f28e2b",
    "#e05c5c",
    "#3db87a",
    "#a78bfa",
    "#f5c842",
    "#26c6da",
    "#ff9da7",
    "#9c755f",
    "#e377c2",
    "#78909c",  # Other
]

_AGENCY_PALETTE = [
    "#4da6ff",  # KCPD
    "#f28e2b",  # Independence PD
    "#e05c5c",  # Lee's Summit PD
    "#3db87a",  # Blue Springs PD
    "#a78bfa",  # Grandview PD
    "#f5c842",  # Raytown PD
    "#26c6da",  # Jackson County Sheriff's Office
    "#78909c",  # Other
]
_OTHER_LABEL = "Other"
_AGENCY_RENAME = {
    "Jackson County Sheriff": "Jackson County Sheriff's Office",
}
_KEEP_AGENCIES = frozenset([
    "KCPD",
    "Independence PD",
    "Lee's Summit PD",
    "Blue Springs PD",
    "Grandview PD",
    "Raytown PD",
    "Jackson County Sheriff's Office",
])

_RACE_LABELS: dict[str, str] = {
    "W": "White alone",
    "B": "Black or African American alone",
    "H": "Hispanic or Latino",
    "A": "Asian alone",
    "I": "American Indian alone",
    "M": "Multiple",
    "P": "Native Hawaiian or Other Pacific Islander",
    "U": "Unknown",
    "Unknown": "Unknown"
}

_SEX_LABELS: dict[str, str] = {
    "M": "Male",
    "F": "Female", 
    "U": "Unknown",
    "Unknown": "Unknown"
}


def _prepare_single_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate case counts by period for a single case-status DataFrame."""
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    counts = (
        df.groupby("period")["pbk_num"]
        .nunique()
        .reindex(full_index, fill_value=0)
    )
    counts.index.name = "period"
    counts = counts.reset_index().rename(columns={"pbk_num": "total_cases"})
    counts["period"] = counts["period"].astype(str)
    return counts


def _prepare_agency_breakdown(
    rcvd: pd.DataFrame,
    period: str | None,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Count unique cases by agency for the selected period (or all periods if None).
    Retains named agencies in _KEEP_AGENCIES; all others are summed into 'Other'.
    """
    df = rcvd.copy()
    df["agency_name"] = df["agency_name"].replace(_AGENCY_RENAME).fillna(_OTHER_LABEL)

    if period:
        df = df[df["period"].astype(str) == period]

    counts = (
        df.groupby("agency_name", dropna=False)["pbk_num"]
        .nunique()
        .reset_index(name="count")
    )

    kept  = counts[counts["agency_name"].isin(_KEEP_AGENCIES)].copy()
    other = int(counts.loc[~counts["agency_name"].isin(_KEEP_AGENCIES), "count"].sum())

    kept = kept.sort_values("count", ascending=False)
    if other > 0:
        kept = pd.concat(
            [kept, pd.DataFrame([{"agency_name": _OTHER_LABEL, "count": other}])],
            ignore_index=True,
        )

    total = kept["count"].sum()
    kept["pct"] = (kept["count"] / total * 100).round(1) if total else 0.0

    domain = kept["agency_name"].tolist()
    colors = _AGENCY_PALETTE[: len(domain)]
    return kept, domain, colors


def _prepare_review_status(
    rcvd: pd.DataFrame,
    fld_all: pd.DataFrame,
    ntfld_all: pd.DataFrame,
    period: str | None,
) -> pd.DataFrame:
    """Classify each received case as Filed, Not Filed, PFI, or Under Review.
    Uses unfiltered fld_all / ntfld_all so outcomes outside the date range are captured.
    """
    df = rcvd.copy()
    if period:
        df = df[df["period"].astype(str) == period]

    fld_ids   = fld_all["pbk_num"].unique()
    pfi_ids   = ntfld_all.loc[ntfld_all["min_ntfld_rank"] == 3,  "pbk_num"].unique()
    ntfld_ids = ntfld_all.loc[ntfld_all["min_ntfld_rank"] != 3, "pbk_num"].unique()

    df["status"] = np.select(
        [
            df["pbk_num"].isin(fld_ids),
            df["pbk_num"].isin(ntfld_ids),
            df["pbk_num"].isin(pfi_ids),
        ],
        ["Filed", "Not Filed", "Pending Further Investigation"],
        default="Under Review",
    )

    counts = (
        df.groupby("status")["pbk_num"]
        .nunique()
        .reindex(_REVIEW_STATUS_ORDER, fill_value=0)
        .reset_index(name="count")
    )
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total * 100).round(1) if total else 0.0
    return counts


def _build_review_status_donut(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    """Donut chart — received cases broken down by review status."""
    total = int(df["count"].sum())

    color_enc = alt.Color(
        "status:N",
        sort=_REVIEW_STATUS_ORDER,
        scale=alt.Scale(domain=_REVIEW_STATUS_ORDER, range=_REVIEW_STATUS_COLORS),
        legend=None,
    )
    tooltips = [
        alt.Tooltip("status:N",  title="Status"),
        alt.Tooltip("count:Q",   title="Cases",      format=","),
        alt.Tooltip("pct:Q",     title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    completed = int(df.loc[df["status"].isin(["Filed", "Not Filed"]), "count"].sum())
    completed_pct = completed / total * 100 if total else 0.0
    center_df = pd.DataFrame({"top": [f"{completed_pct:.1f}%"], "sub": ["completed review"]})
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
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _prepare_arrest_status(
    rcvd: pd.DataFrame,
    period: str | None,
) -> pd.DataFrame:
    """Count cases by arrest status (In Custody vs Anytime) for the selected period."""
    df = rcvd.copy()
    if period:
        df = df[df["period"].astype(str) == period]

    df = df.drop_duplicates("pbk_num")
    df["arrest_status"] = np.where(
        df["arrest_date"].notna(), "In Custody", "Anytime"
    )

    counts = (
        df.groupby("arrest_status")["pbk_num"]
        .nunique()
        .reindex(_ARREST_STATUS_ORDER, fill_value=0)
        .reset_index(name="count")
    )
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total * 100).round(1) if total else 0.0
    return counts


def _build_arrest_status_donut(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    """Donut chart — received cases broken down by arrest status."""
    total = int(df["count"].sum())

    color_enc = alt.Color(
        "arrest_status:N",
        sort=_ARREST_STATUS_ORDER,
        scale=alt.Scale(domain=_ARREST_STATUS_ORDER, range=_ARREST_STATUS_COLORS),
        legend=None,
    )
    tooltips = [
        alt.Tooltip("arrest_status:N", title="Status"),
        alt.Tooltip("count:Q",         title="Cases",      format=","),
        alt.Tooltip("pct:Q",           title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    in_custody = int(df.loc[df["arrest_status"] == "In Custody", "count"].sum())
    in_custody_pct = in_custody / total * 100 if total else 0.0
    center_df = pd.DataFrame({"top": [f"{in_custody_pct:.1f}%"], "sub": ["in custody"]})
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
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _prepare_demographic_breakdown(
    src: pd.DataFrame,
    col: str,
    period: str | None,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Count unique cases by a demographic column (def_race or def_sex).
    Null / blank values are labelled 'Unknown'. All distinct values are retained.
    """
    _label_maps = {"def_race": _RACE_LABELS, "def_sex": _SEX_LABELS}

    df = src.copy()
    if period:
        df = df[df["period"].astype(str) == period]
    df = df.drop_duplicates("pbk_num")
    df[col] = df[col].fillna("Unknown").replace("", "Unknown")
    if col in _label_maps:
        df[col] = df[col].map(_label_maps[col]).fillna("Unknown")

    counts = (
        df.groupby(col)["pbk_num"]
        .nunique()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total * 100).round(1) if total else 0.0

    domain = counts[col].tolist()
    colors = _CATEGORY_PALETTE[: len(domain)]
    return counts, domain, colors


def _build_demographic_donut(
    df: pd.DataFrame,
    col: str,
    domain: list[str],
    colors: list[str],
    title: str = "",
    subtitle: str = "",
) -> alt.Chart:
    """Donut chart — cases broken down by a demographic column."""
    total = int(df["count"].sum())

    color_enc = alt.Color(
        f"{col}:N",
        sort=domain,
        scale=alt.Scale(domain=domain, range=colors),
        legend=None,
    )
    tooltips = [
        alt.Tooltip(f"{col}:N", title=col.replace("_", " ").title()),
        alt.Tooltip("count:Q",  title="Cases",      format=","),
        alt.Tooltip("pct:Q",    title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    center_df = pd.DataFrame({"total": [f"{total:,}"], "sub": ["cases"]})
    center_total = (
        alt.Chart(center_df)
        .mark_text(size=18, fontWeight="bold", color="#e8edf2", dy=-9)
        .encode(text="total:N", tooltip=alt.value(None))
    )
    center_sub = (
        alt.Chart(center_df)
        .mark_text(size=11, color="#6b7a99", dy=9)
        .encode(text="sub:N", tooltip=alt.value(None))
    )

    return (arc + center_total + center_sub).properties(
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _prepare_sevclass_breakdown(
    src: pd.DataFrame,
    sevclass_col: str,
    period: str | None,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Count unique cases by lead charge severity-class using the MSHP SevClass ranking.
    Only severity classes present in the filtered data are included in domain/colors.
    """
    df = src.copy()
    if period:
        df = df[df["period"].astype(str) == period]
    df = df.drop_duplicates("pbk_num")
    df["sevclass"] = df[sevclass_col].apply(_map_sevclass)

    counts = (
        df.groupby("sevclass")["pbk_num"]
        .nunique()
        .reset_index(name="count")
    )
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total * 100).round(1) if total else 0.0

    present = set(counts["sevclass"])
    domain  = [sc for sc in _SEVCLASS_DOMAIN if sc in present]
    colors  = [_SEVCLASS_COLOR_MAP[sc] for sc in domain]

    # Reindex to domain order and add rank for arc ordering
    counts = (
        counts.set_index("sevclass")
        .reindex(domain, fill_value=0)
        .reset_index()
    )
    counts["pct"]  = (counts["count"] / total * 100).round(1) if total else 0.0
    counts["rank"] = range(len(counts))

    return counts, domain, colors


def _build_sevclass_donut(
    df: pd.DataFrame,
    domain: list[str],
    colors: list[str],
    title: str = "",
    subtitle: str = "",
) -> alt.Chart:
    """Donut chart — cases broken down by lead charge severity-class."""
    total = int(df["count"].sum())

    color_enc = alt.Color(
        "sevclass:N",
        sort=domain,
        scale=alt.Scale(domain=domain, range=colors),
        legend=None,
    )
    tooltips = [
        alt.Tooltip("sevclass:N", title="Severity / Class"),
        alt.Tooltip("count:Q",    title="Cases",      format=","),
        alt.Tooltip("pct:Q",      title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("rank:Q", sort="ascending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    felony_count = int(df.loc[df["sevclass"].str.contains("Felony", na=False), "count"].sum())
    felony_pct = felony_count / total * 100 if total else 0.0
    center_df = pd.DataFrame({"top": [f"{felony_pct:.1f}%"], "sub": ["felonies"]})
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
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _prepare_charge_severity(
    src: pd.DataFrame,
    period: str | None,
    sev_col: str,
) -> pd.DataFrame:
    """Count unique cases by lead charge severity (Felony / Misdemeanor / Other)."""
    df = src.copy()
    if period:
        df = df[df["period"].astype(str) == period]
    df = df.drop_duplicates("pbk_num")
    df["severity"] = df[sev_col].map(_SEVERITY_MAP).fillna("Other")

    counts = (
        df.groupby("severity")["pbk_num"]
        .nunique()
        .reindex(_SEVERITY_ORDER, fill_value=0)
        .reset_index(name="count")
    )
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total * 100).round(1) if total else 0.0
    return counts


def _build_charge_severity_donut(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    """Donut chart — received cases broken down by lead charge severity."""
    total = int(df["count"].sum())

    color_enc = alt.Color(
        "severity:N",
        sort=_SEVERITY_ORDER,
        scale=alt.Scale(domain=_SEVERITY_ORDER, range=_SEVERITY_COLORS),
        legend=None,
    )
    tooltips = [
        alt.Tooltip("severity:N", title="Severity"),
        alt.Tooltip("count:Q",    title="Cases",      format=","),
        alt.Tooltip("pct:Q",      title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    center_df = pd.DataFrame({"total": [f"{total:,}"], "sub": ["cases"]})
    center_total = (
        alt.Chart(center_df)
        .mark_text(size=18, fontWeight="bold", color="#e8edf2", dy=-9)
        .encode(text="total:N", tooltip=alt.value(None))
    )
    center_sub = (
        alt.Chart(center_df)
        .mark_text(size=11, color="#6b7a99", dy=9)
        .encode(text="sub:N", tooltip=alt.value(None))
    )

    return (arc + center_total + center_sub).properties(
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _prepare_charge_category(
    src: pd.DataFrame,
    period: str | None,
    cat_col: str,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Count unique cases by lead charge category; top 10 named, rest summed into 'Other'."""
    df = src.copy()
    if period:
        df = df[df["period"].astype(str) == period]
    df = df.drop_duplicates("pbk_num")
    df["category"] = df[cat_col].fillna(_OTHER_LABEL).replace("", _OTHER_LABEL)

    counts = (
        df.groupby("category")["pbk_num"]
        .nunique()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    top10 = counts.head(10).copy()
    other = int(counts.iloc[10:]["count"].sum())

    if other > 0:
        top10 = pd.concat(
            [top10, pd.DataFrame([{"category": _OTHER_LABEL, "count": other}])],
            ignore_index=True,
        )

    total = top10["count"].sum()
    top10["pct"] = (top10["count"] / total * 100).round(1) if total else 0.0

    domain = top10["category"].tolist()
    colors = _CATEGORY_PALETTE[: len(domain)]
    return top10, domain, colors


def _build_charge_category_donut(
    df: pd.DataFrame,
    domain: list[str],
    colors: list[str],
    title: str = "",
    subtitle: str = "",
) -> alt.Chart:
    """Donut chart — received cases by top 10 lead charge categories."""
    total = int(df["count"].sum())

    color_enc = alt.Color(
        "category:N",
        sort=domain,
        scale=alt.Scale(domain=domain, range=colors),
        legend=None,
    )
    tooltips = [
        alt.Tooltip("category:N", title="Category"),
        alt.Tooltip("count:Q",    title="Cases",      format=","),
        alt.Tooltip("pct:Q",      title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    center_df = pd.DataFrame({"total": [f"{total:,}"], "sub": ["cases"]})
    center_total = (
        alt.Chart(center_df)
        .mark_text(size=18, fontWeight="bold", color="#e8edf2", dy=-9)
        .encode(text="total:N", tooltip=alt.value(None))
    )
    center_sub = (
        alt.Chart(center_df)
        .mark_text(size=11, color="#6b7a99", dy=9)
        .encode(text="sub:N", tooltip=alt.value(None))
    )

    return (arc + center_total + center_sub).properties(
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _prepare_open_case_status(
    fld: pd.DataFrame,
    disp_all: pd.DataFrame,
    period: str | None,
) -> pd.DataFrame:
    """Classify filed cases as Still Open or Disposed based on presence in the disposed table.
    Uses unfiltered disp_all so disposals outside the date range are still captured.
    """
    df = fld.copy()
    if period:
        df = df[df["period"].astype(str) == period]
    df = df.drop_duplicates("pbk_num")

    disp_ids = disp_all["pbk_num"].unique()
    df["open_status"] = np.where(df["pbk_num"].isin(disp_ids), "Disposed", "Still Open")

    counts = (
        df.groupby("open_status")["pbk_num"]
        .nunique()
        .reindex(_OPEN_STATUS_ORDER, fill_value=0)
        .reset_index(name="count")
    )
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total * 100).round(1) if total else 0.0
    return counts


def _build_open_case_status_donut(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    """Donut chart — filed cases broken down by still open/disposed status."""
    total = int(df["count"].sum())

    color_enc = alt.Color(
        "open_status:N",
        sort=_OPEN_STATUS_ORDER,
        scale=alt.Scale(domain=_OPEN_STATUS_ORDER, range=_OPEN_STATUS_COLORS),
        legend=None,
    )
    tooltips = [
        alt.Tooltip("open_status:N", title="Status"),
        alt.Tooltip("count:Q",       title="Cases",      format=","),
        alt.Tooltip("pct:Q",         title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    still_open = int(df.loc[df["open_status"] == "Still Open", "count"].sum())
    still_open_pct = still_open / total * 100 if total else 0.0
    center_df = pd.DataFrame({"top": [f"{still_open_pct:.1f}%"], "sub": ["still open"]})
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
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _prepare_file_rate_status(
    fld: pd.DataFrame,
    ntfld: pd.DataFrame,
    fld_all: pd.DataFrame,
    period: str | None,
) -> pd.DataFrame:
    """
    Compute file rate for completed-review cases in the selected period.

    Denominator excludes from ntfld:
      - PFI cases (min_ntfld_rank == 3) — still potentially fileable
      - Plea deal dismissals (min_ntfld_rank == 0) — resolved via negotiation
      - Cases eventually filed (pbk_num in fld_all) — should count as filed

    Returns a two-row DataFrame with columns: file_status, count, pct, file_rate.
    """
    fld_df = fld.copy()
    if period:
        fld_df = fld_df[fld_df["period"].astype(str) == period]
    fld_df = fld_df.drop_duplicates("pbk_num")

    ntfld_df = ntfld.copy()
    if period:
        ntfld_df = ntfld_df[ntfld_df["period"].astype(str) == period]
    ntfld_df = ntfld_df.drop_duplicates("pbk_num")

    # Exclusions from not-filed denominator
    eventually_filed_ids = set(fld_all["pbk_num"].dropna())
    ntfld_df = ntfld_df[ntfld_df["min_ntfld_rank"] != 3]          # exclude PFI
    ntfld_df = ntfld_df[ntfld_df["min_ntfld_rank"] != 0]          # exclude plea deal dismissal
    ntfld_df = ntfld_df[~ntfld_df["pbk_num"].isin(eventually_filed_ids)]  # exclude eventually filed

    n_filed     = fld_df["pbk_num"].nunique()
    n_not_filed = ntfld_df["pbk_num"].nunique()
    total       = n_filed + n_not_filed
    file_rate   = round(n_filed / total * 100, 1) if total else 0.0

    counts = pd.DataFrame([
        {"file_status": "Filed",     "count": n_filed},
        {"file_status": "Not Filed", "count": n_not_filed},
    ])
    counts["pct"]       = (counts["count"] / total * 100).round(1) if total else 0.0
    counts["file_rate"] = file_rate
    return counts


def _build_file_rate_donut(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    """Donut chart — filed vs not-filed share; center shows the file rate %."""
    file_rate = df["file_rate"].iloc[0] if len(df) else 0.0

    color_enc = alt.Color(
        "file_status:N",
        sort=_FILE_RATE_ORDER,
        scale=alt.Scale(domain=_FILE_RATE_ORDER, range=_FILE_RATE_COLORS),
        legend=None,
    )
    tooltips = [
        alt.Tooltip("file_status:N", title="Status"),
        alt.Tooltip("count:Q",       title="Cases",      format=","),
        alt.Tooltip("pct:Q",         title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    center_df = pd.DataFrame({"rate": [f"{file_rate:.1f}%"], "sub": ["file rate"]})
    center_rate = (
        alt.Chart(center_df)
        .mark_text(size=18, fontWeight="bold", color="#e8edf2", dy=-9)
        .encode(text="rate:N", tooltip=alt.value(None))
    )
    center_sub = (
        alt.Chart(center_df)
        .mark_text(size=11, color="#6b7a99", dy=9)
        .encode(text="sub:N", tooltip=alt.value(None))
    )

    return (arc + center_rate + center_sub).properties(
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _prepare_ntfld_refiled_status(
    ntfld: pd.DataFrame,
    fld_all: pd.DataFrame,
    period: str | None,
) -> pd.DataFrame:
    """Classify not-filed cases as Eventually Filed or Stayed Not Filed.
    Uses unfiltered fld_all so filings outside the date range are still captured.
    """
    df = ntfld.copy()
    if period:
        df = df[df["period"].astype(str) == period]
    df = df.drop_duplicates("pbk_num")

    filed_ids = fld_all["pbk_num"].unique()
    df["refiled_status"] = np.where(df["pbk_num"].isin(filed_ids), "Eventually Filed", "Stayed Not Filed")

    counts = (
        df.groupby("refiled_status")["pbk_num"]
        .nunique()
        .reindex(_REFILED_STATUS_ORDER, fill_value=0)
        .reset_index(name="count")
    )
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total * 100).round(1) if total else 0.0
    return counts


def _build_ntfld_refiled_donut(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    """Donut chart — not-filed cases broken down by re-filing status."""
    total = int(df["count"].sum())

    color_enc = alt.Color(
        "refiled_status:N",
        sort=_REFILED_STATUS_ORDER,
        scale=alt.Scale(domain=_REFILED_STATUS_ORDER, range=_REFILED_STATUS_COLORS),
        legend=None,
    )
    tooltips = [
        alt.Tooltip("refiled_status:N", title="Status"),
        alt.Tooltip("count:Q",          title="Cases",      format=","),
        alt.Tooltip("pct:Q",            title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    eventually_filed = int(df.loc[df["refiled_status"] == "Eventually Filed", "count"].sum())
    filed_pct = eventually_filed / total * 100 if total else 0.0
    center_df = pd.DataFrame({"top": [f"{filed_pct:.1f}%"], "sub": ["eventually filed"]})
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
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


# Some disposed rows have a NULL min_disp_rank but a known min_disp_code.
# We impute rank for three known codes before any disposed metric runs:
#   SD     (sentenced)                → rank 2 (Guilty Plea)
#   PRDISP (probation discharged)     → rank 2 (Guilty Plea)
#   MERGED (merged with another ref.) → rank 6 (Nolle — Admin)
# _clean_disp() is called once in render_case_volume so all downstream
# prepare functions receive the corrected DataFrame.
_DISP_CODE_RANK_FILL = {"SD": 2, "PRDISP": 2, "MERGED": 6}


def _clean_disp(disp: pd.DataFrame) -> pd.DataFrame:
    """Impute min_disp_rank for rows where it is NULL using min_disp_code."""
    df = disp.copy()
    null_mask = df["min_disp_rank"].isna()
    df.loc[null_mask, "min_disp_rank"] = (
        df.loc[null_mask, "min_disp_code"].map(_DISP_CODE_RANK_FILL)
    )
    return df


def _prepare_disp_outcome_breakdown(
    disp: pd.DataFrame,
    period: str | None,
) -> pd.DataFrame:
    """Count disposed cases by _DISP_RANK_CATEGORY label for the selected period."""
    df = disp.copy()
    if period:
        df = df[df["period"].astype(str) == period]
    df = df.drop_duplicates("pbk_num")

    df["outcome_cat"] = df["min_disp_rank"].map(_DISP_RANK_CATEGORY).fillna(_OTHER_LABEL)

    counts = (
        df.groupby("outcome_cat")["pbk_num"]
        .nunique()
        .reindex(_DISP_OUTCOME_ORDER, fill_value=0)
        .reset_index(name="count")
    )
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total * 100).round(1) if total else 0.0
    return counts


def _build_disp_outcome_breakdown_donut(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    """Donut chart — disposed cases broken down by disposition outcome category."""
    total = int(df["count"].sum())

    color_enc = alt.Color(
        "outcome_cat:N",
        sort=_DISP_OUTCOME_ORDER,
        scale=alt.Scale(domain=_DISP_OUTCOME_ORDER, range=_DISP_OUTCOME_COLORS),
        legend=None,
    )
    tooltips = [
        alt.Tooltip("outcome_cat:N", title="Outcome"),
        alt.Tooltip("count:Q",       title="Cases",      format=","),
        alt.Tooltip("pct:Q",         title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    center_df = pd.DataFrame({"total": [f"{total:,}"], "sub": ["cases"]})
    center_total = (
        alt.Chart(center_df)
        .mark_text(size=18, fontWeight="bold", color="#e8edf2", dy=-9)
        .encode(text="total:N", tooltip=alt.value(None))
    )
    center_sub = (
        alt.Chart(center_df)
        .mark_text(size=11, color="#6b7a99", dy=9)
        .encode(text="sub:N", tooltip=alt.value(None))
    )

    return (arc + center_total + center_sub).properties(
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _prepare_guilty_plea(
    disp: pd.DataFrame,
    period: str | None,
) -> pd.DataFrame:
    """Classify disposed cases as Guilty Plea / Plea Deal (ranks 2–3) vs Other."""
    df = disp.copy()
    if period:
        df = df[df["period"].astype(str) == period]
    df = df.drop_duplicates("pbk_num")

    df["plea_status"] = np.where(
        df["min_disp_rank"].isin(_GUILTY_PLEA_RANKS),
        "Guilty Plea",
        "Other",
    )

    counts = (
        df.groupby("plea_status")["pbk_num"]
        .nunique()
        .reindex(_GUILTY_PLEA_ORDER, fill_value=0)
        .reset_index(name="count")
    )
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total * 100).round(1) if total else 0.0
    return counts


def _build_guilty_plea_donut(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    """Donut chart — disposed cases: Guilty Plea / Plea Deal vs Other."""
    total = int(df["count"].sum())

    color_enc = alt.Color(
        "plea_status:N",
        sort=_GUILTY_PLEA_ORDER,
        scale=alt.Scale(domain=_GUILTY_PLEA_ORDER, range=_GUILTY_PLEA_COLORS),
        legend=None,
    )
    tooltips = [
        alt.Tooltip("plea_status:N", title="Outcome"),
        alt.Tooltip("count:Q",       title="Cases",      format=","),
        alt.Tooltip("pct:Q",         title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    center_df = pd.DataFrame({"total": [f"{total:,}"], "sub": ["cases"]})
    center_total = (
        alt.Chart(center_df)
        .mark_text(size=18, fontWeight="bold", color="#e8edf2", dy=-9)
        .encode(text="total:N", tooltip=alt.value(None))
    )
    center_sub = (
        alt.Chart(center_df)
        .mark_text(size=11, color="#6b7a99", dy=9)
        .encode(text="sub:N", tooltip=alt.value(None))
    )

    return (arc + center_total + center_sub).properties(
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _prepare_ntfld_reason(
    ntfld: pd.DataFrame,
    period: str | None,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Count unique cases by not-filed reason (min_ntfld_category); top 10 + Other."""
    df = ntfld.copy()
    if period:
        df = df[df["period"].astype(str) == period]
    df = df.drop_duplicates("pbk_num")
    df["reason"] = df["min_ntfld_category"].fillna(_OTHER_LABEL).replace("", _OTHER_LABEL)

    counts = (
        df.groupby("reason")["pbk_num"]
        .nunique()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    top10 = counts.head(10).copy()
    other = int(counts.iloc[10:]["count"].sum())

    if other > 0:
        top10 = pd.concat(
            [top10, pd.DataFrame([{"reason": _OTHER_LABEL, "count": other}])],
            ignore_index=True,
        )

    total = top10["count"].sum()
    top10["pct"] = (top10["count"] / total * 100).round(1) if total else 0.0

    domain = top10["reason"].tolist()
    colors = _CATEGORY_PALETTE[: len(domain)]
    return top10, domain, colors


def _build_ntfld_reason_donut(
    df: pd.DataFrame,
    domain: list[str],
    colors: list[str],
    title: str = "",
    subtitle: str = "",
) -> alt.Chart:
    """Donut chart — not-filed cases broken down by reason (min_ntfld_category)."""
    total = int(df["count"].sum())

    color_enc = alt.Color(
        "reason:N",
        sort=domain,
        scale=alt.Scale(domain=domain, range=colors),
        legend=None,
    )
    tooltips = [
        alt.Tooltip("reason:N", title="Reason"),
        alt.Tooltip("count:Q",  title="Cases",      format=","),
        alt.Tooltip("pct:Q",    title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    center_df = pd.DataFrame({"total": [f"{total:,}"], "sub": ["cases"]})
    center_total = (
        alt.Chart(center_df)
        .mark_text(size=18, fontWeight="bold", color="#e8edf2", dy=-9)
        .encode(text="total:N", tooltip=alt.value(None))
    )
    center_sub = (
        alt.Chart(center_df)
        .mark_text(size=11, color="#6b7a99", dy=9)
        .encode(text="sub:N", tooltip=alt.value(None))
    )

    return (arc + center_total + center_sub).properties(
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _prepare_disp_outcome(
    disp: pd.DataFrame,
    period: str | None,
) -> pd.DataFrame:
    """Classify disposed cases as Convicted or Not Convicted via _DISP_RANK_CATEGORY."""
    df = disp.copy()
    if period:
        df = df[df["period"].astype(str) == period]
    df = df.drop_duplicates("pbk_num")

    # Ranks 1–3 (Trial Guilty, Guilty Plea, Plea Deal) are convictions — hardcoded
    df["conv_status"] = np.where(
        df["min_disp_rank"].isin({1, 2, 3}),
        "Convicted",
        "Not Convicted",
    )

    counts = (
        df.groupby("conv_status")["pbk_num"]
        .nunique()
        .reindex(_CONV_STATUS_ORDER, fill_value=0)
        .reset_index(name="count")
    )
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total * 100).round(1) if total else 0.0
    return counts


def _build_disp_outcome_donut(df: pd.DataFrame, title: str = "", subtitle: str = "") -> alt.Chart:
    """Donut chart — disposed cases: Convicted vs Not Convicted."""
    total = int(df["count"].sum())

    color_enc = alt.Color(
        "conv_status:N",
        sort=_CONV_STATUS_ORDER,
        scale=alt.Scale(domain=_CONV_STATUS_ORDER, range=_CONV_STATUS_COLORS),
        legend=None,
    )
    tooltips = [
        alt.Tooltip("conv_status:N", title="Outcome"),
        alt.Tooltip("count:Q",       title="Cases",      format=","),
        alt.Tooltip("pct:Q",         title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    center_df = pd.DataFrame({"total": [f"{total:,}"], "sub": ["cases"]})
    center_total = (
        alt.Chart(center_df)
        .mark_text(size=18, fontWeight="bold", color="#e8edf2", dy=-9)
        .encode(text="total:N", tooltip=alt.value(None))
    )
    center_sub = (
        alt.Chart(center_df)
        .mark_text(size=11, color="#6b7a99", dy=9)
        .encode(text="sub:N", tooltip=alt.value(None))
    )

    return (arc + center_total + center_sub).properties(
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _build_single_volume_bar(df: pd.DataFrame, color: str, title: str = "", subtitle: str = "") -> alt.Chart:
    """Single-color bar chart for one case status, with click selection by period."""
    click_sel = alt.selection_point(name="click_sel", fields=["period"], on="click", clear="dblclick")

    base = alt.Chart(df).encode(
        x=alt.X("period:O", title=None, axis=alt.Axis(
            labelAngle=0,
            labelExpr="indexof(domain('x'), datum.value) % 2 === 0 ? datum.value : ''",
        )),
        tooltip=[
            alt.Tooltip("period:O",      title="Period"),
            alt.Tooltip("total_cases:Q", title="Cases", format=","),
        ],
    )

    bars = (
        base
        .mark_bar(color=color, cursor="pointer")
        .encode(
            y=alt.Y("total_cases:Q", title=None),
            opacity=alt.condition(click_sel, alt.value(1.0), alt.value(0.65)),
        )
        .add_params(click_sel)
    )

    labels = (
        base
        .mark_text(dy=-10, size=10, color="#c9d6e3")
        .encode(
            y=alt.Y("total_cases:Q"),
            text=alt.Text("total_cases:Q", format=","),
        )
    )

    return (bars + labels).properties(
        width="container",
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _build_agency_donut(
    df: pd.DataFrame,
    domain: list[str],
    colors: list[str],
    title: str = "",
    subtitle: str = "",
) -> alt.Chart:
    """Donut chart — cases received broken down by referring agency, legend at bottom."""
    total = int(df["count"].sum())

    color_enc = alt.Color(
        "agency_name:N",
        sort=domain,
        scale=alt.Scale(domain=domain, range=colors),
        legend=None,
    )
    tooltips = [
        alt.Tooltip("agency_name:N", title="Agency"),
        alt.Tooltip("count:Q",       title="Cases",      format=","),
        alt.Tooltip("pct:Q",         title="% of Total", format=".1f"),
    ]

    base = alt.Chart(df).encode(
        theta=alt.Theta("count:Q", stack=True),
        order=alt.Order("count:Q", sort="descending"),
        color=color_enc,
        tooltip=tooltips,
    )

    arc = base.mark_arc(innerRadius=56, outerRadius=120, stroke="#e8edf2", strokeWidth=1.4, strokeOpacity=1)

    center_df = pd.DataFrame({"total": [f"{total:,}"], "sub": ["cases"]})
    center_total = (
        alt.Chart(center_df)
        .mark_text(size=18, fontWeight="bold", color="#e8edf2", dy=-9)
        .encode(text="total:N", tooltip=alt.value(None))
    )
    center_sub = (
        alt.Chart(center_df)
        .mark_text(size=11, color="#6b7a99", dy=9)
        .encode(text="sub:N", tooltip=alt.value(None))
    )

    return (arc + center_total + center_sub).properties(
        width="container",
        height=315,
        title=alt.TitleParams(title, subtitle=subtitle, anchor="start", subtitleColor="#e8edf2"),
    )


def _build_volume_gt(df: pd.DataFrame, status: str, subtitle: str) -> GT:
    """GT table — period-by-period case counts for one case status, with a Total row."""
    total_row = pd.DataFrame([{"period": "Total", "total_cases": int(df["total_cases"].sum())}])
    df = pd.concat([df, total_row], ignore_index=True)

    gt = (
        GT(df)
        .tab_header(title=f"Cases {status}", subtitle=subtitle)
        .cols_label(period="Period", total_cases="Cases")
        .fmt_integer(columns="total_cases")
        .tab_style(
            style=text(weight="bold"),
            locations=loc.body(rows=lambda df: df["period"] == "Total"),
        )
        .tab_style(
            style=borders(sides="top", color="#e8edf2", weight="2px", style="solid"),
            locations=loc.body(rows=lambda df: df["period"] == "Total"),
        )
        .cols_align(align="right", columns=["total_cases"])
    )
    return apply_dark_theme(gt)


def _build_simple_gt(
    df: pd.DataFrame,
    label_col: str,
    col_label: str,
    title: str,
    subtitle: str,
) -> GT:
    """Generic GT table for donut breakdowns — label | count | % of Total, plus a Total row.
    Rows are kept in the order they arrive (prepare functions handle sorting/Other placement).
    """
    total_row = pd.DataFrame([{label_col: "Total", "count": int(df["count"].sum()), "pct": 100.0}])
    df = pd.concat([df, total_row], ignore_index=True)

    gt = (
        GT(df)
        .tab_header(title=title, subtitle=subtitle)
        .cols_label(**{label_col: col_label, "count": "Cases", "pct": "% of Total"})
        .cols_move_to_start(columns=[label_col])
        .fmt_integer(columns="count")
        .fmt_number(columns="pct", decimals=1)
        .tab_style(
            style=text(weight="bold"),
            locations=loc.body(rows=lambda d: d[label_col] == "Total"),
        )
        .tab_style(
            style=borders(sides="top", color="#e8edf2", weight="2px", style="solid"),
            locations=loc.body(rows=lambda d: d[label_col] == "Total"),
        )
        .cols_align(align="right", columns=["count", "pct"])
    )
    return apply_dark_theme(gt)


def _build_agency_gt(df: pd.DataFrame, subtitle: str) -> GT:
    """GT table — cases broken down by referring agency, sorted by count descending.
    'Other' is pinned to the bottom, followed by a Total row.
    """
    other = df[df["agency_name"] == _OTHER_LABEL]
    main  = df[df["agency_name"] != _OTHER_LABEL].sort_values("count", ascending=False)
    total_row = pd.DataFrame([{"agency_name": "Total", "count": int(df["count"].sum()), "pct": 100.0}])
    df = pd.concat([main, other, total_row], ignore_index=True)

    gt = (
        GT(df)
        .tab_header(title="By Referring Agency", subtitle=subtitle)
        .cols_label(agency_name="Agency", count="Cases", pct="% of Total")
        .cols_move_to_start(columns=["agency_name"])
        .fmt_integer(columns="count")
        .fmt_number(columns="pct", decimals=1)
        .tab_style(
            style=text(weight="bold"),
            locations=loc.body(rows=lambda df: df["agency_name"] == "Total"),
        )
        .tab_style(
            style=borders(sides="top", color="#e8edf2", weight="2px", style="solid"),
            locations=loc.body(rows=lambda df: df["agency_name"] == "Total"),
        )
        .cols_align(align="right", columns=["count", "pct"])
    )
    return apply_dark_theme(gt)


def render_case_volume(
    rcvd: pd.DataFrame,
    fld: pd.DataFrame,
    ntfld: pd.DataFrame,
    disp: pd.DataFrame,
    FLD: pd.DataFrame | None = None,
    NTFLD: pd.DataFrame | None = None,
    DISP: pd.DataFrame | None = None,
) -> None:
    """Render a selectbox-driven single-status bar chart with a click-driven detail panel."""
    disp = _clean_disp(disp)
    if DISP is not None:
        DISP = _clean_disp(DISP)

    df_map = {
        "Received":  rcvd,
        "Filed":     fld,
        "Not Filed": ntfld,
        "Disposed":  disp,
    }

    col_left, col_right = st.columns(2, gap="medium")

    with col_left:
        selected_status = st.selectbox(
            label="Select case status category to view:",
            options=list(_STATUS_MAP.keys()),
            key="case_overview_status",
        )

        color = _STATUS_MAP[selected_status]
        df    = _prepare_single_volume(df_map[selected_status])

        _FREQ_LABEL = {"M": "Monthly", "Q": "Quarterly", "Y": "Yearly"}
        start, end  = st.session_state["date_range_filter"]
        freq        = st.session_state["period_freq_filter"]
        start_str   = pd.Timestamp(str(start)).strftime("%b %Y")
        end_str     = pd.Timestamp(str(end)).strftime("%b %Y")
        subtitle    = f"{_FREQ_LABEL.get(freq, freq)} totals · {start_str} – {end_str}"

        with st.container(border=True):
            event = st.altair_chart(
                _build_single_volume_bar(df, color, title=f"Cases {selected_status}", subtitle=subtitle),
                width="stretch",
                height=350,
                on_select="rerun",
            )
            with st.expander("View data table"):
                great_tables(_build_volume_gt(df, selected_status, subtitle), width="stretch")

    with col_right:
        click_items     = event.selection.get("click_sel", [])
        selected_period = click_items[0].get("period") if click_items else None

        detail_options = _DETAIL_OPTIONS[selected_status]

        if not detail_options:
            st.selectbox(
                label="Select a metric to view:",
                options=["No breakdowns available"],
                key=f"case_overview_detail_{selected_status}",
                disabled=True,
            )
            with st.container(border=True):
                st.caption(f"No breakdowns available for **{selected_status}** yet.")
        else:
            selected_detail = st.selectbox(
                label="Select a metric to view:",
                options=detail_options,
                key=f"case_overview_detail_{selected_status}",
            )

            with st.container(border=True):
                if not selected_period:
                    start, end = st.session_state["date_range_filter"]
                s_fmt = pd.Timestamp(str(start)).strftime("%b %-d, %Y")
                e_fmt = pd.Timestamp(str(end)).strftime("%b %-d, %Y")
                _range = f"from {s_fmt} to {e_fmt}"
                _in    = f"in {selected_period}" if selected_period else _range

                if selected_status == "Received" and selected_detail == "By Referring Agency":
                    agency_df, domain, colors = _prepare_agency_breakdown(rcvd, selected_period)
                    gt_subtitle = f"Total cases received {_in} by referring police agency"
                    st.altair_chart(
                        _build_agency_donut(agency_df, domain, colors, title="By Referring Agency",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_agency_gt(agency_df, gt_subtitle), width="stretch")

                elif selected_status == "Received" and selected_detail == "By Review Status":
                    fld_src   = FLD   if FLD   is not None else fld
                    ntfld_src = NTFLD if NTFLD is not None else ntfld
                    review_df = _prepare_review_status(rcvd, fld_src, ntfld_src, selected_period)
                    gt_subtitle = f"Current filing status of cases received {_in}"
                    st.altair_chart(
                        _build_review_status_donut(review_df, title="By Review Status",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(review_df, "status", "Status", "By Review Status", gt_subtitle), width="stretch")

                elif selected_status == "Received" and selected_detail == "By Arrest Status":
                    arrest_df = _prepare_arrest_status(rcvd, selected_period)
                    gt_subtitle = f"Arrest status at referral for cases received {_in}"
                    st.altair_chart(
                        _build_arrest_status_donut(arrest_df, title="By Arrest Status",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(arrest_df, "arrest_status", "Status", "By Arrest Status", gt_subtitle), width="stretch")

                elif selected_status == "Received" and selected_detail == "By Referring Lead Charge Category":
                    category_df, domain, colors = _prepare_charge_category(rcvd, selected_period, "rcvd_lead_category")
                    gt_subtitle = f"Lead charge type for cases received {_in}"
                    st.altair_chart(
                        _build_charge_category_donut(category_df, domain, colors, title="By Referring Lead Charge Category",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(category_df, "category", "Category", "By Referring Lead Charge Category", gt_subtitle), width="stretch")

                elif selected_status == "Received" and selected_detail == "By Referring Lead Charge Severity-Class":
                    sevclass_df, domain, colors = _prepare_sevclass_breakdown(rcvd, "rcvd_lead_sevclass_rank", selected_period)
                    gt_subtitle = f"Referring lead charge severity-class for cases received {_in}"
                    st.altair_chart(
                        _build_sevclass_donut(sevclass_df, domain, colors, title="By Referring Lead Charge Severity-Class",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(sevclass_df[["sevclass", "count", "pct"]], "sevclass", "Severity / Class", "By Referring Lead Charge Severity-Class", gt_subtitle), width="stretch")

                elif selected_status == "Received" and selected_detail == "By Defendant Race":
                    race_df, domain, colors = _prepare_demographic_breakdown(rcvd, "def_race", selected_period)
                    gt_subtitle = f"Defendant race for cases received {_in}"
                    st.altair_chart(
                        _build_demographic_donut(race_df, "def_race", domain, colors, title="By Defendant Race",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(race_df, "def_race", "Race", "By Defendant Race", gt_subtitle), width="stretch")

                elif selected_status == "Received" and selected_detail == "By Defendant Sex":
                    sex_df, domain, colors = _prepare_demographic_breakdown(rcvd, "def_sex", selected_period)
                    gt_subtitle = f"Defendant sex for cases received {_in}"
                    st.altair_chart(
                        _build_demographic_donut(sex_df, "def_sex", domain, colors, title="By Defendant Sex",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(sex_df, "def_sex", "Sex", "By Defendant Sex", gt_subtitle), width="stretch")

                elif selected_status == "Filed" and selected_detail == "By Referring Agency":
                    agency_df, domain, colors = _prepare_agency_breakdown(fld, selected_period)
                    gt_subtitle = f"Total cases filed {_in} by referring police agency"
                    st.altair_chart(
                        _build_agency_donut(agency_df, domain, colors, title="By Referring Agency",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_agency_gt(agency_df, gt_subtitle), width="stretch")

                elif selected_status == "Filed" and selected_detail == "By Filed Lead Charge Category":
                    category_df, domain, colors = _prepare_charge_category(fld, selected_period, "fld_lead_category")
                    gt_subtitle = f"Lead charge type for cases filed {_in}"
                    st.altair_chart(
                        _build_charge_category_donut(category_df, domain, colors, title="By Filed Lead Charge Category",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(category_df, "category", "Category", "By Filed Lead Charge Category", gt_subtitle), width="stretch")

                elif selected_status == "Filed" and selected_detail == "By Open Case Status":
                    disp_src = DISP if DISP is not None else disp
                    open_df = _prepare_open_case_status(fld, disp_src, selected_period)
                    gt_subtitle = f"Whether cases filed {_in} have since been disposed"
                    st.altair_chart(
                        _build_open_case_status_donut(open_df, title="By Open Case Status",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(open_df, "open_status", "Status", "By Open Case Status", gt_subtitle), width="stretch")

                elif selected_status == "Filed" and selected_detail == "By File Rate":
                    fld_src = FLD if FLD is not None else fld
                    rate_df = _prepare_file_rate_status(fld, ntfld, fld_src, selected_period)
                    gt_subtitle = (
                        f"Share of completed-review cases {_in} that were filed. "
                        f"Excludes PFI, plea deal dismissals, and not-filed cases later re-filed."
                    )
                    st.altair_chart(
                        _build_file_rate_donut(rate_df, title="By File Rate",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(rate_df, "file_status", "Status", "By File Rate", gt_subtitle), width="stretch")

                elif selected_status == "Filed" and selected_detail == "By Filed Lead Charge Severity-Class":
                    sevclass_df, domain, colors = _prepare_sevclass_breakdown(fld, "fld_lead_sevclass_rank", selected_period)
                    gt_subtitle = f"Filed lead charge severity-class for cases filed {_in}"
                    st.altair_chart(
                        _build_sevclass_donut(sevclass_df, domain, colors, title="By Filed Lead Charge Severity-Class",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(sevclass_df[["sevclass", "count", "pct"]], "sevclass", "Severity / Class", "By Filed Lead Charge Severity-Class", gt_subtitle), width="stretch")

                elif selected_status == "Filed" and selected_detail == "By Defendant Race":
                    race_df, domain, colors = _prepare_demographic_breakdown(fld, "def_race", selected_period)
                    gt_subtitle = f"Defendant race for cases filed {_in}"
                    st.altair_chart(
                        _build_demographic_donut(race_df, "def_race", domain, colors, title="By Defendant Race",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(race_df, "def_race", "Race", "By Defendant Race", gt_subtitle), width="stretch")

                elif selected_status == "Filed" and selected_detail == "By Defendant Sex":
                    sex_df, domain, colors = _prepare_demographic_breakdown(fld, "def_sex", selected_period)
                    gt_subtitle = f"Defendant sex for cases filed {_in}"
                    st.altair_chart(
                        _build_demographic_donut(sex_df, "def_sex", domain, colors, title="By Defendant Sex",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(sex_df, "def_sex", "Sex", "By Defendant Sex", gt_subtitle), width="stretch")

                elif selected_status == "Not Filed" and selected_detail == "By Referring Agency":
                    agency_df, domain, colors = _prepare_agency_breakdown(ntfld, selected_period)
                    gt_subtitle = f"Total cases not filed {_in} by referring police agency"
                    st.altair_chart(
                        _build_agency_donut(agency_df, domain, colors, title="By Referring Agency",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_agency_gt(agency_df, gt_subtitle), width="stretch")

                elif selected_status == "Not Filed" and selected_detail == "By Referring Lead Charge Category":
                    category_df, domain, colors = _prepare_charge_category(ntfld, selected_period, "lead_ntfld_charge_category")
                    gt_subtitle = f"Lead charge type for cases not filed {_in}"
                    st.altair_chart(
                        _build_charge_category_donut(category_df, domain, colors, title="By Referring Lead Charge Category",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(category_df, "category", "Category", "By Referring Lead Charge Category", gt_subtitle), width="stretch")

                elif selected_status == "Not Filed" and selected_detail == "By Not Filed Reason":
                    reason_df, domain, colors = _prepare_ntfld_reason(ntfld, selected_period)
                    gt_subtitle = f"Reason for declination for cases not filed {_in}"
                    st.altair_chart(
                        _build_ntfld_reason_donut(reason_df, domain, colors, title="By Not Filed Reason",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(reason_df, "reason", "Reason", "By Not Filed Reason", gt_subtitle), width="stretch")

                elif selected_status == "Not Filed" and selected_detail == "By Re-Filing Status":
                    fld_src = FLD if FLD is not None else fld
                    refiled_df = _prepare_ntfld_refiled_status(ntfld, fld_src, selected_period)
                    gt_subtitle = f"Whether cases not filed {_in} were eventually filed with the court"
                    st.altair_chart(
                        _build_ntfld_refiled_donut(refiled_df, title="By Re-Filing Status",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(refiled_df, "refiled_status", "Status", "By Re-Filing Status", gt_subtitle), width="stretch")

                elif selected_status == "Not Filed" and selected_detail == "By Referring Lead Charge Severity-Class":
                    sevclass_df, domain, colors = _prepare_sevclass_breakdown(ntfld, "lead_ntfld_sevclass_rank", selected_period)
                    gt_subtitle = f"Referring lead charge severity-class for cases not filed {_in}"
                    st.altair_chart(
                        _build_sevclass_donut(sevclass_df, domain, colors, title="By Referring Lead Charge Severity-Class",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(sevclass_df[["sevclass", "count", "pct"]], "sevclass", "Severity / Class", "By Referring Lead Charge Severity-Class", gt_subtitle), width="stretch")

                elif selected_status == "Not Filed" and selected_detail == "By Defendant Race":
                    race_df, domain, colors = _prepare_demographic_breakdown(ntfld, "def_race", selected_period)
                    gt_subtitle = f"Defendant race for cases not filed {_in}"
                    st.altair_chart(
                        _build_demographic_donut(race_df, "def_race", domain, colors, title="By Defendant Race",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(race_df, "def_race", "Race", "By Defendant Race", gt_subtitle), width="stretch")

                elif selected_status == "Not Filed" and selected_detail == "By Defendant Sex":
                    sex_df, domain, colors = _prepare_demographic_breakdown(ntfld, "def_sex", selected_period)
                    gt_subtitle = f"Defendant sex for cases not filed {_in}"
                    st.altair_chart(
                        _build_demographic_donut(sex_df, "def_sex", domain, colors, title="By Defendant Sex",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(sex_df, "def_sex", "Sex", "By Defendant Sex", gt_subtitle), width="stretch")

                elif selected_status == "Disposed" and selected_detail == "By Referring Agency":
                    agency_df, domain, colors = _prepare_agency_breakdown(disp, selected_period)
                    gt_subtitle = f"Total cases disposed {_in} by referring police agency"
                    st.altair_chart(
                        _build_agency_donut(agency_df, domain, colors, title="By Referring Agency",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_agency_gt(agency_df, gt_subtitle), width="stretch")

                elif selected_status == "Disposed" and selected_detail == "By Disposed Lead Charge Category":
                    category_df, domain, colors = _prepare_charge_category(disp, selected_period, "lead_disp_category")
                    gt_subtitle = f"Lead charge type for cases disposed {_in}"
                    st.altair_chart(
                        _build_charge_category_donut(category_df, domain, colors, title="By Disposed Lead Charge Category",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(category_df, "category", "Category", "By Disposed Lead Charge Category", gt_subtitle), width="stretch")

                elif selected_status == "Disposed" and selected_detail == "By Conviction Rate":
                    outcome_df = _prepare_disp_outcome(disp, selected_period)
                    gt_subtitle = f"Convicted vs. not convicted outcomes for cases disposed {_in}"
                    st.altair_chart(
                        _build_disp_outcome_donut(outcome_df, title="By Conviction Rate",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(outcome_df, "conv_status", "Outcome", "By Conviction Rate", gt_subtitle), width="stretch")

                elif selected_status == "Disposed" and selected_detail == "By Disposition Outcome":
                    disp_outcome_df = _prepare_disp_outcome_breakdown(disp, selected_period)
                    gt_subtitle = f"Disposition outcome breakdown for cases disposed {_in}"
                    st.altair_chart(
                        _build_disp_outcome_breakdown_donut(disp_outcome_df, title="By Disposition Outcome",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(disp_outcome_df, "outcome_cat", "Outcome", "By Disposition Outcome", gt_subtitle), width="stretch")

                elif selected_status == "Disposed" and selected_detail == "By Guilty Plea":
                    plea_df = _prepare_guilty_plea(disp, selected_period)
                    gt_subtitle = f"Cases disposed by guilty plea vs. other outcome {_in}"
                    st.altair_chart(
                        _build_guilty_plea_donut(plea_df, title="By Guilty Plea",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(plea_df, "plea_status", "Outcome", "By Guilty Plea", gt_subtitle), width="stretch")

                elif selected_status == "Disposed" and selected_detail == "By Disposed Lead Charge Severity-Class":
                    sevclass_df, domain, colors = _prepare_sevclass_breakdown(disp, "lead_disp_sevclass_rank", selected_period)
                    gt_subtitle = f"Disposed lead charge severity-class for cases disposed {_in}"
                    st.altair_chart(
                        _build_sevclass_donut(sevclass_df, domain, colors, title="By Disposed Lead Charge Severity-Class",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(sevclass_df[["sevclass", "count", "pct"]], "sevclass", "Severity / Class", "By Disposed Lead Charge Severity-Class", gt_subtitle), width="stretch")

                elif selected_status == "Disposed" and selected_detail == "By Defendant Race":
                    race_df, domain, colors = _prepare_demographic_breakdown(disp, "def_race", selected_period)
                    gt_subtitle = f"Defendant race for cases disposed {_in}"
                    st.altair_chart(
                        _build_demographic_donut(race_df, "def_race", domain, colors, title="By Defendant Race",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(race_df, "def_race", "Race", "By Defendant Race", gt_subtitle), width="stretch")

                elif selected_status == "Disposed" and selected_detail == "By Defendant Sex":
                    sex_df, domain, colors = _prepare_demographic_breakdown(disp, "def_sex", selected_period)
                    gt_subtitle = f"Defendant sex for cases disposed {_in}"
                    st.altair_chart(
                        _build_demographic_donut(sex_df, "def_sex", domain, colors, title="By Defendant Sex",
                            subtitle=gt_subtitle),
                        width="stretch", height=350,
                    )
                    with st.expander("View data table"):
                        great_tables(_build_simple_gt(sex_df, "def_sex", "Sex", "By Defendant Sex", gt_subtitle), width="stretch")
