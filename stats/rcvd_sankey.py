# stats/rcvd_sankey.py
# Sankey diagram: lifecycle of received cases from referral to final outcome.
#
# rcvd          — filtered by sidebar (responsive to date range, charge, agency, etc.)
# fld_all       — UNFILTERED: to-date filing outcomes regardless of date filter
# ntfld_all     — UNFILTERED: to-date not-filed outcomes regardless of date filter
# disp_all      — UNFILTERED: to-date dispositions regardless of date filter
#
# Flow:
#   Received
#   ├── Completed Review
#   │   ├── Filed
#   │   │   ├── Disposed
#   │   │   └── Still Open
#   │   └── Not Filed  (excl. PFI)
#   ├── Under Review   (terminal)
#   └── Pending Further Investigation  (terminal unless later filed)
#
# Classification priority (per case pbk_num):
#   1. Filed         — appears in fld_all (takes priority over PFI/Not Filed)
#   2. PFI           — appears in ntfld_all with min_ntfld_rank == 3, NOT yet filed
#   3. Not Filed     — appears in ntfld_all with min_ntfld_rank != 3, NOT yet filed
#   4. Under Review  — no record in fld_all or ntfld_all

import plotly.graph_objects as go
import pandas as pd
import streamlit as st


_NODE_COLORS = {
    "Received":                       "#4da6ff",
    "Completed Review":               "#8490a8",
    "Under Review":                   "#6b7a99",
    "Pending Further Investigation":  "#f28e2b",
    "Filed":                          "#3db87a",
    "Not Filed":                      "#f5c842",
    "Disposed":                       "#e05c5c",
    "Still Open":                     "#a0c4ff",
}


def _rgba(hex_color: str, alpha: float = 0.35) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _prepare_rcvd_sankey(
    rcvd: pd.DataFrame,
    fld_all: pd.DataFrame,
    ntfld_all: pd.DataFrame,
    disp_all: pd.DataFrame,
) -> dict:
    """
    Classify each received case by its to-date lifecycle status.
    Uses fast set operations; fld/ntfld/disp must be unfiltered.
    """
    cases_set = set(rcvd["pbk_num"].dropna().unique())

    filed_ids = set(fld_all["pbk_num"].dropna())
    pfi_ids   = set(ntfld_all.loc[ntfld_all["min_ntfld_rank"] == 3, "pbk_num"].dropna())
    ntfld_ids = set(ntfld_all.loc[ntfld_all["min_ntfld_rank"] != 3, "pbk_num"].dropna())
    disp_ids  = set(disp_all["pbk_num"].dropna())

    filed_in_rcvd  = cases_set & filed_ids
    pfi_only       = (cases_set & pfi_ids)   - filed_ids
    ntfld_only     = (cases_set & ntfld_ids) - filed_ids - pfi_ids
    under_review   = cases_set - filed_ids - pfi_ids - ntfld_ids

    n_filed        = len(filed_in_rcvd)
    n_pfi          = len(pfi_only)
    n_not_filed    = len(ntfld_only)
    n_under_review = len(under_review)
    n_disposed     = len(filed_in_rcvd & disp_ids)
    n_still_open   = n_filed - n_disposed
    n_completed    = n_filed + n_not_filed

    return {
        "n_total":        len(cases_set),
        "n_completed":    n_completed,
        "n_under_review": n_under_review,
        "n_pfi":          n_pfi,
        "n_filed":        n_filed,
        "n_not_filed":    n_not_filed,
        "n_disposed":     n_disposed,
        "n_still_open":   n_still_open,
    }


def _build_rcvd_sankey(counts: dict) -> go.Figure:
    """Build a Plotly Sankey diagram from the classified case counts."""
    labels = [
        "Received",                       # 0
        "Completed Review",               # 1
        "Under Review",                   # 2
        "Pending Further Investigation",  # 3
        "Filed",                          # 4
        "Not Filed",                      # 5
        "Disposed",                       # 6
        "Still Open",                     # 7
    ]
    node_colors = [_NODE_COLORS[l] for l in labels]

    sources = [0, 0, 0, 1, 1, 4, 4]
    targets = [1, 2, 3, 4, 5, 6, 7]
    values  = [
        counts["n_completed"],
        counts["n_under_review"],
        counts["n_pfi"],
        counts["n_filed"],
        counts["n_not_filed"],
        counts["n_disposed"],
        counts["n_still_open"],
    ]
    link_target_colors = [
        _NODE_COLORS["Completed Review"],
        _NODE_COLORS["Under Review"],
        _NODE_COLORS["Pending Further Investigation"],
        _NODE_COLORS["Filed"],
        _NODE_COLORS["Not Filed"],
        _NODE_COLORS["Disposed"],
        _NODE_COLORS["Still Open"],
    ]

    # Build hover labels with counts and percentages
    total = counts["n_total"] or 1
    link_labels = [
        f"Completed Review: {counts['n_completed']:,} ({counts['n_completed']/total:.1%})",
        f"Under Review: {counts['n_under_review']:,} ({counts['n_under_review']/total:.1%})",
        f"Pending Further Investigation: {counts['n_pfi']:,} ({counts['n_pfi']/total:.1%})",
        f"Filed: {counts['n_filed']:,} ({counts['n_filed']/total:.1%})",
        f"Not Filed: {counts['n_not_filed']:,} ({counts['n_not_filed']/total:.1%})",
        f"Disposed: {counts['n_disposed']:,} ({counts['n_disposed']/total:.1%})",
        f"Still Open: {counts['n_still_open']:,} ({counts['n_still_open']/total:.1%})",
    ]

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=25,
            label=labels,
            color=node_colors,
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            label=link_labels,
            color=[_rgba(c) for c in link_target_colors],
            hovertemplate="%{label}<extra></extra>",
        ),
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=10),
        height=450,
    )
    return fig


def render_rcvd_sankey(
    rcvd: pd.DataFrame,
    fld_all: pd.DataFrame,
    ntfld_all: pd.DataFrame,
    disp_all: pd.DataFrame,
) -> None:
    """Render the case lifecycle Sankey for received cases."""
    counts = _prepare_rcvd_sankey(rcvd, fld_all, ntfld_all, disp_all)

    with st.container(border=True):
        st.header(":material/account_tree: Case Lifecycle")
        st.caption(
            "Traces the to-date status of cases received within the selected date range. "
            "The received set responds to sidebar filters; outcomes (filed, not filed, disposed) "
            "are looked up from all available data regardless of the date range filter."
        )
        st.plotly_chart(_build_rcvd_sankey(counts), use_container_width=True)
