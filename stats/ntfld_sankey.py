# stats/ntfld_sankey.py
# Sankey diagram: not-filed case reasons by outcome status → category.
#
# Flow:
#   Not Filed
#   ├── Resolved
#   │   ├── Plea Deal
#   │   └── Suspect Deceased
#   ├── Pending
#   │   ├── PFI
#   │   └── Other Jurisdiction
#   └── Unresolved
#       ├── Self Defense
#       ├── Statute of Limitations
#       ├── Suppression
#       ├── Uncooperative Party
#       ├── Lack of Evidence
#       └── Other

import plotly.graph_objects as go
import pandas as pd
import streamlit as st


# min_ntfld_rank → outcome status (stable domain mapping)
_RANK_TO_STATUS: dict[int, str] = {
    0:  "Resolved",    # Plea Deal
    1:  "Resolved",    # Suspect Deceased
    3:  "Pending",     # PFI
    4:  "Pending",     # Other Jurisdiction
    5:  "Unresolved",  # Self Defense
    6:  "Unresolved",  # Statute of Limitations
    7:  "Unresolved",  # Suppression
    8:  "Unresolved",  # Uncooperative Party
    9:  "Unresolved",  # Lack of Evidence
    10: "Unresolved",  # Other
}

_STATUS_ORDER = ["Resolved", "Pending", "Unresolved", "Unknown"]

_STATUS_COLORS = {
    "Resolved":   "#3db87a",
    "Pending":    "#f28e2b",
    "Unresolved": "#e05c5c",
    "Unknown":    "#78909c",
}

_ROOT_COLOR = "#f5c842"


def _rgba(hex_color: str, alpha: float = 0.35) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _prepare_ntfld_sankey(ntfld: pd.DataFrame) -> dict:
    df = ntfld.copy()
    df["code_status"] = (
        df["min_ntfld_rank"]
        .apply(lambda r: _RANK_TO_STATUS.get(int(r), "Unknown") if pd.notna(r) else "Unknown")
    )
    df["category"] = (
        df["min_ntfld_category"]
        .fillna("Unknown")
        .replace({"PFI": "Pending Further Investigation"})
    )

    total = df["pbk_num"].nunique()

    by_status = (
        df.groupby("code_status")["pbk_num"]
        .nunique()
        .reset_index(name="cases")
    )
    by_status_cat = (
        df.groupby(["code_status", "category"])["pbk_num"]
        .nunique()
        .reset_index(name="cases")
    )

    return {
        "total":         total,
        "by_status":     by_status,
        "by_status_cat": by_status_cat,
    }


def _build_ntfld_sankey(data: dict) -> go.Figure:
    total        = data["total"] or 1
    by_status    = data["by_status"]
    by_status_cat = data["by_status_cat"]

    present_statuses = [
        s for s in _STATUS_ORDER
        if s in by_status["code_status"].values
    ]

    # Build node lists dynamically
    labels = ["Not Filed"]
    colors = [_ROOT_COLOR]
    node_idx: dict[str, int] = {"Not Filed": 0}

    for status in present_statuses:
        node_idx[status] = len(labels)
        labels.append(status)
        colors.append(_STATUS_COLORS.get(status, "#999999"))

    for _, row in by_status_cat.iterrows():
        status = row["code_status"]
        cat    = row["category"]
        key    = f"{status}/{cat}"
        if key not in node_idx:
            node_idx[key] = len(labels)
            labels.append(cat)
            colors.append(_STATUS_COLORS.get(status, "#999999"))

    # Build links
    sources, targets, values, link_colors, link_labels = [], [], [], [], []

    for _, row in by_status.iterrows():
        status = row["code_status"]
        if status not in present_statuses:
            continue
        n   = int(row["cases"])
        pct = n / total * 100
        sc  = _STATUS_COLORS.get(status, "#999999")
        sources.append(node_idx["Not Filed"])
        targets.append(node_idx[status])
        values.append(n)
        link_colors.append(_rgba(sc))
        link_labels.append(f"{status}: {n:,} ({pct:.1f}%)")

    for _, row in by_status_cat.iterrows():
        status = row["code_status"]
        cat    = row["category"]
        n      = int(row["cases"])
        pct    = n / total * 100
        key    = f"{status}/{cat}"
        sc     = _STATUS_COLORS.get(status, "#999999")
        sources.append(node_idx[status])
        targets.append(node_idx[key])
        values.append(n)
        link_colors.append(_rgba(sc))
        link_labels.append(f"{cat}: {n:,} ({pct:.1f}%)")

    # Filter zero-value links
    keep = [i for i, v in enumerate(values) if v > 0]
    sources     = [sources[i]     for i in keep]
    targets     = [targets[i]     for i in keep]
    values      = [values[i]      for i in keep]
    link_colors = [link_colors[i] for i in keep]
    link_labels = [link_labels[i] for i in keep]

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=25,
            label=labels,
            color=colors,
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


def render_ntfld_sankey(ntfld: pd.DataFrame) -> None:
    """Render a Sankey diagram of not-filed cases by outcome status and reason category."""
    data = _prepare_ntfld_sankey(ntfld)

    with st.container(border=True):
        st.header(":material/account_tree: Not-Filed Reasons — Sankey")
        st.caption(
            "Flow diagram of not-filed cases by outcome status and reason category. "
            "Cases are classified using the most optimal not-filed reason (`min_ntfld_rank`), "
            "then grouped into :green[Resolved] (plea deal, suspect deceased), "
            ":orange[Pending] (PFI, other jurisdiction), and :red[Unresolved] "
            "(evidence, suppression, self defense, etc.) outcomes."
        )
        st.plotly_chart(_build_ntfld_sankey(data), width="container")
