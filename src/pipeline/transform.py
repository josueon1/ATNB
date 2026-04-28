"""
Camada de Transformação (Silver Layer)
----------------------------------------
Responsável por:
  1. Padronizar nomes e tipos de colunas
  2. Parsear datas e horas
  3. Tratar valores nulos / inconsistências
  4. Normalizar strings categóricas
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Valores considerados nulos em campos de texto
_NULL_STRINGS = {"NAO INFORMADO", "DESCONHECIDO", "DESCONHECIDAS", "NAO INFORMADA", ""}


def _normalize_str_col(series: pd.Series) -> pd.Series:
    """Strip, upper, substitui strings nulas por pd.NA."""
    s = series.astype(str).str.strip().str.upper()
    return s.where(~s.isin(_NULL_STRINGS), other=pd.NA)


def _parse_hora(series: pd.Series) -> pd.Series:
    """
    Converte hora no formato HHMMSS (inteiro) para hora inteira (0-23).
    Ex: 214400 → 21, 94000 → 9
    """
    s = series.astype(str).str.zfill(6)
    return pd.to_numeric(s.str[:2], errors="coerce").astype("Int8")


def transform_acidentes(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica limpeza e transformações ao DataFrame de acidentes."""
    logger.info("Transformando acidentes (%d linhas)...", len(df))
    df = df.copy()

    # ── 1. Nomes de colunas em snake_case ─────────────────────────────────
    df.columns = df.columns.str.strip().str.lower()

    # ── 2. Parsing de data e hora ─────────────────────────────────────────
    df["data_acidente"] = pd.to_datetime(df["data_acidente"], errors="coerce")
    df["hora"] = _parse_hora(df["hora_acidente"]).fillna(0)
    df["ano_acidente"] = df["ano_acidente"].astype("Int16")
    df["mes_acidente"] = df["mes_acidente"].astype("Int8")

    # ── 3. Coordenadas geográficas ────────────────────────────────────────
    df["latitude_acidente"] = pd.to_numeric(
        df["latitude_acidente"].astype(str).str.replace(",", "."),
        errors="coerce",
    )
    df["longitude_acidente"] = pd.to_numeric(
        df["longitude_acidente"].astype(str).str.replace(",", "."),
        errors="coerce",
    )
    # Coordenadas fora dos limites do Brasil → nulas
    lat_mask = df["latitude_acidente"].between(-33.8, 5.3)
    lon_mask = df["longitude_acidente"].between(-73.9, -34.7)
    df.loc[~lat_mask, "latitude_acidente"] = np.nan
    df.loc[~lon_mask, "longitude_acidente"] = np.nan

    # ── 4. Colunas numéricas ──────────────────────────────────────────────
    for col in ["qtde_acidente", "qtde_acid_com_obitos", "qtde_envolvidos",
                "qtde_feridosilesos", "qtde_obitos"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("Int32")

    # lim_velocidade pode vir como texto "80 km/h" ou número
    df["lim_velocidade"] = pd.to_numeric(
        df.get("lim_velocidade", pd.Series(dtype=str))
          .astype(str).str.extract(r"(\d+)")[0],
        errors="coerce",
    ).fillna(0).astype("Int16")

    # ── 5. Colunas categóricas ────────────────────────────────────────────
    str_cols = [
        "uf_acidente", "dia_semana", "fase_dia", "tp_acidente",
        "cond_meteorologica", "cond_pista", "tp_rodovia", "tp_pavimento",
        "tp_pista", "bairro_acidente", "end_acidente",
    ]
    for col in str_cols:
        if col in df.columns:
            df[col] = _normalize_str_col(df[col])

    # Categorias conhecidas → dtype category para economizar memória
    cat_cols = [
        "uf_acidente", "dia_semana", "fase_dia", "tp_acidente",
        "cond_meteorologica", "cond_pista", "tp_rodovia", "tp_pista",
    ]
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].astype("category")

    # ── 6. Remover colunas auxiliares brutas ──────────────────────────────
    df.drop(columns=["hora_acidente"], inplace=True, errors="ignore")

    logger.info("  → acidentes transformados: %d linhas, %d colunas", *df.shape)
    return df


def transform_vitimas(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica limpeza e transformações ao DataFrame de vítimas."""
    logger.info("Transformando vítimas (%d linhas)...", len(df))
    df = df.copy()

    df.columns = df.columns.str.strip().str.lower()

    df["data_acidente"] = pd.to_datetime(df["data_acidente"], errors="coerce")
    df["ano_acidente"] = df["ano_acidente"].astype("Int16")
    df["mes_acidente"] = df["mes_acidente"].astype("Int8")

    for col in ["qtde_envolvidos", "qtde_feridosilesos", "qtde_obitos"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("Int32")

    str_cols = [
        "faixa_idade", "genero", "tp_envolvido", "gravidade_lesao",
        "equip_seguranca", "ind_motorista", "susp_alcool", "uf_acidente",
    ]
    for col in str_cols:
        df[col] = _normalize_str_col(df[col])

    cat_cols = [
        "faixa_idade", "genero", "tp_envolvido", "gravidade_lesao",
        "equip_seguranca", "ind_motorista", "susp_alcool", "uf_acidente",
    ]
    for col in cat_cols:
        df[col] = df[col].astype("category")

    # Flag binária de óbito
    df["flag_obito"] = (df["qtde_obitos"] > 0).astype("Int8")

    logger.info("  → vítimas transformadas: %d linhas", len(df))
    return df


def transform_tipo_veiculo(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica limpeza ao DataFrame de tipo de veículo."""
    logger.info("Transformando tipo veículo (%d linhas)...", len(df))
    df = df.copy()

    df.columns = df.columns.str.strip().str.lower()
    df["tipo_veiculo"] = _normalize_str_col(df["tipo_veiculo"])
    df["ind_veic_estrangeiro"] = _normalize_str_col(df["ind_veic_estrangeiro"])
    df["qtde_veiculos"] = pd.to_numeric(df["qtde_veiculos"], errors="coerce").fillna(1).astype("Int16")

    df["tipo_veiculo"] = df["tipo_veiculo"].astype("category")

    logger.info("  → tipo veículo transformado: %d linhas", len(df))
    return df


def transform_localidade(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma a dimensão de localidade.
    Mantém apenas o snapshot mais recente por município (maior mes_ano_referencia).
    """
    logger.info("Transformando localidade (%d linhas)...", len(df))
    df = df.copy()

    df.columns = df.columns.str.strip().str.lower()

    for col in ["qtde_habitantes", "frota_total", "frota_circulante"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("Int64")

    df["codigo_ibge"] = df["codigo_ibge"].astype(str).str.strip()
    df["municipio"] = _normalize_str_col(df["municipio"])
    df["regiao"] = _normalize_str_col(df["regiao"])
    df["uf"] = _normalize_str_col(df["uf"])

    # Manter o registro mais recente por chave localidade
    df = df.sort_values(["chv_localidade", "ano_referencia", "mes_referencia"])
    df = df.drop_duplicates(subset=["chv_localidade"], keep="last")

    # Calcular taxa de motorização (veículos por habitante)
    mask = df["qtde_habitantes"] > 0
    df["taxa_motorizacao"] = np.where(
        mask,
        (df["frota_circulante"] / df["qtde_habitantes"]).round(4),
        np.nan,
    )

    logger.info("  → localidade transformada: %d municípios únicos", len(df))
    return df


def transform_volume_trafego(df: pd.DataFrame) -> pd.DataFrame:
    """Transforma os dados de volume de tráfego mensal."""
    logger.info("Transformando volume de tráfego (%d linhas)...", len(df))
    df = df.copy()

    df["vmd"] = pd.to_numeric(df["vmd"], errors="coerce").fillna(0).astype("Int32")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce").fillna(0)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce").fillna(0)
    df["data"] = pd.to_datetime(df["data"], format="%Y-%m", errors="coerce")
    df["ano"] = df["data"].dt.year.astype("Int16")
    df["mes"] = df["data"].dt.month.astype("Int8")

    logger.info("  → volume de tráfego transformado: %d linhas", len(df))
    return df
