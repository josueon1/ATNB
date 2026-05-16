# CONCERNS

**Date:** [2026-05-12]

## Technical Debt & Issues
- **Missing Automated Tests**: There is a complete lack of unit and integration tests. Regressions in data transformation logic might go unnoticed until the dashboard crashes.
- **Data Size Handling**: The `TipoVeiculo` dataset is noted as being 310 MB, causing memory constraints. The codebase includes a `--skip-heavy` flag to bypass this, suggesting that local environments struggle to process it entirely in memory via Pandas.
- **Hardcoded File References**: Several file dependencies and dataset structures rely on exact naming matches and hardcoded logic, which may break if the upstream data schema changes.

## Security
- No immediate security vulnerabilities detected (the app only processes public data).
- The Streamlit app does not perform sanitization on data inputs, though inputs are read locally from Parquet files and not from users.

## Performance
- **Pandas Memory Consumption**: Pandas loads data entirely into memory. For large datasets like `vitimas` (12.5M rows), the script relies on checking existing Parquet files to prevent Out-of-Memory (OOM) exceptions. Dask is in the requirements but does not appear to be utilized effectively in the pipeline to solve out-of-core processing.
- **Caching Warnings**: Streamlit relies heavily on caching via `@st.cache_data`. Very large Parquet files might cause RAM spikes when the dashboard is loaded for the first time.

## Fragile Areas
- `setup_data.py` relies on a Google Drive file ID which can become invalid if the owner deletes the file or changes sharing settings.
- `app/dashboard.py` breaks cleanly if `data/processed` is empty, but expects all intermediate Silver and Gold data to be present if it starts reading. Partial pipeline executions might leave it in an inconsistent state.
