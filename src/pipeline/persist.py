"""
Camada de Persistência (Parquet)
----------------------------------
Responsável por salvar os datasets processados no formato Parquet,
com particionamento inteligente para otimizar leituras analíticas.

Estratégia de particionamento:
  - acidentes_gold     → particionado por ano_acidente e uf_acidente
  - vitimas_silver     → particionado por ano_acidente
  - tipo_veiculo_silver → sem partição (arquivo menor)
  - localidade_silver  → sem partição (dimensão pequena)
  - ranking_locais     → sem partição (resultado analítico)
  - analise_temporal/* → sem partição (pequenos)
  - correlacao_frota   → sem partição (resultado analítico)
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_parquet(
    df: pd.DataFrame,
    path: Path,
    partition_cols: list[str] | None = None,
) -> None:
    """
    Salva DataFrame em Parquet.
    - Se partition_cols informado → usa write_to_dataset do pyarrow (hive partitioning)
    - Caso contrário → salva arquivo único
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.Table.from_pandas(df, preserve_index=False)

    if partition_cols:
        _ensure_dir(path)
        pq.write_to_dataset(
            table,
            root_path=str(path),
            partition_cols=partition_cols,
            existing_data_behavior="delete_matching",
        )
        logger.info(
            "  → salvo em %s (particionado por %s) | %d linhas",
            path, partition_cols, len(df),
        )
    else:
        _ensure_dir(path.parent)
        pq.write_table(table, str(path), compression="snappy")
        logger.info("  → salvo em %s | %d linhas", path, len(df))


# ────────────────────────────────────────────────────────────────────────────
# Funções públicas
# ────────────────────────────────────────────────────────────────────────────

def save_acidentes_gold(df: pd.DataFrame, processed_dir: Path) -> None:
    """Salva dataset Gold de acidentes particionado por ano e UF."""
    # Garantir que as colunas de partição sejam strings simples (não category)
    df = df.copy()
    df["ano_acidente"] = df["ano_acidente"].astype(str)
    df["uf_acidente"] = df["uf_acidente"].astype(str)
    _save_parquet(
        df,
        processed_dir / "acidentes_gold",
        partition_cols=["ano_acidente", "uf_acidente"],
    )


def save_vitimas_silver(df: pd.DataFrame, processed_dir: Path) -> None:
    """Salva dataset Silver de vítimas particionado por ano."""
    df = df.copy()
    df["ano_acidente"] = df["ano_acidente"].astype(str)
    _save_parquet(
        df,
        processed_dir / "vitimas_silver",
        partition_cols=["ano_acidente"],
    )


def save_tipo_veiculo_silver(df: pd.DataFrame, processed_dir: Path) -> None:
    """Salva dataset Silver de tipo veículo."""
    _save_parquet(df, processed_dir / "tipo_veiculo_silver.parquet")


def save_localidade_silver(df: pd.DataFrame, processed_dir: Path) -> None:
    """Salva dimensão de localidade."""
    _save_parquet(df, processed_dir / "localidade_silver.parquet")


def save_ranking_locais(df: pd.DataFrame, processed_dir: Path) -> None:
    """Salva ranking de locais com mais acidentes."""
    _save_parquet(df, processed_dir / "ranking_locais.parquet")


def save_analise_temporal(
    temporal: dict[str, pd.DataFrame], processed_dir: Path
) -> None:
    """Salva cada subdataset de análise temporal em arquivo próprio."""
    dest = processed_dir / "analise_temporal"
    _ensure_dir(dest)
    for name, df in temporal.items():
        _save_parquet(df, dest / f"{name}.parquet")


def save_correlacao_frota(df: pd.DataFrame, processed_dir: Path) -> None:
    """Salva dataset de correlação frota x acidentes."""
    _save_parquet(df, processed_dir / "correlacao_frota_acidentes.parquet")


def save_volume_trafego_silver(df: pd.DataFrame, processed_dir: Path) -> None:
    """Salva dataset Silver de volume de tráfego."""
    _save_parquet(df, processed_dir / "volume_trafego_silver.parquet")


# ────────────────────────────────────────────────────────────────────────────
# Leitura utilitária (para o dashboard)
# ────────────────────────────────────────────────────────────────────────────

def load_parquet(path: Path, filters: list | None = None) -> pd.DataFrame:
    """
    Lê um arquivo ou dataset Parquet.
    Aceita tanto arquivos únicos quanto diretórios particionados.
    """
    import pyarrow.parquet as pq

    if path.is_dir():
        dataset = pq.ParquetDataset(str(path), filters=filters, use_legacy_dataset=False)
        return dataset.read_pandas().to_pandas()
    return pd.read_parquet(str(path), engine="pyarrow", filters=filters)
