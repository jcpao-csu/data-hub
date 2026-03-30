# stats/disp_breakdown.py
# Disposition outcome breakdown by min_disp_rank — mutually exclusive optimal outcome classification.

import altair as alt
import pandas as pd
import streamlit as st

# Rank → human-readable label (ordered from most to least favorable to prosecution)
_RANK_LABELS = {
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

# Rank → resolution category (for color grouping)
_RANK_CATEGORY = {
    1:   "Conviction",
    2:   "Conviction",
    3:   "Conviction",
    4:   "Resolved Nolle",
    5:   "Resolved Nolle",
    6:   "Pending Nolle",
    7:   "Pending Nolle",
    7.5: "Acquittal",
    8:   "Unresolved Nolle",
    9:   "Unresolved Nolle",
    10:  "Unresolved Nolle",
    11:  "Unresolved Nolle",
}

_CATEGORY_ORDER  = ["Conviction", "Resolved Nolle", "Pending Nolle", "Acquittal", "Unresolved Nolle"]
_CATEGORY_COLORS = ["#3db87a",    "#4da6ff",         "#e8a838",       "#e05c5c",   "#c0392b"]

# Sorted outcome labels in rank order (top = most favorable)
_OUTCOME_ORDER = [_RANK_LABELS[r] for r in sorted(_RANK_LABELS)]


def _prepare_disp_breakdown(disp: pd.DataFrame) -> pd.DataFrame:
    total = disp["pbk_num"].nunique()

    counts = (
        disp.groupby("min_disp_rank")["pbk_num"]
        .nunique()
        .reset_index()
        .rename(columns={"pbk_num": "count"})
    )
    counts["outcome"]  = counts["min_disp_rank"].map(_RANK_LABELS).fillna("Unknown")
    counts["category"] = counts["min_disp_rank"].map(_RANK_CATEGORY).fillna("Unknown")
    counts["pct"]      = (counts["count"] / total * 100).round(1) if total else 0.0

    # Preserve rank-order sort for the y-axis
    counts = counts.sort_values("min_disp_rank")
    return counts


def _build_disp_breakdown_bar(df: pd.DataFrame, y_field: str, y_title: str) -> alt.Chart:
    selection = alt.selection_point(fields=["category"], bind="legend")

    tooltips = [
        alt.Tooltip("outcome:N",   title="Outcome"),
        alt.Tooltip("category:N",  title="Category"),
        alt.Tooltip("count:Q",     title="Cases",      format=","),
        alt.Tooltip("pct:Q",       title="Percentage", format=".1f"),
    ]

    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(f"{y_field}:Q", title=y_title),
            y=alt.Y(
                "outcome:N",
                title=None,
                sort=_OUTCOME_ORDER,
                axis=alt.Axis(labelLimit=220),
            ),
            color=alt.Color(
                "category:N",
                title="Category",
                scale=alt.Scale(domain=_CATEGORY_ORDER, range=_CATEGORY_COLORS),
                sort=_CATEGORY_ORDER,
            ),
            opacity=alt.condition(selection, alt.value(1.0), alt.value(0.2)),
            tooltip=tooltips,
        )
        .add_params(selection)
        .properties(width="container")
    )


def render_disp_breakdown(disp: pd.DataFrame) -> None:
    """Render a horizontal bar chart of disposed cases broken down by min_disp_rank outcome."""
    df = _prepare_disp_breakdown(disp)

    with st.container(border=True):
        st.header(":material/bar_chart: Disposition Outcome Breakdown")
        st.caption(
            "Cases broken down by their most favorable disposition outcome (`min_disp_rank`), "
            "which classifies each case into exactly one mutually exclusive outcome — from "
            "**Conviction** (trial guilty, guilty plea, plea deal) through **Resolved**, "
            "**Pending**, and **Unresolved** nolles. Click a legend category to highlight it."
        )

        view_mode = st.segmented_control(
            "Display",
            options=["Count", "Percentage"],
            default="Count",
            key="disp_breakdown_view_mode",
        )
        y_field = "count" if view_mode == "Count" else "pct"
        y_title = "Cases" if view_mode == "Count" else "% of Disposed Cases"

        st.altair_chart(_build_disp_breakdown_bar(df, y_field, y_title), use_container_width=True)
