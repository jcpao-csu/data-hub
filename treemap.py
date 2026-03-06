# treemap.py
# JCPAO Dashboard — Treemap of case volume by agency and charge category
#
# USAGE:
#   from treemap import render_treemap
#   from session_state import get_filtered_data
#
#   rcvd, fld, ntfld, disp = get_filtered_data()
#   render_treemap(rcvd)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from session_state import get_filtered_data, MSHP_CODES

# Load filtered data (see session_state.py)
rcvd, fld, ntfld, disp = get_filtered_data()

# ---------------------------------------------------------------------------
# Data prep
# ---------------------------------------------------------------------------

def _prepare(
    rcvd: pd.DataFrame,
    outer: str,
    inner: str,
) -> tuple[list, list, list, list]:
    """
    Build the four parallel lists Plotly needs for a two-level treemap:
        ids, labels, parents, values

    Structure:
        Root (hidden)
          └── Outer level  (agency or charge category)
                └── Inner level  (charge category or agency)
    """
    df = rcvd[["pbk_num", outer, inner]].copy()
    df[outer] = df[outer].fillna("Unknown")
    df[inner] = df[inner].fillna("Unknown")

    # Counts
    outer_counts = (
        df.groupby(outer)["pbk_num"].nunique()
        .reset_index(name="count")
    )
    inner_counts = (
        df.groupby([outer, inner])["pbk_num"].nunique()
        .reset_index(name="count")
    )
    total = int(df["pbk_num"].nunique())

    ids     = ["__root__"]
    labels  = ["All Cases"]
    parents = [""]
    values  = [total]

    # Outer nodes
    for _, row in outer_counts.iterrows():
        ids.append(str(row[outer]))
        labels.append(str(row[outer]))
        parents.append("__root__")
        values.append(int(row["count"]))

    # Inner nodes — id must be unique so prefix with parent
    for _, row in inner_counts.iterrows():
        ids.append(f"{row[outer]}||{row[inner]}")
        labels.append(str(row[inner]))
        parents.append(str(row[outer]))
        values.append(int(row["count"]))

    return ids, labels, parents, values


# ---------------------------------------------------------------------------
# Chart builder
# ---------------------------------------------------------------------------

def _build_treemap(
    rcvd: pd.DataFrame,
    outer: str,
    inner: str,
    outer_label: str,
    inner_label: str,
    color_scheme: str,
) -> go.Figure:
    ids, labels, parents, values = _prepare(rcvd, outer, inner)
    total = rcvd["pbk_num"].nunique()

    fig = go.Figure(go.Treemap(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        root_color="lightgrey",
        maxdepth=2,                     # show both levels at once
        branchvalues="total",           # parent size = sum of children
        textinfo="label+value+percent parent",
        textfont=dict(size=13),
        marker=dict(
            colorscale=color_scheme,
            showscale=True,
            colorbar=dict(
                thickness=14,
                tickfont=dict(size=10),
                title=dict(text="Cases", font=dict(size=11)),
            ),
        ),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Cases: %{value:,}<br>"
            "% of group: %{percentParent:.1%}"   # ← was percentRoot
            "<extra></extra>"
        ),
    ))

    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        height=520,
        title=dict(
            text=f"Case Volume by {outer_label} → {inner_label}",
            font=dict(size=14),
            x=0,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig

# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_treemap(rcvd: pd.DataFrame = rcvd) -> None:
    """
    Render an interactive two-level treemap of case volume.
    User can toggle which dimension is the outer (grouping) level.
    """
    if rcvd.empty:
        st.info("No data available for the current filters.")
        return

    mode = st.radio(
        "Group by",
        options=["Agency → Charge Category", "Charge Category → Agency"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if mode == "Agency → Charge Category":
        fig = _build_treemap(
            rcvd,
            outer="agency_name",
            inner="rcvd_lead_category",
            outer_label="Agency",
            inner_label="Charge Category",
            color_scheme="Blues",
        )
    else:
        fig = _build_treemap(
            rcvd,
            outer="rcvd_lead_category",
            inner="agency_name",
            outer_label="Charge Category",
            inner_label="Agency",
            color_scheme="Purples",
        )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Click any outer tile to drill down into its breakdown. "
        "Click the center label to zoom back out."
    )

render_treemap()