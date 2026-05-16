# STACK

**Date:** [2026-05-12]

## Languages
- **Python 3**: Primary language for data processing, machine learning, and dashboard development.

## Frameworks & Libraries
- **Pandas**: Core data manipulation and processing (`src/pipeline/`).
- **Streamlit**: Web framework used for the interactive dashboard (`app/dashboard.py`).
- **Plotly**: Interactive data visualization (`app/dashboard.py`).
- **Scikit-Learn**: Machine learning models (`src/pipeline/ml.py`).
- **PyArrow**: Handling parquet file reading/writing optimizations.
- **Dask**: Listed in requirements (`dask[dataframe]`), likely for handling large out-of-core datasets if needed.
- **NumPy**: Numerical operations.

## Runtime & Environments
- **Virtual Environment**: `.venv` using standard `python -m venv`.
- **Docker**: Containerized deployment via `Dockerfile` and `docker-compose.yml`.

## Dependencies
- Managed via `requirements.txt`.
- Includes `pandas`, `streamlit`, `plotly`, `pyarrow`, `dask[dataframe]`, `numpy`, `scikit-learn`.

## Configuration
- Pipeline arguments parsed via `argparse` in `src/pipeline/pipeline.py` (e.g., `--skip-heavy`, `--ano`).
