# STRUCTURE

**Date:** [2026-05-12]

## Directory Layout
```
/
├── app/
│   └── dashboard.py           # Streamlit web application
├── data/                      # Data storage (git-ignored for the most part)
│   ├── processed/             # Output directory for Silver/Gold Parquet files
│   └── *.csv                  # Raw Bronze CSV datasets
├── src/
│   └── pipeline/              # ETL Pipeline module
│       ├── __init__.py
│       ├── pipeline.py        # Orchestrator
│       ├── ingestion.py       # Data reading
│       ├── transform.py       # Data cleaning
│       ├── enrich.py          # Data aggregation/joining
│       ├── persist.py         # File I/O
│       └── ml.py              # Machine Learning scripts
├── .streamlit/                # Streamlit configuration folder
├── .claude/                   # Claude Code settings and prompts
├── .venv/                     # Python virtual environment
├── Dockerfile                 # Docker configuration
├── docker-compose.yml         # Multi-container Docker configuration
├── requirements.txt           # Python dependencies
├── setup_data.py              # Helper script to fetch data from Google Drive
├── README.md                  # Project documentation
├── FLUXO_DA_APLICACAO.md      # Detailed documentation of the application flow
└── REFERENCIAS.md             # Project references
```

## Key Locations
- **`app/dashboard.py`**: The frontend UI where users interact with the data.
- **`src/pipeline/pipeline.py`**: The main execution script for data processing.
- **`data/processed/`**: Crucial directory where the dashboard pulls its optimized `.parquet` files.

## Naming Conventions
- Snake_case is used for Python files and variables (`pipeline.py`, `total_acidentes`).
- Parquet files follow layer naming conventions (e.g., `localidade_silver.parquet`, `acidentes_gold`).
