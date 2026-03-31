# stats/disp_sankey.py
# Sankey diagram: disposition outcomes from high-level buckets down to specific reasons.
#
# Flow (based on min_disp_rank — most favorable outcome per case):
#   Disposed
#   ├── Plea
#   │   ├── Guilty Plea        (rank 2)
#   │   └── Plea Deal          (rank 3)
#   ├── Trial
#   │   ├── Trial — Guilty     (rank 1)
#   │   └── Trial — Not Guilty (rank 7.5)
#   └── Nolle Prosequi
#       ├── Resolved Nolle
#       │   ├── Nolle — Diversion            (rank 4)
#       │   └── Nolle — Defendant Deceased   (rank 5)
#       ├── Pending Nolle
#       │   ├── Nolle — Admin                (rank 6)
#       │   └── Nolle — Other Jurisdiction   (rank 7)
#       └── Unresolved Nolle
#           ├── Nolle — DPNPSD / Self Defense  (rank 8)
#           ├── Nolle — Statute of Limitations (rank 9)
#           ├── Nolle — Lack of Evidence       (rank 10)
#           └── Nolle — NP-Other               (rank 11)

import plotly.graph_objects as go
import pandas as pd
import streamlit as st


_PLEA_RANKS       = {2, 3}
_TRIAL_RANKS      = {1, 7.5}
_NOLLE_RANKS      = {4, 5, 6, 7, 8, 9, 10, 11}
_NOLLE_RESOLVED   = {4, 5}
_NOLLE_PENDING    = {6, 7}
_NOLLE_UNRESOLVED = {8, 9, 10, 11}

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

_DISPOSED_COLOR   = "#e05c5c"
_PLEA_COLOR       = "#3db87a"
_TRIAL_COLOR      = "#4da6ff"
_NOLLE_COLOR      = "#8490a8"
_RESOLVED_COLOR   = "#4da6ff"
_PENDING_COLOR    = "#f28e2b"
_UNRESOLVED_COLOR = "#c0392b"
_ACQUITTAL_COLOR  = "#e05c5c"


def _rgba(hex_color: str, alpha: float = 0.35) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _prepare_disp_sankey(disp: pd.DataFrame) -> dict:
    counts = (
        disp.groupby("min_disp_rank")["pbk_num"]
        .nunique()
        .reset_index(name="cases")
    )
    total = int(counts["cases"].sum())

    rc: dict[float, int] = {
        float(row["min_disp_rank"]): int(row["cases"])
        for _, row in counts.iterrows()
    }

    n_plea  = sum(rc.get(float(r), 0) for r in _PLEA_RANKS)
    n_trial = sum(rc.get(float(r), 0) for r in _TRIAL_RANKS)
    n_nolle = sum(rc.get(float(r), 0) for r in _NOLLE_RANKS)

    n_resolved   = sum(rc.get(float(r), 0) for r in _NOLLE_RESOLVED)
    n_pending    = sum(rc.get(float(r), 0) for r in _NOLLE_PENDING)
    n_unresolved = sum(rc.get(float(r), 0) for r in _NOLLE_UNRESOLVED)

    return {
        "total":              total,
        "n_plea":             n_plea,
        "n_trial":            n_trial,
        "n_nolle":            n_nolle,
        "n_guilty_plea":      rc.get(2.0, 0),
        "n_plea_deal":        rc.get(3.0, 0),
        "n_trial_guilty":     rc.get(1.0, 0),
        "n_trial_not_guilty": rc.get(7.5, 0),
        "n_resolved":         n_resolved,
        "n_pending":          n_pending,
        "n_unresolved":       n_unresolved,
        "rc":                 rc,
    }


def _build_disp_sankey(data: dict) -> go.Figure:
    total = data["total"] or 1
    rc    = data["rc"]

    def pct(n: int) -> float:
        return n / total * 100

    # Node index map (fixed positions — see module header for hierarchy)
    labels = [
        "Disposed",                        # 0
        "Plea",                            # 1
        "Trial",                           # 2
        "Nolle Prosequi",                  # 3
        "Guilty Plea",                     # 4
        "Plea Deal",                       # 5
        "Trial — Guilty",                  # 6
        "Trial — Not Guilty",              # 7
        "Resolved Nolle",                  # 8
        "Pending Nolle",                   # 9
        "Unresolved Nolle",                # 10
        "Nolle — Diversion",               # 11
        "Nolle — Defendant Deceased",      # 12
        "Nolle — Admin",                   # 13
        "Nolle — Other Jurisdiction",      # 14
        "Nolle — DPNPSD / Self Defense",   # 15
        "Nolle — Statute of Limitations",  # 16
        "Nolle — Lack of Evidence",        # 17
        "Nolle — NP-Other",                # 18
    ]
    node_colors = [
        _DISPOSED_COLOR,    # 0  Disposed
        _PLEA_COLOR,        # 1  Plea
        _TRIAL_COLOR,       # 2  Trial
        _NOLLE_COLOR,       # 3  Nolle Prosequi
        _PLEA_COLOR,        # 4  Guilty Plea
        _PLEA_COLOR,        # 5  Plea Deal
        _PLEA_COLOR,        # 6  Trial — Guilty (conviction color)
        _ACQUITTAL_COLOR,   # 7  Trial — Not Guilty
        _RESOLVED_COLOR,    # 8  Resolved Nolle
        _PENDING_COLOR,     # 9  Pending Nolle
        _UNRESOLVED_COLOR,  # 10 Unresolved Nolle
        _RESOLVED_COLOR,    # 11 Nolle — Diversion
        _RESOLVED_COLOR,    # 12 Nolle — Defendant Deceased
        _PENDING_COLOR,     # 13 Nolle — Admin
        _PENDING_COLOR,     # 14 Nolle — Other Jurisdiction
        _UNRESOLVED_COLOR,  # 15 Nolle — DPNPSD / Self Defense
        _UNRESOLVED_COLOR,  # 16 Nolle — Statute of Limitations
        _UNRESOLVED_COLOR,  # 17 Nolle — Lack of Evidence
        _UNRESOLVED_COLOR,  # 18 Nolle — NP-Other
    ]

    links_raw = [
        # Disposed → top-level buckets
        (0,  1,  data["n_plea"],             f"Plea: {data['n_plea']:,} ({pct(data['n_plea']):.1f}%)",                     _PLEA_COLOR),
        (0,  2,  data["n_trial"],            f"Trial: {data['n_trial']:,} ({pct(data['n_trial']):.1f}%)",                  _TRIAL_COLOR),
        (0,  3,  data["n_nolle"],            f"Nolle Prosequi: {data['n_nolle']:,} ({pct(data['n_nolle']):.1f}%)",         _NOLLE_COLOR),
        # Plea → sub-outcomes
        (1,  4,  data["n_guilty_plea"],      f"Guilty Plea: {data['n_guilty_plea']:,} ({pct(data['n_guilty_plea']):.1f}%)",       _PLEA_COLOR),
        (1,  5,  data["n_plea_deal"],        f"Plea Deal: {data['n_plea_deal']:,} ({pct(data['n_plea_deal']):.1f}%)",             _PLEA_COLOR),
        # Trial → sub-outcomes
        (2,  6,  data["n_trial_guilty"],     f"Trial — Guilty: {data['n_trial_guilty']:,} ({pct(data['n_trial_guilty']):.1f}%)",         _PLEA_COLOR),
        (2,  7,  data["n_trial_not_guilty"], f"Trial — Not Guilty: {data['n_trial_not_guilty']:,} ({pct(data['n_trial_not_guilty']):.1f}%)", _ACQUITTAL_COLOR),
        # Nolle → resolution groups
        (3,  8,  data["n_resolved"],         f"Resolved: {data['n_resolved']:,} ({pct(data['n_resolved']):.1f}%)",         _RESOLVED_COLOR),
        (3,  9,  data["n_pending"],          f"Pending: {data['n_pending']:,} ({pct(data['n_pending']):.1f}%)",             _PENDING_COLOR),
        (3,  10, data["n_unresolved"],       f"Unresolved: {data['n_unresolved']:,} ({pct(data['n_unresolved']):.1f}%)",   _UNRESOLVED_COLOR),
        # Resolved → specific reasons
        (8,  11, rc.get(4.0, 0),  f"Nolle — Diversion: {rc.get(4.0,0):,} ({pct(rc.get(4.0,0)):.1f}%)",                   _RESOLVED_COLOR),
        (8,  12, rc.get(5.0, 0),  f"Nolle — Defendant Deceased: {rc.get(5.0,0):,} ({pct(rc.get(5.0,0)):.1f}%)",          _RESOLVED_COLOR),
        # Pending → specific reasons
        (9,  13, rc.get(6.0, 0),  f"Nolle — Admin: {rc.get(6.0,0):,} ({pct(rc.get(6.0,0)):.1f}%)",                       _PENDING_COLOR),
        (9,  14, rc.get(7.0, 0),  f"Nolle — Other Jurisdiction: {rc.get(7.0,0):,} ({pct(rc.get(7.0,0)):.1f}%)",          _PENDING_COLOR),
        # Unresolved → specific reasons
        (10, 15, rc.get(8.0, 0),  f"Nolle — DPNPSD / Self Defense: {rc.get(8.0,0):,} ({pct(rc.get(8.0,0)):.1f}%)",      _UNRESOLVED_COLOR),
        (10, 16, rc.get(9.0, 0),  f"Nolle — Statute of Limitations: {rc.get(9.0,0):,} ({pct(rc.get(9.0,0)):.1f}%)",     _UNRESOLVED_COLOR),
        (10, 17, rc.get(10.0, 0), f"Nolle — Lack of Evidence: {rc.get(10.0,0):,} ({pct(rc.get(10.0,0)):.1f}%)",         _UNRESOLVED_COLOR),
        (10, 18, rc.get(11.0, 0), f"Nolle — NP-Other: {rc.get(11.0,0):,} ({pct(rc.get(11.0,0)):.1f}%)",                 _UNRESOLVED_COLOR),
    ]

    # Filter zero-value links
    links_raw = [(s, t, v, l, c) for s, t, v, l, c in links_raw if v > 0]

    sources     = [r[0] for r in links_raw]
    targets     = [r[1] for r in links_raw]
    values      = [r[2] for r in links_raw]
    link_labels = [r[3] for r in links_raw]
    link_colors = [_rgba(r[4]) for r in links_raw]

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
            color=link_colors,
            hovertemplate="%{label}<extra></extra>",
        ),
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=10),
        height=620,
    )
    return fig


def render_disp_sankey(disp: pd.DataFrame) -> None:
    """Render a Sankey diagram of disposed cases from high-level outcome to specific reason."""
    data = _prepare_disp_sankey(disp)

    with st.container(border=True):
        st.header(":material/account_tree: Disposition Outcomes — Sankey")
        st.caption(
            "Flow diagram tracing disposed cases from high-level outcome category down to "
            "specific disposition type. Cases are classified by `min_disp_rank` — the most "
            "favorable outcome recorded per case. :green[Plea and Trial Guilty] outcomes "
            "reflect convictions; :red[Trial Not Guilty] reflects acquittals; Nolle Prosequi "
            "cases are split into :blue[Resolved], :orange[Pending], and :darkred[Unresolved]."
        )
        st.plotly_chart(_build_disp_sankey(data))
