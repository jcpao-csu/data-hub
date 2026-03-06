import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from read_data import RCVD, FLD, NTFLD, DISP

st.title("Custom Tooltip Sankey Example")

labels = ["Received", "Filed", "Not Filed", "Disposed"]
source = [0, 0, 0, 1, 1, 2]
target = [1, 2, 3, 3, 2, 3]
value = [100, 50, 20, 60, 20, 30]

# Custom tooltip text for each link
tooltip_text = [
    "100 cases from Received → Filed",
    "50 cases from Received → Not Filed",
    "20 cases from Received → Disposed",
    "60 cases from Filed → Disposed",
    "20 cases from Filed → Not Filed",
    "30 cases from Not Filed → Disposed"
]

fig = go.Figure(go.Sankey(
    node=dict(
        label=labels,
        color="blue"
    ),
    link=dict(
        source=source,
        target=target,
        value=value,
        customdata=tooltip_text,  # attach custom tooltip
        hovertemplate='%{customdata}<extra></extra>'  # display it
    )
))

fig.update_layout(title_text="Case Status Flow with Custom Tooltips", font_size=12)

st.plotly_chart(fig, use_container_width=True)

# To wrangle

## total cases by agency

## total cases by year

## total cases by crime category

## unique defendants -- pbk_def_id, def_sex, def_race, 

## 


## Get the life of a case (by ref_date) -- RCVD cases metric 
def case_life(
    rcvd: pd.DataFrame,
    fld: pd.DataFrame,
    ntfld: pd.DataFrame,
    disp: pd.DataFrame
) -> pd.DataFrame:

    # ntfld_dict
    ntfld_dict = {
        0: 'Plea Deal', # resolved
        1: 'Suspect Deceased',
        2: 'Plea Deal', # pending
        3: 'PFI',
        4: 'Other Jurisdiction',
        5: 'Self Defense',
        6: 'Statute of Limitations',
        7: 'Suppression',
        8: 'Uncooperative Party',
        9: 'Lack of Evidence',
        10: 'Other Reason'
    }

    # disp_dict
    disp_dict = {
        1: 'Trial - Guilty Verdict',
        2: 'Guilty Plea',
        3: 'Guilty Plea - Plea Deal',
        4: 'Diversion',
        5: 'Defendant Deceased',
        6: 'Re-filed',
        7: 'Other Jurisdiction',
        7.5: 'Trial - Not Guilty Verdict',
        8: 'Self Defense',
        9: 'Statute of Limitations',
        10: 'Lack of Evidence',
        11: 'Other Reason'
    }

    
    # Keep relevant data from DFs
    rcvd = rcvd[['pbk_num', 'ref_date']]
    fld = fld[['pbk_num', 'ref_date', 'earliest_fld_date']]
    fld['fld'] = 'Filed'
    ntfld = ntfld[['pbk_num', 'ref_date', 'earliest_ntfld_date', 'min_ntfld_category']]
    ntfld['ntfld'] = 'Not Filed'
    disp = disp[['pbk_num', 'ref_date', 'earliest_disp_date', 'min_disp_rank']]
    disp['disp'] = 'Disposed'
    disp['min_disp_category'] = disp['min_disp_rank'].map(disp_dict)

    # Define merge_ref_date() function
    def merge_ref_date(dfs: list[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame], on: str, how: str = "left"):
        """
        Merge multiple DataFrames on a key column, filling missing values from subsequent DataFrames.
        
        Parameters:
        - dfs: list of pd.DataFrame
        - on: column to merge on (str)
        - how: merge method (default "outer")
        
        Returns:
        - merged DataFrame with filled values
        """

        if not dfs:
            return pd.DataFrame()
        
        # Start with the first DataFrame
        merged = dfs[0].copy()
        
        for df in dfs[1:]:
            df_copy = df.copy()
            
            # Identify overlapping columns besides the key
            overlap_cols = [c for c in df_copy.columns if c in merged.columns and c != on]
            
            # Merge the next DataFrame
            merged = merged.merge(df_copy, on=on, how=how, suffixes=("", "_dup"))
            
            # For overlapping columns, fill missing in original with duplicate
            for col in overlap_cols:
                merged[col] = merged[col].fillna(merged[f"{col}_dup"])
                merged.drop(columns=[f"{col}_dup"], inplace=True)
        
        return merged

    # Merge DFs
    dfs = [rcvd, fld, ntfld, disp]
    df = merge_ref_date(dfs, "pbk_num")

    # Step 1: Define stages
    df["file_stage"] = df.apply(lambda row: "Filed" if row["fld"] == 1 else row["min_ntfld_category"], axis=1)
    df["disp_stage"] = df["min_disp_category"].fillna("Not Disposed")

    # Step 2: Build source-target-value table
    # Referred -> Filed/Not Filed
    stage1 = df.groupby(["ref_date", "file_stage"]).size().reset_index(name="value")
    stage1 = stage1.rename(columns={"ref_date": "source", "file_stage": "target"})

    # Filed/Not Filed -> Disposed
    stage2 = df.groupby(["file_stage", "disp_stage"]).size().reset_index(name="value")
    stage2 = stage2.rename(columns={"file_stage": "source", "disp_stage": "target"})

    # Combine stages
    sankey_df = pd.concat([stage1, stage2], ignore_index=True)

    # Step 3: Map labels to indices
    labels = list(pd.unique(sankey_df[["source", "target"]].values.ravel()))
    label_map = {label: i for i, label in enumerate(labels)}

    sankey_df["source_idx"] = sankey_df["source"].map(label_map)
    sankey_df["target_idx"] = sankey_df["target"].map(label_map)

    # Step 4: Create Sankey diagram
    fig = go.Figure(go.Sankey(
        node=dict(
            label=labels,
            color="blue"
        ),
        link=dict(
            source=sankey_df["source_idx"],
            target=sankey_df["target_idx"],
            value=sankey_df["value"],
            hovertemplate='%{source.label} → %{target.label}: %{value}<extra></extra>'
        )
    ))

    fig.update_layout(title_text="Case Flow Sankey Diagram", font_size=12)

    st.plotly_chart(fig, use_container_width=True)

    st.write(dfs)

case_life(RCVD, FLD, NTFLD, DISP)


# Received cases - by agency
rcvd -> fld 
rcvd -> ntfld 
rcvd -> under review

# Filed cases - 
fld -> disp
fld -> open / pending 

# Not Filed cases - reasons 
ntfld -> fld? 


# Disposed cases - outcomes