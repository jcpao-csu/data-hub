# stats/disp_trial.py
# Breakdown of cases that went to trial by ultimate disposition outcome.

import altair as alt
import pandas as pd
import streamlit as st

# Classify trial cases by min_disp_rank (most favorable outcome across all charges).
# rank 1   = Trial — Guilty Verdict
# rank 7.5 = Trial — Acquittal
# rank 2,3 = Plea on another charge (better for prosecution than acquittal)
# rank 4+  = Nolle / Other (not 7.5)

_OUTCOME_ORDER  = ["Guilty Verdict", "Acquittal", "Plea on Another Charge", "Nolle / Other"]
_OUTCOME_COLORS = ["#3db87a",        "#e05c5c",   "#4da6ff",                 "#8490a8"]


def _classify_trial_outcome(rank) -> str:
    if rank == 1:
        return "Guilty Verdict"
    elif rank == 7.5:
        return "Acquittal"
    elif rank in (2, 3):
        return "Plea on Another Charge"
    else:
        return "Nolle / Other"


def _prepare_trial_verdicts(disp: pd.DataFrame) -> pd.DataFrame:
    trials = disp.loc[disp["any_trial"] == True].copy()
    total  = trials["pbk_num"].nunique()

    trials["outcome"] = trials["min_disp_rank"].map(_classify_trial_outcome).fillna("Nolle / Other")

    counts = (
        trials.groupby("outcome")["pbk_num"]
        .nunique()
        .reindex(_OUTCOME_ORDER, fill_value=0)
        .reset_index(name="count")
    )
    counts.columns = ["verdict", "count"]
    counts["pct"] = (counts["count"] / total * 100).round(1) if total else 0.0
    return counts


def _build_trial_verdict_pie(df: pd.DataFrame) -> alt.Chart:
    present  = [o for o in _OUTCOME_ORDER if df.loc[df["verdict"] == o, "count"].iloc[0] > 0]
    colors   = [_OUTCOME_COLORS[_OUTCOME_ORDER.index(o)] for o in present]
    df_plot  = df.loc[df["verdict"].isin(present)]

    selection = alt.selection_point(fields=["verdict"], bind="legend")

    return (
        alt.Chart(df_plot)
        .mark_arc(outerRadius=130)
        .encode(
            theta=alt.Theta("count:Q"),
            color=alt.Color(
                "verdict:N",
                title="Outcome",
                scale=alt.Scale(domain=present, range=colors),
                sort=present,
            ),
            opacity=alt.condition(selection, alt.value(1.0), alt.value(0.3)),
            tooltip=[
                alt.Tooltip("verdict:N", title="Outcome"),
                alt.Tooltip("count:Q",   title="Cases",      format=","),
                alt.Tooltip("pct:Q",     title="% of Trials", format=".1f"),
            ],
        )
        .add_params(selection)
        .properties(width="container")
    )


def render_trial_verdicts(disp: pd.DataFrame) -> None:
    """Render a pie chart breaking down trial cases by ultimate disposition outcome."""
    trials_total = disp.loc[disp["any_trial"] == True, "pbk_num"].nunique()
    if trials_total == 0:
        return

    df = _prepare_trial_verdicts(disp)
    n_guilty = int(df.loc[df["verdict"] == "Guilty Verdict", "count"].iloc[0])
    pct      = round(n_guilty / trials_total * 100, 1) if trials_total else 0.0

    with st.container(border=True):
        st.header(":material/gavel: Trial Verdicts")
        st.caption(
            "Of the cases that went to trial (`any_trial`), shows the ultimate disposition "
            "outcome based on `min_disp_rank` — the most favorable outcome across all charges. "
            "**Guilty Verdict** (rank 1) means the trial conviction was the best outcome. "
            "**Acquittal** (rank 7.5) means the not-guilty verdict was the final outcome with "
            "no better result on another charge. **Plea on Another Charge** (ranks 2–3) means "
            "the case went to trial but a plea on a separate charge was the overall best outcome. "
            "**Nolle / Other** covers remaining dispositions. Click a legend item to highlight."
        )
        st.markdown(
            f":green-background[**{n_guilty:,} of {trials_total:,} trial cases "
            f"({pct:.1f}%) resulted in a guilty verdict** during the selected period.]"
        )
        st.altair_chart(_build_trial_verdict_pie(df), width="container")
