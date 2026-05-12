# ARCHITECTURE

**Date:** [2026-05-12]

## System Design & Pattern
The system is built as a **Medallion Architecture Data Pipeline** (Bronze -> Silver -> Gold), coupled with an interactive web dashboard for visualization.

### 1. Data Pipeline (`src/pipeline/`)
The data pipeline (`pipeline.py`) orchestrates the ETL process:
- **Bronze (Ingestion)**: Reads raw CSV files from `data/` using `ingestion.py`.
- **Silver (Transform)**: Cleans, standardizes, and normalizes data (e.g., handling nulls, formatting dates) using `transform.py`. Saves intermediate state as Parquet files.
- **Gold (Enrich)**: Crosses and aggregates data (e.g., joining accidents with locality data, victim aggregations, ranking) using `enrich.py`.
- **Persist**: Handles saving datasets as Parquet files (`persist.py`).
- **Machine Learning (ML)**: Optional step to train classification models (Decision Tree, MLP, SVC) to predict injury severity using `ml.py`.

### 2. Dashboard (`app/`)
- A single-page Streamlit application (`dashboard.py`) that reads the Gold Parquet files from `data/processed/`.
- Uses in-memory caching (`@st.cache_data`) for fast subsequent loads.
- Displays key performance indicators (KPIs), Plotly interactive graphs, and ML model evaluations.

## Data Flow
`CSV (Bronze) -> Pandas DataFrames -> Parquet (Silver) -> Joined/Aggregated DataFrames -> Parquet (Gold) -> Streamlit Dashboard`

## Abstractions & Modules
- Modules are separated by responsibilities: Ingestion, Transformation, Enrichment, Persistence, and ML.
- Heavy computations (like the vehicles dataset) can be skipped via CLI flags (`--skip-heavy`).

## Entry Points
- Pipeline: `python -m src.pipeline.pipeline`
- Dashboard: `streamlit run app/dashboard.py`
