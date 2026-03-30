# stats/ntfld_reasons.py
# Not-filed cases broken down by reason category (min_ntfld_category).
# Uses the most optimal not-filed reason per case (min_ntfld_rank).
# Category order follows ntfld_rank ascending: best outcomes anchor the bottom of the stack.
#
# Also provides a treemap (render_ntfld_treemap) with hierarchy:
#   code_status → ntfld_category → ntfld_sub_category → ntfld_desc2
# Joined via min_ntfld_code → codebook ntfld_code.

import altair as alt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path


# Fixed color palette — up to 11 categories, ordered by rank (rank 0 = bottom of stack)
_REASON_PALETTE = [
    "#3db87a",  # Plea Deal           (rank 0)
    "#a0c4ff",  # Suspect Deceased    (rank 1)
    "#f28e2b",  # PFI                 (rank 3)
    "#26c6da",  # Other Jurisdiction  (rank 4)
    "#a78bfa",  # Self Defense        (rank 5)
    "#f5c842",  # Statute of Lim.     (rank 6)
    "#ff9da7",  # Suppression         (rank 7)
    "#9c755f",  # Uncooperative Party (rank 8)
    "#e05c5c",  # Lack of Evidence    (rank 9)
    "#78909c",  # Other               (rank 10)
    "#b0bec5",  # overflow slot
]


def _prepare_ntfld_reasons(ntfld: pd.DataFrame) -> pd.DataFrame:
    """
    Group not-filed cases by period × min_ntfld_category.
    Categories are ordered by their median min_ntfld_rank so the stack
    reflects outcome quality (most optimal at bottom) without hard-coding values.
    """
    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    df = ntfld.copy()
    df = df.dropna(subset=["min_ntfld_category"])

    # Derive stable rank order for categories from the data
    cat_rank = (
        df.groupby("min_ntfld_category")["min_ntfld_rank"]
        .median()
        .sort_values()
    )
    category_order = cat_rank.index.tolist()

    # Period × category counts
    grouped = (
        df.groupby(["period", "min_ntfld_category"])["pbk_num"]
        .nunique()
        .unstack(fill_value=0)
        .reindex(full_index, fill_value=0)
    )
    grouped.index.name = "period"
    grouped = grouped.reset_index()

    melted = grouped.melt(id_vars="period", var_name="Reason", value_name="total_cases")
    melted["period"] = melted["period"].astype(str)

    period_totals = melted.groupby("period")["total_cases"].transform("sum")
    melted["pct"] = (
        (melted["total_cases"] / period_totals * 100)
        .where(period_totals > 0, other=0.0)
        .round(1)
    )

    # Assign rank for stack order (rank 0 = bottom of stack)
    rank_map = {cat: i for i, cat in enumerate(category_order)}
    melted["rank"] = melted["Reason"].map(rank_map)

    return melted, category_order


def _build_ntfld_reasons_bar(
    df: pd.DataFrame,
    category_order: list[str],
    is_normalized: bool,
) -> alt.Chart:
    """Stacked bar chart — not-filed cases by reason category and period."""
    colors = _REASON_PALETTE[: len(category_order)]
    legend_sel = alt.selection_point(fields=["Reason"], bind="legend")

    y_enc = (
        alt.Y(
            "total_cases:Q",
            stack="normalize",
            axis=alt.Axis(format=".0%", title="Share of Not-Filed Cases"),
        )
        if is_normalized
        else alt.Y("total_cases:Q", stack="zero", title="Cases Not Filed")
    )

    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
            y=y_enc,
            color=alt.Color(
                "Reason:N",
                title="Reason",
                sort=category_order,
                scale=alt.Scale(domain=category_order, range=colors),
            ),
            order=alt.Order("rank:Q"),
            opacity=alt.condition(legend_sel, alt.value(1.0), alt.value(0.2)),
            tooltip=[
                alt.Tooltip("period:O",       title="Period"),
                alt.Tooltip("Reason:N",       title="Reason"),
                alt.Tooltip("total_cases:Q",  title="Cases Not Filed",    format=","),
                alt.Tooltip("pct:Q",          title="% of Period Total",  format=".1f"),
            ],
        )
        .add_params(legend_sel)
        .properties(width="container")
    )


def render_ntfld_reasons(ntfld: pd.DataFrame) -> None:
    """Render stacked bar of not-filed cases broken down by reason category."""
    df, category_order = _prepare_ntfld_reasons(ntfld)

    with st.container(border=True):
        st.header(":material/gavel: Reasons for Not Filing")
        st.caption(
            "Breakdown of not-filed cases by the most optimal reason recorded "
            "(`min_ntfld_category`). Categories are ordered by outcome quality — "
            "most favorable outcomes (e.g. Plea Deal) anchor the bottom of the stack. "
            "Click a reason in the legend to highlight or isolate it."
        )

        tab_count, tab_pct = st.tabs(["Count", "Normalized (%)"])
        with tab_count:
            st.altair_chart(
                _build_ntfld_reasons_bar(df, category_order, is_normalized=False),
                width="container",
            )
        with tab_pct:
            st.altair_chart(
                _build_ntfld_reasons_bar(df, category_order, is_normalized=True),
                width="container",
            )


# --- Treemap ---

_CODEBOOK_PATH = Path(__file__).parent.parent / "assets/codebooks/Karpel Event Codes Glossary.xlsx"

_STATUS_COLORS = {
    "Resolved":   "#3db87a",
    "Pending":    "#f28e2b",
    "Unresolved": "#e05c5c",
    "Unknown":    "#78909c",
}


@st.cache_data(ttl=3600)
def _load_ntfld_codebook() -> pd.DataFrame:
    """Load and cache unique (rank, code_status, category, sub_category) from the NTFLD sheet."""
    cb = pd.read_excel(_CODEBOOK_PATH, sheet_name="NTFLD")
    return (
        cb[["ntfld_rank", "code_status", "ntfld_category", "ntfld_sub_category"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )


def _prepare_ntfld_treemap(ntfld: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Join ntfld on min_ntfld_rank → ntfld_rank, group by the full hierarchy,
    and compute tooltip percentages. ntfld_sub_category == ntfld_category rows
    are handled in the build step (collapsed to avoid duplication in the treemap).
    """
    cb = _load_ntfld_codebook()

    rank_counts = (
        ntfld.groupby("min_ntfld_rank")["pbk_num"]
        .nunique()
        .reset_index(name="cases")
    )

    joined = rank_counts.merge(cb, left_on="min_ntfld_rank", right_on="ntfld_rank", how="left")
    joined = joined.fillna({
        "code_status":        "Unknown",
        "ntfld_category":     "Unknown",
        "ntfld_sub_category": "Unknown",
    })

    grouped = (
        joined
        .groupby(["code_status", "ntfld_category", "ntfld_sub_category"])["cases"]
        .sum()
        .reset_index()
    )
    total = int(grouped["cases"].sum())
    return grouped, total


def _build_ntfld_treemap(df: pd.DataFrame, total: int) -> go.Figure:
    """
    Build a go.Treemap with branchvalues='remainder'.

    Hierarchy: All Not Filed → code_status → ntfld_category → ntfld_sub_category
    Where ntfld_sub_category == ntfld_category AND diff sub-categories also exist
    (e.g. Lack of Evidence), an explicit 'Other' child node is added for those cases
    rather than silently folding them into the parent remainder.
    Where all sub-categories equal the category name, the category node is the leaf.

    Tooltip shows: cases, % of all not-filed, % of [named parent].
    customdata: [actual_count, pct_total, pct_parent, parent_label]
    """
    ids, labels, parents, values, colors, customdata = [], [], [], [], [], []

    def _node(id_, label, parent, tm_value, actual_count, color, pct_total, pct_parent, parent_label):
        ids.append(id_)
        labels.append(label)
        parents.append(parent)
        values.append(tm_value)
        colors.append(color)
        customdata.append([actual_count, round(pct_total, 1), round(pct_parent, 1), parent_label])

    # Root
    _node("root", "All Not Filed", "", 0, total, "#555555", 100.0, 100.0, "All Not Filed")

    for cs, cs_df in df.groupby("code_status"):
        cs_total = int(cs_df["cases"].sum())
        cs_color = _STATUS_COLORS.get(cs, "#999999")
        cs_pct   = cs_total / total * 100 if total else 0

        _node(cs, cs, "root", 0, cs_total, cs_color, cs_pct, cs_pct, "All Not Filed")

        for cat, cat_df in cs_df.groupby("ntfld_category"):
            cat_total = int(cat_df["cases"].sum())
            cat_id    = f"{cs}/{cat}"
            cat_pct   = cat_total / total * 100 if total else 0

            same_mask  = cat_df["ntfld_sub_category"] == cat
            same_cases = int(cat_df.loc[same_mask, "cases"].sum())
            diff_df    = cat_df[~same_mask]
            has_diff   = len(diff_df) > 0

            # If diff sub-categories exist alongside same-name cases, all cases go into
            # explicit children (remainder=0). Otherwise category node is the leaf (remainder=same_cases).
            cat_remainder = 0 if (has_diff and same_cases > 0) else same_cases

            _node(
                cat_id, cat, cs,
                cat_remainder, cat_total,
                cs_color, cat_pct,
                cat_total / cs_total * 100 if cs_total else 0,
                cs,
            )

            # Explicit "Other" child for same-name cases when diff children also exist
            if has_diff and same_cases > 0:
                _node(
                    f"{cs}/{cat}/Other", "Other", cat_id,
                    same_cases, same_cases,
                    cs_color,
                    same_cases / total * 100 if total else 0,
                    same_cases / cat_total * 100 if cat_total else 0,
                    cat,
                )

            for _, row in diff_df.iterrows():
                subcat       = row["ntfld_sub_category"]
                subcat_cases = int(row["cases"])
                _node(
                    f"{cs}/{cat}/{subcat}", subcat, cat_id,
                    subcat_cases, subcat_cases,
                    cs_color,
                    subcat_cases / total * 100 if total else 0,
                    subcat_cases / cat_total * 100 if cat_total else 0,
                    cat,
                )

    fig = go.Figure(go.Treemap(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="remainder",
        marker=dict(colors=colors, line=dict(width=1)),
        customdata=customdata,
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Cases: %{customdata[0]:,}<br>"
            "% of All Not Filed: %{customdata[1]:.1f}%<br>"
            "% of %{customdata[3]}: %{customdata[2]:.1f}%"
            "<extra></extra>"
        ),
        texttemplate="<b>%{label}</b><br>%{customdata[0]:,}",
        textfont=dict(size=12),
    ))
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=10))
    return fig


def render_ntfld_treemap(ntfld: pd.DataFrame) -> None:
    """Render the not-filed reasons treemap."""
    df, total = _prepare_ntfld_treemap(ntfld)

    with st.container(border=True):
        st.header(":material/account_tree: Not-Filed Reasons — Treemap")
        st.caption(
            "Hierarchical breakdown of not-filed cases by outcome status, category, and "
            "sub-category. Color reflects the outcome status: "
            ":green[Resolved] (plea deal / deceased), :orange[Pending] (PFI / jurisdiction), "
            "and :red[Unresolved] (evidence / suppression / other). "
            "Click any tile to drill down; click the path bar to navigate back up."
        )
        st.plotly_chart(_build_ntfld_treemap(df, total), width="container")
