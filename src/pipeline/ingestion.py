"""
Camada de Ingestão (Bronze Layer)
----------------------------------
Responsável por ler os arquivos brutos da pasta data/ e retornar
DataFrames pandas com as colunas e tipos originais preservados.
Arquivos suportados:
  - acidentes2023.csv          → fatos de acidentes (2018-2025)
  - Vitimas_DadosAbertos.csv   → vítimas por acidente
  - TipoVeiculo_DadosAbertos.csv → veículos envolvidos
  - Localidade_20260312.csv    → dimensão de localidade (município/UF)
  - Volume_trafego_mensal.csv  → volume de tráfego mensal (Fortaleza)
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Colunas que serão lidas de cada arquivo (projeção para economizar memória)
_ACIDENTES_COLS = [
    "num_acidente", "chv_localidade", "data_acidente", "uf_acidente",
    "ano_acidente", "mes_acidente", "dia_semana", "fase_dia", "hora_acidente",
    "tp_acidente", "cond_meteorologica", "cond_pista", "tp_rodovia",
    "tp_pavimento", "lim_velocidade", "tp_pista", "bairro_acidente",
    "latitude_acidente", "longitude_acidente",
    "qtde_acidente", "qtde_acid_com_obitos", "qtde_envolvidos",
    "qtde_feridosilesos", "qtde_obitos",
]

_VITIMAS_COLS = [
    "num_acidente", "chv_localidade", "data_acidente", "uf_acidente",
    "ano_acidente", "mes_acidente", "faixa_idade", "genero", "tp_envolvido",
    "gravidade_lesao", "equip_seguranca", "ind_motorista", "susp_alcool",
    "qtde_envolvidos", "qtde_feridosilesos", "qtde_obitos",
]

_TIPO_VEICULO_COLS = [
    "num_acidente", "tipo_veiculo", "ind_veic_estrangeiro", "qtde_veiculos",
]

_LOCALIDADE_COLS = [
    "chv_localidade", "ano_referencia", "mes_referencia", "regiao", "uf",
    "codigo_ibge", "municipio", "regiao_metropolitana",
    "qtde_habitantes", "frota_total", "frota_circulante",
]

_VOLUME_COLS = ["Sitio", "DATA", "ViaSentido", "VMD", "Lon", "Lat"]


def _read_csv_chunked(
    path: Path,
    usecols: list[str] | None,
    dtype: dict | None = None,
    chunksize: int = 500_000,
) -> pd.DataFrame:
    """Lê CSVs grandes em chunks e concatena. Economiza pico de memória RAM."""
    logger.info("Ingerindo %s ...", path.name)
    chunks = []
    reader = pd.read_csv(
        path,
        sep=";",
        encoding="latin-1",
        low_memory=False,
        usecols=usecols,
        dtype=dtype,
        chunksize=chunksize,
    )
    for chunk in reader:
        chunks.append(chunk)
    df = pd.concat(chunks, ignore_index=True)
    logger.info("  → %d linhas lidas de %s", len(df), path.name)
    return df


def ingest_acidentes(data_dir: Path) -> pd.DataFrame:
    """Lê o arquivo principal de acidentes (2018-2025)."""
    path = data_dir / "acidentes2023.csv"
    dtype = {
        "hora_acidente": str,
        "bairro_acidente": str,
        "latitude_acidente": str,
        "longitude_acidente": str,
        "lim_velocidade": str,
    }
    return _read_csv_chunked(path, usecols=_ACIDENTES_COLS, dtype=dtype)


def ingest_vitimas(data_dir: Path) -> pd.DataFrame:
    """Lê o arquivo de vítimas de acidentes."""
    path = data_dir / "Vitimas_DadosAbertos_20260312.csv"
    return _read_csv_chunked(path, usecols=_VITIMAS_COLS)


def ingest_tipo_veiculo(data_dir: Path) -> pd.DataFrame:
    """Lê o arquivo de tipo de veículo por acidente."""
    path = data_dir / "TipoVeiculo_DadosAbertos_20260312.csv"
    return _read_csv_chunked(path, usecols=_TIPO_VEICULO_COLS)


def ingest_localidade(data_dir: Path) -> pd.DataFrame:
    """Lê a dimensão de localidade (município/UF/habitantes/frota)."""
    path = data_dir / "Localidade_20260312.csv"
    return _read_csv_chunked(path, usecols=_LOCALIDADE_COLS, chunksize=200_000)


def ingest_volume_trafego(data_dir: Path) -> pd.DataFrame:
    """Lê o volume de tráfego mensal (dados de Fortaleza/CE)."""
    path = data_dir / "Volume_trafego_mensal.csv"
    logger.info("Ingerindo %s ...", path.name)
    df = pd.read_csv(
        path,
        sep=",",
        encoding="latin-1",
        index_col=0,
        quotechar='"',
    )
    df.columns = [c.strip().strip('"') for c in df.columns]
    # normalizar nomes das colunas para snake_case
    col_map = {
        "Sitio": "sitio",
        "DATA": "data",
        "ViaSentido": "via_sentido",
        "VMD": "vmd",
        "Lon": "longitude",
        "Lat": "latitude",
    }
    df = df.rename(columns=col_map)
    logger.info("  → %d linhas lidas de %s", len(df), path.name)
    return df
