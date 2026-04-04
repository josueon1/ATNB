from pathlib import Path

import pandas as pd

from src.pipeline.persist import load_parquet

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"


def load_data() -> pd.DataFrame:
    """
    Carrega o dataset Gold gerado pelo pipeline.
    Contém acidentes já enriquecidos com município, UF, habitantes,
    frota, vítimas agregadas e veículo predominante.

    Pré-requisito: executar o pipeline antes de usar este módulo.
        python -m src.pipeline.pipeline --skip-heavy
    """
    return load_parquet(PROCESSED_DIR / "acidentes_gold")


def acidentes_por_estado(data_frame: pd.DataFrame) -> pd.Series:
    return data_frame.groupby("uf_acidente")["qtde_acidente"].sum().sort_values(ascending=False)


def acidentes_por_causa(data_frame: pd.DataFrame) -> pd.Series:
    return data_frame.groupby("causa_acidente")["qtde_acidente"].sum().sort_values(ascending=False).head(10)


def acidentes_por_hora(data_frame: pd.DataFrame) -> pd.Series:
    return data_frame.groupby("hora_acidente")["qtde_acidente"].sum().sort_values()


def acidentes_por_municipio(data_frame: pd.DataFrame, top: int = 20) -> pd.DataFrame:
    """Ranking de municípios com total de acidentes e óbitos."""
    return (
        data_frame.groupby(["municipio", "uf_acidente"])
        .agg(total_acidentes=("qtde_acidente", "sum"), total_obitos=("qtde_obitos", "sum"))
        .reset_index()
        .sort_values("total_acidentes", ascending=False)
        .head(top)
    )


def obitos_por_tipo_acidente(data_frame: pd.DataFrame) -> pd.Series:
    """Total de óbitos agrupados por tipo de acidente."""
    return data_frame.groupby("tipo_acidente")["qtde_obitos"].sum().sort_values(ascending=False)
