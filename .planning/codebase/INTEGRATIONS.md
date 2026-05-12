# INTEGRATIONS

**Date:** [2026-05-12]

## External Services & APIs
- Currently, no real-time external APIs are called during execution.
- Data is sourced offline from public datasets (Polícia Rodoviária Federal, SENATRAN, Portal Brasileiro de Dados Abertos).

## Databases
- No traditional relational databases are used (e.g., PostgreSQL, MySQL).
- Data storage relies entirely on flat files (`.csv`) for ingestion and `.parquet` files for processed data (Silver/Gold layers).

## Auth Providers
- None. The Streamlit dashboard is publicly accessible without authentication.

## Third-Party Platforms
- **Streamlit Community Cloud**: The project has documentation explicitly supporting deployment to Streamlit Cloud.
- **Google Drive**: Used for hosting large processed datasets (`processed_data.zip`) that exceed GitHub's file size limits. The script `setup_data.py` downloads data directly from Google Drive using a file ID.
- **Docker**: Supported for isolated execution via `docker-compose`.
