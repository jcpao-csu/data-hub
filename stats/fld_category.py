# stats/fld_category.py
# Filed cases broken down by lead charge code category (fld_lead_category).
# Top 9 categories by overall total are named individually; the rest are summed into "Other".

import altair as alt
import pandas as pd
import streamlit as st

_CATEGORY_PALETTE = [
    "#4da6ff",  # 1
    "#f28e2b",  # 2
    "#e05c5c",  # 3
    "#3db87a",  # 4
    "#a78bfa",  # 5
    "#f5c842",  # 6
    "#26c6da",  # 7
    "#ff9da7",  # 8
    "#9c755f",  # 9
    "#78909c",  # Other
]
_OTHER_LABEL = "Other"


def _prepare_fld_category(fld: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    df = fld.copy()
    df["fld_lead_category"] = df["fld_lead_category"].fillna(_OTHER_LABEL)

    category_totals = (
        df.groupby("fld_lead_category")["pbk_num"]
        .nunique()
        .sort_values(ascending=False)
    )
    top_9 = category_totals.head(9).index.tolist()

    df["Category"] = df["fld_lead_category"].where(
        df["fld_lead_category"].isin(top_9), other=_OTHER_LABEL
    )

    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    wide = (
        df.groupby(["period", "Category"])["pbk_num"]
        .nunique()
        .unstack(fill_value=0)
        .reindex(full_index, fill_value=0)
    )
    wide.index.name = "period"
    wide = wide.reset_index()

    melted = wide.melt(id_vars="period", var_name="Category", value_name="total_cases")
    melted["period"] = melted["period"].astype(str)

    period_totals = melted.groupby("period")["total_cases"].transform("sum")
    melted["pct"] = (
        (melted["total_cases"] / period_totals * 100)
        .where(period_totals > 0, other=0.0)
        .round(1)
    )

    domain = top_9 + ([_OTHER_LABEL] if _OTHER_LABEL in melted["Category"].values else [])
    colors = _CATEGORY_PALETTE[: len(domain)]

    rank_map = {cat: i for i, cat in enumerate(domain)}
    melted["rank"] = melted["Category"].map(rank_map)

    return melted, domain, colors


def _build_fld_category_area(
    df: pd.DataFrame,
    domain: list[str],
    colors: list[str],
    stack: str | bool,
) -> alt.Chart:
    legend_sel = alt.selection_point(fields=["Category"], bind="legend")

    if stack == "normalize":
        y_enc = alt.Y(
            "total_cases:Q",
            stack="normalize",
            axis=alt.Axis(format="%", title="Share of Filed Cases"),
        )
    else:
        y_enc = alt.Y("total_cases:Q", stack=True, title="Cases Filed")

    tooltips = [
        alt.Tooltip("period:O",      title="Period"),
        alt.Tooltip("Category:N",    title="Charge Category"),
        alt.Tooltip("total_cases:Q", title="Cases Filed",        format=","),
        alt.Tooltip("pct:Q",         title="% of Period Total",  format=".1f"),
    ]

    return (
        alt.Chart(df)
        .mark_area(interpolate="monotone")
        .encode(
            x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
            y=y_enc,
            color=alt.Color(
                "Category:N",
                title="Charge Category",
                sort=domain,
                scale=alt.Scale(domain=domain, range=colors),
            ),
            order=alt.Order("rank:Q"),
            opacity=alt.condition(legend_sel, alt.value(0.85), alt.value(0.15)),
            tooltip=tooltips,
        )
        .add_params(legend_sel)
        .properties(width="container")
    )


def render_fld_category(fld: pd.DataFrame) -> None:
    """Render a stacked area chart of filed cases by lead charge code category."""
    with st.container(border=True):
        st.header(":material/category: Top Lead Charge Categories")
        # st.caption(
        #     "Breaks down formally filed cases by the category of the lead filed charge "
        #     "(`fld_lead_category`). The top 9 categories by total volume are shown "
        #     "individually; all remaining categories are grouped as **Other**. "
        #     "Click a legend item to highlight that category."
        # )

        df, domain, colors = _prepare_fld_category(fld)

        tab_stacked, tab_normalized = st.tabs(["Stacked", "Normalized (%)"])
        with tab_stacked:
            st.altair_chart(
                _build_fld_category_area(df, domain, colors, True),
                width="container",
            )
        with tab_normalized:
            st.altair_chart(
                _build_fld_category_area(df, domain, colors, "normalize"),
                width="container",
            )
