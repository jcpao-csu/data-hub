# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Public data hub for the Jackson County Prosecuting Attorney's Office (JCPAO), deployed on [Streamlit Community Cloud](https://streamlit.io/cloud). Visualizes criminal case data (received, filed, not filed, disposed) from a NeonDB PostgreSQL database via SQLAlchemy.

## Common Commands

```bash
# Run the app locally
streamlit run streamlit_app.py

# Install dependencies (uses uv)
uv sync

# Lint
ruff check .

# Format
ruff format .
```

## Architecture

### Entry Point
`streamlit_app.py` — sets page config, renders the sidebar, and defines all navigation via `st.navigation()`. Pages are organized into sections: *Prosecuting Cases*, *Domestic Violence*, *Family Support Division (FSD)*, and *Resources*.

### Data Layer
- **`read_data.py`** — connects to NeonDB (via `st.secrets["sqlalchemy"]["database_url"]` in production, or `../jcpao-csu.env` locally). Exposes module-level DataFrames: `RCVD`, `FLD`, `NTFLD`, `DISP`, `AGENCIES`, `MSHP_CODES`. Uses `@st.cache_data(ttl=3600)` for queries and `@st.cache_resource` for the connection pool.
- **`session_state.py`** — the single source of truth for filter state. Pages must **never import directly from `read_data.py`** — they call `get_filtered_data()` which returns `(rcvd, fld, ntfld, disp)` filtered and annotated per sidebar selections.

### Session State & Sidebar
`session_state.py` manages all filter state keys (`date_range_filter`, `period_freq_filter`, `charge_category_filter`, `police_agency_filter`, `def_race_filter`, `def_sex_filter`). Call order in `streamlit_app.py`:
1. `initialize_session_state()` — sets defaults if keys don't exist
2. `render_sidebar()` inside `with st.sidebar:` — renders the filter form

### Key Tables (NeonDB)
| DataFrame | SQL Table | Primary Date Column |
|-----------|-----------|---------------------|
| `RCVD` | `karpel_rcvd` | `ref_date` |
| `FLD` | `karpel_fld` | `earliest_fld_date` |
| `NTFLD` | `karpel_ntfld` | `earliest_ntfld_date` |
| `DISP` | `karpel_disp` | `earliest_disp_date` |

All tables share a `pbk_num` case identifier. Cases can be tracked across their lifecycle: received → filed/not filed → disposed.

### Pages
Organized under `pages/` by section:
- `case_pages/` — case processing overview and sub-views (received, filed, not filed, disposed)
- `dv_pages/` — domestic violence cases, IPV, harassment, stalking
- `fsd_pages/` — Family Support Division stats
- `resources_pages/` — static info (about, process, charge codes)
- `violence_pages/` — violent crime review (currently commented out in nav)

### Visualization Libraries
- **Altair** — primary charting library for most bar/line/area charts
- **Plotly** — used for Sankey diagrams
- Charts follow the dark navy theme defined in `.streamlit/config.toml`

### Loose Root-Level Modules
Several files at the root are in-progress utilities (not imported by production pages):
- `dashboard_stats.py` — stat/chart functions (YTD metrics, time series)
- `prepare_data.py` — Sankey diagram prototype
- `wrangle_data.py` — early Sankey/data wrangling experiments
- `dv_data.py`, `heatmap.py`, `treemap.py`, `age_histogram.py`, etc. — domain-specific chart helpers

### Secrets & Local Dev
- **Production**: secrets in Streamlit Cloud; accessed via `st.secrets["sqlalchemy"]["database_url"]`
- **Local**: `../jcpao-csu.env` (parent directory, not committed). The app falls back to `os.getenv("SQLALCHEMY_DATABASE_URL")` when `st.secrets` is unavailable.

## Deployment

Pushes to `main` trigger automatic redeployment on Streamlit Community Cloud.
