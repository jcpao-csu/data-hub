# stats/fld_sevclass.py
# Filed cases broken down by lead charge severity/class (fld_lead_sevclass_rank).
# SevClass definitions sourced from MSHP Columns Codebook.xlsx — sheet "SevClass".
# Ranks 12+ are consolidated to "Other"; null values are labelled "Unknown".

import altair as alt
import pandas as pd
import streamlit as st

_SEVCLASS_LABELS: dict[int, str] = {
    1:  "Class A Felony",
    2:  "Class B Felony",
    3:  "Class C Felony",
    4:  "Class D Felony",
    5:  "Class E Felony",
    6:  "Class U Felony",
    7:  "Class A Misdemeanor",
    8:  "Class B Misdemeanor",
    9:  "Class C Misdemeanor",
    10: "Class D Misdemeanor",
    11: "Class U Misdemeanor",
}
_OTHER_LABEL   = "Other"    # ranks 12+
_UNKNOWN_LABEL = "Unknown"  # null / unmapped

# Full ordered domain — most serious (bottom of stack) to least serious (top)
_DOMAIN = [
    "Class A Felony",
    "Class B Felony",
    "Class C Felony",
    "Class D Felony",
    "Class E Felony",
    "Class U Felony",
    "Class A Misdemeanor",
    "Class B Misdemeanor",
    "Class C Misdemeanor",
    "Class D Misdemeanor",
    "Class U Misdemeanor",
    "Other",
    "Unknown",
]

# Felonies → warm reds/ambers; Misdemeanors → blues; Other/Unknown → grays
_COLOR_MAP: dict[str, str] = {
    "Class A Felony":      "#8b1a1a",
    "Class B Felony":      "#c0392b",
    "Class C Felony":      "#e05c5c",
    "Class D Felony":      "#e8824a",
    "Class E Felony":      "#e8a838",
    "Class U Felony":      "#f0c040",
    "Class A Misdemeanor": "#1565c0",
    "Class B Misdemeanor": "#2196f3",
    "Class C Misdemeanor": "#4da6ff",
    "Class D Misdemeanor": "#80c8ff",
    "Class U Misdemeanor": "#b3d9ff",
    "Other":               "#78909c",
    "Unknown":             "#455a64",
}


def _map_sevclass(rank) -> str:
    if pd.isna(rank):
        return _UNKNOWN_LABEL
    rank = int(rank)
    if rank >= 12:
        return _OTHER_LABEL
    return _SEVCLASS_LABELS.get(rank, _UNKNOWN_LABEL)


def _prepare_fld_sevclass(fld: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    df = fld.copy()
    df["SevClass"] = df["fld_lead_sevclass_rank"].apply(_map_sevclass)

    start, end = st.session_state["date_range_filter"]
    freq = st.session_state["period_freq_filter"]
    full_index = pd.period_range(start=start, end=end, freq=freq)

    wide = (
        df.groupby(["period", "SevClass"])["pbk_num"]
        .nunique()
        .unstack(fill_value=0)
        .reindex(full_index, fill_value=0)
    )
    wide.index.name = "period"
    wide = wide.reset_index()

    melted = wide.melt(id_vars="period", var_name="SevClass", value_name="total_cases")
    melted["period"] = melted["period"].astype(str)

    period_totals = melted.groupby("period")["total_cases"].transform("sum")
    melted["pct"] = (
        (melted["total_cases"] / period_totals * 100)
        .where(period_totals > 0, other=0.0)
        .round(1)
    )

    # Only include severity classes that actually appear in the filtered data
    present = melted.loc[melted["total_cases"] > 0, "SevClass"].unique()
    domain = [sc for sc in _DOMAIN if sc in present]
    colors = [_COLOR_MAP[sc] for sc in domain]

    # Rank for stack order: index in domain (0 = bottom of stack = most serious)
    rank_map = {sc: i for i, sc in enumerate(domain)}
    melted["rank"] = melted["SevClass"].map(rank_map)

    return melted, domain, colors


def _build_fld_sevclass_area(
    df: pd.DataFrame,
    domain: list[str],
    colors: list[str],
    stack: str | bool,
) -> alt.Chart:
    legend_sel = alt.selection_point(fields=["SevClass"], bind="legend")

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
        alt.Tooltip("SevClass:N",    title="Severity / Class"),
        alt.Tooltip("total_cases:Q", title="Cases Filed",         format=","),
        alt.Tooltip("pct:Q",         title="% of Period Total",   format=".1f"),
    ]

    return (
        alt.Chart(df)
        .mark_area(interpolate="monotone")
        .encode(
            x=alt.X("period:O", title="Period", axis=alt.Axis(labelAngle=-45)),
            y=y_enc,
            color=alt.Color(
                "SevClass:N",
                title="Severity / Class",
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


def render_fld_sevclass(fld: pd.DataFrame) -> None:
    """Render a stacked area chart of filed cases by lead charge severity/class."""
    with st.container(border=True):
        st.header(":material/balance: Lead Charge Severity and Class")
        # st.caption(
        #     "Breaks down formally filed cases by the severity and class of the lead "
        #     "filed charge (`fld_lead_sevclass_rank`), from Class A Felony (most serious) "
        #     "down through misdemeanors. Ranks 12+ are grouped as **Other**; missing values "
        #     "as **Unknown**. Click a legend item to highlight that class."
        # )

        df, domain, colors = _prepare_fld_sevclass(fld)

        tab_stacked, tab_normalized = st.tabs(["Stacked", "Normalized (%)"])
        with tab_stacked:
            st.altair_chart(
                _build_fld_sevclass_area(df, domain, colors, True),
                use_container_width=True,
            )
        with tab_normalized:
            st.altair_chart(
                _build_fld_sevclass_area(df, domain, colors, "normalize"),
                use_container_width=True,
            )
