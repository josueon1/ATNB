# CONVENTIONS

**Date:** [2026-05-12]

## Code Style
- **Python**: Follows standard PEP 8 conventions.
- **Typing**: Uses type hinting on function signatures (e.g., `def run_pipeline(skip_heavy: bool = False, ano_filtro: int | None = None) -> None:`).
- **Docstrings**: Uses standard docstrings for module and function descriptions.

## Naming
- Functions prefix internal operations with an underscore (e.g., `_silver_exists`, `_print_summary`).
- Descriptive variable names are preferred over abbreviations (`df_acidentes`, `df_tipo_veiculo`).
- Constants are in ALL_CAPS (`ROOT`, `DATA_DIR`, `PROCESSED_DIR`).

## Patterns
- **Separation of Concerns**: The pipeline is strictly divided into steps (`ingestion`, `transform`, `enrich`, `persist`).
- **Memory Management**: Uses `del` explicitly to free memory after processing large DataFrames (`del df_acidentes_raw`).
- **Caching**: Dashboard aggressively caches file reading operations using `@st.cache_data`.
- **Idempotency Check**: The pipeline checks if intermediate files exist (e.g., `vitimas_silver`) and skips processing to save time and memory.

## Error Handling
- Currently, standard Python exception propagation is used.
- Assumes the presence of CSVs; missing processed files in the dashboard triggers a user-friendly `st.error()` and stops execution using `st.stop()`.
- Extensive use of the `logging` module to output progress and trace data execution paths.
