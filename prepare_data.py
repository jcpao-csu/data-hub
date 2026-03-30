# prepare_data.py

import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
from typing import Callable, Dict, Tuple, List

from read_data import RCVD, FLD, NTFLD, DISP

# Basic Structure of ETL: (1) import relevant DFs, (2) wrangle to desired summary DF, (3) transfer to data viz
# Caveat: important to keep in mind that session state parameters will filter data (where appropriate)

## Sankey Diagrams - (1) based on ref_date, where do cases currently stand (within the criminal justice system)?

def generate_sankey(
    rcvd: pd.DataFrame = RCVD, # may change to DF from session_state 
    fld: pd.DataFrame = FLD, 
    ntfld: pd.DataFrame = NTFLD, 
    disp: pd.DataFrame = DISP,
    date_col: str = "ref_date",
) -> pd.DataFrame:

    # Focus on cases recevied by the Office since 2016 (makes it easier for us to evaluate)

    rcvd = rcvd.loc[:,["pbk_num", "ref_date", "agency_name", "rcvd_lead_category"]].copy()
    rcvd["rcvd?"] = "Received"

    fld = fld.loc[:, ["pbk_num", "earliest_fld_date", "fld_lead_category"]].copy()
    fld["filed?"]: bool = True

    ntfld = ntfld.loc[:, ["pbk_num", "earliest_ntfld_date", "lead_ntfld_charge_category", "min_ntfld_category"]].copy()
    ntfld["not filed?"]: bool = True

    disp = disp.loc[:, ["pbk_num", "earliest_disp_date", "lead_disp_category", "lead_disp_rank"]].copy()
    disp["disposed?"]: bool = True

    # Merge on rcvd
    df = rcvd.merge(fld, on="pbk_num", how="left") # only on RCVD (2016 - current year-to-date)
    df = df.merge(ntfld, on="pbk_num", how="left")
    df = df.merge(disp, on="pbk_num", how="left")

    df[["filed?", "not filed?", "disposed?"]] = (
        df[["filed?", "not filed?", "disposed?"]].fillna(False).astype(bool)
    )

    # Referring Agency --> df["agency_grouped"]
    agency_counts = df["agency_name"].value_counts()
    top_agencies = agency_counts.head(10).index
    df["agency_grouped"] = df["agency_name"].where(df["agency_name"].isin(top_agencies), "Other Agencies") # Replace all non-top agencies with "Other Agencies"

    # Rcvd --> df["rcvd?"]

    # Review Complete / Under Review 
    df.loc[(df["filed?"]) | (df["not filed?"]), "review_status"] = "Completed Review"
    df["review_status"] = df["review_status"].fillna("Under Review")

    # Completed Review --> Fld / Ntfld? 
    df.loc[(df["review_status"]=="Completed Review") & (df["filed?"]), "review_status_type"] = "Filed"
    df.loc[(df["review_status"]=="Completed Review") & (df["not filed?"]), "review_status_type"] = "Not Filed"

    # Ntfld --> Reasoning: df["min_ntfld_category"]
    
    # Open (Pending) / Disposed 
    df.loc[(df["filed?"]) & (df["disposed?"]), "file_status"] = "Open"
    df.loc[(df["filed?"]) & (~df["disposed?"]), "file_status"] = "Closed"

    # Closed --> Outcomes
    disp_dict = {
        1: 'Trial (Guilty)',
        2: 'Guilty Plea',
        3: 'Plea Deal', # Same as Guilty Plea
        4: 'Diversion',
        5: 'Defendant Deceased',
        6: 'Re-filed',
        7: 'Other Jurisdiction',
        7.5: 'Trial (Not Guilty)',
        8: 'Self Defense',
        9: 'Statute of Limitations',
        10: 'Lack of Evidence',
        11: 'Other Reason'
    }
    df["disposed_outcome"] = df["lead_disp_rank"].map(disp_dict)

    ## Generate Sankey data from DF

    # Define stage columns and branch logic
    cols = [
        "agency_grouped", # Referring police agency
        "rcvd?", # Case received by the Office
        "review_status", # Completed review or still under review?
        "review_status_type", # Completed review: Filed or Not Filed?
        "file_status", # Filed: Open or Closed?
        "min_ntfld_category", # Not Filed: Reason for Not Filing?
        "lead_disp_rank", # Closed: Disposed Outcome? "disposed_outcome"
    ]

    logic = {
        "review_status": {
            "Under Review": None,
            "Completed Review": "review_status_type"
        },
        "review_status_type": {
            "Not Filed": "min_ntfld_category",
            "Filed": "file_status"
        },
        "file_status": {
            "Open": None,
            "Closed": "lead_disp_rank" # disposed_outcome
        }
    }

    # Define calculate_edges() function
    def calculate_edges(
        df: pd.DataFrame, 
        stage_cols: list[str] = cols, 
        branch_rules: dict = logic,
    ) -> pd.DataFrame:
        """Computes edges for Sankey diagram (source, target, value)"""

        # Initialize edges list 
        edges = []

        # Iterate over cols
        for i, col in enumerate(stage_cols[:-1]):
            next_col = stage_cols[i + 1]
            prefix_col = lambda s: f"{col}: {s}" if pd.notna(s) else None
            prefix_next = lambda s: f"{next_col}: {s}" if pd.notna(s) else None

            if col in branch_rules:
                for val, nxt in branch_rules[col].items():
                    if nxt:
                        subset = df[df[col] == val].copy()
                        edge_data = (
                            subset
                            .groupby([col, nxt])
                            .size()
                            .reset_index(name="value")
                            .rename(columns={col: "source", nxt: "target"})
                        )
                        # Apply prefixes
                        edge_data["source"] = edge_data["source"].map(prefix_col)
                        edge_data["target"] = edge_data["target"].map(prefix_next)
                        edges.append(edge_data)
            else:
                edge_data = (
                    df.groupby([col, next_col])
                    .size()
                    .reset_index(name="value")
                    .rename(columns={col: "source", next_col: "target"})
                )
                # Apply prefixes
                edge_data["source"] = edge_data["source"].map(prefix_col)
                edge_data["target"] = edge_data["target"].map(prefix_next)
                edges.append(edge_data)

        return pd.concat(edges, ignore_index=True)

    # Convert edges to Plotly format (→)
    def generate_sankey(
        edges_df: pd.DataFrame, 
        title: str = "Received Cases Flow Chart" # include filtered date range / category / etc?
    ):
        # Get all unique nodes
        # node_labels = pd.unique(edges_df[["source", "target"]].values.ravel("K")).tolist()
        node_labels = sorted(
            pd.unique(edges_df[["source", "target"]].values.ravel("K")),
            key=lambda x: (x != "Other Agencies", x)
        )
        display_labels = [lbl.split(": ", 1)[1] if ": " in lbl else lbl for lbl in node_labels]

        node_indices = {label: i for i, label in enumerate(node_labels)}

        # Map source/target names → indices
        edges_df["source_id"] = edges_df["source"].map(node_indices)
        edges_df["target_id"] = edges_df["target"].map(node_indices)

        # Build figure
        fig = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        pad=15,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                        label=display_labels, # node_labels
                        color="lightgray"
                    ),
                    link=dict(
                        source=edges_df["source_id"],
                        target=edges_df["target_id"],
                        value=edges_df["value"],
                    ),
                )
            ]
        )
        fig.update_layout(title_text=title, font_size=12)

        return fig
    
    # Generate Sankey diagram
    edges = calculate_edges(df)
    fig = generate_sankey(edges)
    fig.show()

    # Display in Streamlit app
    st.write(edges)
    st.plotly_chart(fig, width="container")


    def calculate_edges(
        df: pd.DataFrame,
        stage_cols: List[str],
        transition_rules: Dict[Tuple[str, str], Callable[[pd.DataFrame], pd.Series]] = None,
        prefix_nodes: bool = True,
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Turn df + ordered stage_cols into sankey edges (source, target, value) and node list.

        Parameters
        ----------
        df : pd.DataFrame -- input dataframe
        stage_cols : list[str] -- Ordered list of stage column names
        transition_rules : dict[(src, tgt) -> callable(df)->mask]  
            Optional: mask functions per (src, tgt). If provided, they are (&) ANDed with non-null checks.
            The callable receives the full df and returns a boolean Series to filter rows for that transition.
        prefix_nodes : bool -- If TRUE, node labels become "stage: value" to avoid label collisions across stages.

        Returns
        -------
        edges: pd.DataFrame with columns ["source", "target", "value"]
        nodes: list[str] ordered by stage appearance (good for Sankey node order)
        """

        # Copy df 
        df = df.copy()

        # default transition rules to enforce terminal logic you described
        default_rules = {
            ("review_status", "review_status_type"): lambda d: d["review_status"] == "Completed Review",
            ("review_status_type", "min_ntfld_category"): lambda d: d["review_status_type"] == "Not Filed",
            ("review_status_type", "file_status"): lambda d: d["review_status_type"] == "Filed",
            ("file_status", "disposed_outcome"): lambda d: d["file_status"] == "Closed",  # or d["disposed?"]
            # agency_name -> rcvd? and rcvd? -> review_status are generally unconditional (all rows)
        }
        if transition_rules:
            default_rules.update(transition_rules)

        flows = []
        for i in range(len(stage_cols) - 1):
            src = stage_cols[i]
            tgt = stage_cols[i + 1]

            # skip if either column missing
            if src not in dfc.columns or tgt not in dfc.columns:
                continue

            # base mask: both values non-null
            mask = dfc[src].notna() & dfc[tgt].notna()

            # apply rule if exists
            rule = default_rules.get((src, tgt))
            if rule is not None:
                mask &= rule(dfc)

            # build grouped counts
            tmp = (
                dfc.loc[mask, [src, tgt]]
                .groupby([src, tgt], dropna=False)
                .size()
                .reset_index(name="value")
            )

            if tmp.empty:
                continue

            # optionally prefix stage to values (keeps nodes unique & readable)
            if prefix_nodes:
                tmp["source"] = tmp[src].astype(str).apply(lambda v, s=src: f"{s}: {v}")
                tmp["target"] = tmp[tgt].astype(str).apply(lambda v, s=tgt: f"{s}: {v}")
            else:
                tmp["source"] = tmp[src].astype(str)
                tmp["target"] = tmp[tgt].astype(str)

            flows.append(tmp[["source", "target", "value"]])

        # aggregate across all transitions (in case same source->target appear in different adjacent pairs)
        if flows:
            edges = pd.concat(flows, ignore_index=True).groupby(["source", "target"], as_index=False)["value"].sum()
        else:
            edges = pd.DataFrame(columns=["source", "target", "value"])

        # build nodes in stage order (preserve left->right ordering)
        nodes = []
        for stage in stage_cols:
            if stage not in dfc.columns:
                continue
            vals = dfc.loc[dfc[stage].notna(), stage].astype(str).unique().tolist()
            for v in vals:
                label = f"{stage}: {v}" if prefix_nodes else v
                if label not in nodes:
                    nodes.append(label)

        # ensure every source/target from edges present in nodes (they should be) - append any missing
        missing_nodes = [x for x in pd.unique(edges[["source", "target"]].values.ravel()) if x not in nodes]
        nodes.extend(missing_nodes)

        return edges, nodes
    
    # Source (starting node)

    # Target (destination node)

    # Value 

generate_sankey()


# fig = go.Figure(data=[go.Sankey(
#     node = dict(
#       pad = 15,
#       thickness = 20,
#       line = dict(color = "black", width = 0.5),
#       label = ["A1", "A2", "B1", "B2", "C1", "C2"],
#       color = "blue"
#     ),
#     link = dict(
#       source = [0, 1, 0, 2, 3, 3], # indices correspond to labels, eg A1, A2, A1, B1, ...
#       target = [2, 3, 3, 4, 4, 5],
#       value = [8, 4, 2, 8, 4, 2]
#   ))])

# fig.update_layout(title_text="Basic Sankey Diagram", font_size=10)
# fig.show()