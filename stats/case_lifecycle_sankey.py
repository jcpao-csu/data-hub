# stats/case_lifecycle_sankey.py
# Case lifecycle Sankey: referring agencies → received → review → filed/not filed → court status.
#
# rcvd      — filtered by sidebar (date range, charge category, agency, etc.)
# fld_all   — UNFILTERED: captures all filing outcomes regardless of date filter
# ntfld_all — UNFILTERED: captures all not-filed outcomes regardless of date filter
# disp_all  — UNFILTERED: captures all dispositions regardless of date filter
#
# Flow:
#   Top agencies → Received
#   Received → Completed Review / Under Review / Pending Further Investigation
#   Completed Review → Filed / Not Filed  (both terminal)
#   Filed → Disposed / Still Open         (both terminal)
#
# Classification priority (per case pbk_num):
#   1. Filed         — appears in fld_all (takes priority over PFI/Not Filed)
#   2. PFI           — appears in ntfld_all with min_ntfld_rank == 3, NOT yet filed
#   3. Not Filed     — appears in ntfld_all with min_ntfld_rank != 3, NOT yet filed
#   4. Under Review  — no record in fld_all or ntfld_all

import plotly.graph_objects as go
import pandas as pd
import streamlit as st


_TOP_N_AGENCIES = 8

_COLORS = {
    "agency":       "#4da6ff",
    "other_agency": "#7bbfff",
    "received":     "#4da6ff",
    "completed":    "#8490a8",
    "under_review": "#6b7a99",
    "pfi":          "#f28e2b",
    "filed":        "#3db87a",
    "not_filed":    "#f5c842",
    "still_open":   "#a0c4ff",
    "disposed":     "#e05c5c",
}


def _rgba(hex_color: str, alpha: float = 0.35) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _prepare_case_lifecycle_sankey(
    rcvd: pd.DataFrame,
    fld_all: pd.DataFrame,
    ntfld_all: pd.DataFrame,
    disp_all: pd.DataFrame,
) -> dict:
    """Classify received cases into full lifecycle stages and collect sub-breakdowns."""
    cases_set = set(rcvd["pbk_num"].dropna().unique())
    filed_ids = set(fld_all["pbk_num"].dropna())
    pfi_ids   = set(ntfld_all.loc[ntfld_all["min_ntfld_rank"] == 3, "pbk_num"].dropna())
    ntfld_ids = set(ntfld_all.loc[ntfld_all["min_ntfld_rank"] != 3, "pbk_num"].dropna())
    disp_ids  = set(disp_all["pbk_num"].dropna())

    filed_in_rcvd = cases_set & filed_ids
    pfi_only      = (cases_set & pfi_ids)   - filed_ids
    ntfld_only    = (cases_set & ntfld_ids) - filed_ids - pfi_ids
    under_review  = cases_set - filed_ids - pfi_ids - ntfld_ids - disp_ids
    disposed_set  = filed_in_rcvd & disp_ids

    n_filed        = len(filed_in_rcvd)
    n_pfi          = len(pfi_only)
    n_not_filed    = len(ntfld_only)
    n_under_review = len(under_review)
    n_disposed     = len(disposed_set)
    n_still_open   = max(0, n_filed - n_disposed)
    n_completed    = n_filed + n_not_filed

    # Agency breakdown (top N + "Other Agencies" remainder)
    agency_raw = (
        rcvd.groupby("agency_name")["pbk_num"]
        .nunique()
        .sort_values(ascending=False)
        .reset_index(name="cases")
    )
    top_agencies = agency_raw.head(_TOP_N_AGENCIES)
    rest_cases   = int(agency_raw.iloc[_TOP_N_AGENCIES:]["cases"].sum())

    agencies     = top_agencies["agency_name"].tolist()
    agency_cases = top_agencies["cases"].tolist()
    if rest_cases > 0:
        agencies.append("Other Agencies")
        agency_cases.append(rest_cases)

    return {
        "n_total":        len(cases_set),
        "n_completed":    n_completed,
        "n_under_review": n_under_review,
        "n_pfi":          n_pfi,
        "n_filed":        n_filed,
        "n_not_filed":    n_not_filed,
        "n_disposed":     n_disposed,
        "n_still_open":   n_still_open,
        "agencies":       agencies,
        "agency_cases":   agency_cases,
    }


def _build_case_lifecycle_sankey(data: dict) -> go.Figure:
    """Build the case lifecycle Sankey diagram."""
    agencies   = data["agencies"]
    n_agencies = len(agencies)
    total      = data["n_total"] or 1

    # Fixed node indices (offset by number of dynamic agency nodes)
    I_RCVD       = n_agencies
    I_COMPLETED  = I_RCVD + 1
    I_UNDER      = I_RCVD + 2
    I_PFI        = I_RCVD + 3
    I_FILED      = I_RCVD + 4
    I_NTFLD      = I_RCVD + 5
    I_STILL_OPEN = I_RCVD + 6
    I_DISPOSED   = I_RCVD + 7

    labels      = []
    node_colors = []

    for ag in agencies:
        labels.append(ag)
        node_colors.append(_COLORS["other_agency"] if ag == "Other Agencies" else _COLORS["agency"])

    labels += [
        "Received",
        "Completed Review",
        "Under Review",
        "Pending Further Investigation",
        "Filed",
        "Not Filed",
        "Still Open",
        "Disposed",
    ]
    node_colors += [
        _COLORS["received"],
        _COLORS["completed"],
        _COLORS["under_review"],
        _COLORS["pfi"],
        _COLORS["filed"],
        _COLORS["not_filed"],
        _COLORS["still_open"],
        _COLORS["disposed"],
    ]

    def pct(n: int) -> float:
        return n / total * 100

    links_raw: list[tuple] = []

    def link(src: int, tgt: int, val: int, label: str, color: str) -> None:
        if val > 0:
            links_raw.append((src, tgt, val, label, color))

    # Agencies → Received
    for i, (ag, cnt) in enumerate(zip(agencies, data["agency_cases"])):
        link(i, I_RCVD, cnt, f"{ag}: {cnt:,} ({pct(cnt):.1f}%)", _COLORS["agency"])

    # Received → review branches
    link(I_RCVD, I_COMPLETED, data["n_completed"],    f"Completed Review: {data['n_completed']:,} ({pct(data['n_completed']):.1f}%)", _COLORS["completed"])
    link(I_RCVD, I_UNDER,     data["n_under_review"], f"Under Review: {data['n_under_review']:,} ({pct(data['n_under_review']):.1f}%)", _COLORS["under_review"])
    link(I_RCVD, I_PFI,       data["n_pfi"],          f"Pending Further Investigation: {data['n_pfi']:,} ({pct(data['n_pfi']):.1f}%)", _COLORS["pfi"])

    # Completed Review → filing decision
    link(I_COMPLETED, I_FILED, data["n_filed"],     f"Filed: {data['n_filed']:,} ({pct(data['n_filed']):.1f}%)", _COLORS["filed"])
    link(I_COMPLETED, I_NTFLD, data["n_not_filed"], f"Not Filed: {data['n_not_filed']:,} ({pct(data['n_not_filed']):.1f}%)", _COLORS["not_filed"])

    # Filed → court status
    link(I_FILED, I_DISPOSED,   data["n_disposed"],   f"Disposed: {data['n_disposed']:,} ({pct(data['n_disposed']):.1f}%)", _COLORS["disposed"])
    link(I_FILED, I_STILL_OPEN, data["n_still_open"], f"Still Open: {data['n_still_open']:,} ({pct(data['n_still_open']):.1f}%)", _COLORS["still_open"])

    sources     = [r[0] for r in links_raw]
    targets     = [r[1] for r in links_raw]
    values      = [r[2] for r in links_raw]
    link_labels = [r[3] for r in links_raw]
    link_colors = [_rgba(r[4]) for r in links_raw]

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=15,
            thickness=20,
            label=labels,
            color=node_colors,
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            label=link_labels,
            color=link_colors,
            hovertemplate="%{label}<extra></extra>",
        ),
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=10),
        height=500,
    )
    return fig


def render_case_lifecycle_sankey(
    rcvd: pd.DataFrame,
    fld_all: pd.DataFrame,
    ntfld_all: pd.DataFrame,
    disp_all: pd.DataFrame,
) -> None:
    """Render the case lifecycle Sankey for the overview page."""
    data = _prepare_case_lifecycle_sankey(rcvd, fld_all, ntfld_all, disp_all)

    with st.container(border=True):
        st.header(":material/account_tree: Case Lifecycle")
        st.caption(
            "Traces the status of cases received within the selected date range — "
            "from referring agency through review, filing decision, and court status. "
            "The received set responds to sidebar filters; filing, not-filed, and disposition "
            "outcomes are looked up from all available data regardless of the date range. "
            "Top referring agencies are shown individually; remaining agencies are grouped."
        )
        st.plotly_chart(_build_case_lifecycle_sankey(data), width="container")
