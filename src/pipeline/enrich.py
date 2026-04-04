"""
Camada de Enriquecimento / Cruzamento (Gold Layer)
----------------------------------------------------
Responsável por cruzar as fontes transformadas e produzir
datasets analíticos prontos para consumo:

  1. acidentes_enriquecidos  → acidentes + município/UF/habitantes/frota
  2. acidentes_com_vitimas   → agregação de vítimas por acidente
  3. acidentes_com_veiculos  → tipo de veículo predominante por acidente
  4. ranking_locais          → ranking municipios/UFs por incidência
  5. analise_temporal        → distribuição por ano/mês/hora/dia da semana
  6. analise_correlacao      → correlação entre frota, população e acidentes
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def enrich_acidentes_localidade(
    df_acidentes: pd.DataFrame,
    df_localidade: pd.DataFrame,
) -> pd.DataFrame:
    """
    Enriquece acidentes com dados de município, região, habitantes e frota.
    Join pela chave chv_localidade.
    """
    logger.info("Cruzando acidentes x localidade...")

    # Selecionar apenas as colunas úteis da dimensão localidade
    loc_cols = [
        "chv_localidade", "municipio", "regiao", "codigo_ibge",
        "qtde_habitantes", "frota_total", "frota_circulante", "taxa_motorizacao",
    ]
    loc = df_localidade[loc_cols].copy()

    df = df_acidentes.merge(loc, on="chv_localidade", how="left")
    pct_enrich = df["municipio"].notna().mean() * 100
    logger.info("  → %.1f%% dos acidentes enriquecidos com localidade", pct_enrich)
    return df


def aggregate_vitimas_por_acidente(df_vitimas: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega vítimas por num_acidente, retornando contagens por gravidade.
    """
    logger.info("Agregando vítimas por acidente...")

    # Contagem por gravidade — usa observed=True para evitar combinação cartesiana em colunas category
    _vit = df_vitimas.copy()
    if hasattr(_vit["gravidade_lesao"], "cat"):
        _vit["gravidade_lesao"] = _vit["gravidade_lesao"].astype(str)
    gravidade_pivot = (
        _vit.groupby(["num_acidente", "gravidade_lesao"], observed=True)
        .size()
        .unstack(fill_value=0)
        .add_prefix("vitimas_")
        .reset_index()
    )
    gravidade_pivot.columns.name = None

    # Totais gerais
    totais = df_vitimas.groupby("num_acidente").agg(
        total_vitimas=("qtde_envolvidos", "sum"),
        total_obitos=("qtde_obitos", "sum"),
        total_feridos=("qtde_feridosilesos", "sum"),
        tipo_envolvidos=("tp_envolvido", lambda x: x.dropna().unique().tolist()),
    ).reset_index()

    df = totais.merge(gravidade_pivot, on="num_acidente", how="left")
    logger.info("  → %d acidentes com dados de vítimas agregados", len(df))
    return df


def aggregate_veiculos_por_acidente(df_tipo_veiculo: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega veículos por num_acidente: tipo predominante e contagem total.
    """
    logger.info("Agregando veículos por acidente...")

    df = df_tipo_veiculo.groupby("num_acidente").agg(
        total_veiculos=("qtde_veiculos", "sum"),
        tipos_veiculos=("tipo_veiculo", lambda x: x.dropna().unique().tolist()),
    ).reset_index()

    # Tipo de veículo mais comum no acidente
    modo = (
        df_tipo_veiculo[df_tipo_veiculo["tipo_veiculo"].notna()]
        .groupby("num_acidente")["tipo_veiculo"]
        .agg(lambda x: x.mode().iloc[0] if len(x) > 0 else pd.NA)
        .reset_index()
        .rename(columns={"tipo_veiculo": "veiculo_predominante"})
    )
    df = df.merge(modo, on="num_acidente", how="left")
    logger.info("  → %d acidentes com dados de veículos agregados", len(df))
    return df


def build_acidentes_gold(
    df_acidentes_enriquecidos: pd.DataFrame,
    df_vitimas_agg: pd.DataFrame,
    df_veiculos_agg: pd.DataFrame,
) -> pd.DataFrame:
    """
    Dataset Gold: acidentes + vítimas agregadas + veículos agregados.
    É o principal dataset analítico do pipeline.
    """
    logger.info("Construindo dataset Gold de acidentes...")

    df = df_acidentes_enriquecidos.merge(
        df_vitimas_agg, on="num_acidente", how="left"
    )
    df = df.merge(df_veiculos_agg, on="num_acidente", how="left")

    # Preencher nulos de contagem com 0
    count_cols = [c for c in df.columns if c.startswith(("total_", "vitimas_"))]
    for col in count_cols:
        df[col] = df[col].fillna(0)

    logger.info("  → dataset Gold: %d linhas, %d colunas", *df.shape)
    return df


def build_ranking_locais(df_gold: pd.DataFrame) -> pd.DataFrame:
    """
    Ranking de municípios e UFs por:
      - total de acidentes
      - total de óbitos
      - taxa de acidente por 100k habitantes
    """
    logger.info("Calculando ranking de locais com mais acidentes...")

    agg = df_gold.groupby(
        ["uf_acidente", "municipio", "codigo_ibge", "qtde_habitantes",
         "frota_circulante", "taxa_motorizacao"],
        observed=True,
    ).agg(
        total_acidentes=("qtde_acidente", "sum"),
        total_obitos=("qtde_obitos", "sum"),
        total_feridos=("qtde_feridosilesos", "sum"),
        total_envolvidos=("qtde_envolvidos", "sum"),
        acidentes_chuva=(
            "cond_meteorologica",
            lambda x: (x == "CHUVA").sum(),
        ),
        acidentes_noite=(
            "fase_dia",
            lambda x: x.isin(["NOITE", "MADRUGADA"]).sum(),
        ),
    ).reset_index()

    # Taxa de acidente por 100.000 habitantes
    mask = agg["qtde_habitantes"] > 0
    agg["taxa_acidente_100k"] = (
        (agg["total_acidentes"] / agg["qtde_habitantes"]) * 100_000
    ).where(mask).round(2)

    # Taxa de mortalidade por acidente
    mask_acid = agg["total_acidentes"] > 0
    agg["taxa_mortalidade"] = (
        (agg["total_obitos"] / agg["total_acidentes"]) * 100
    ).where(mask_acid).round(2)

    agg = agg.sort_values("total_acidentes", ascending=False).reset_index(drop=True)
    agg["ranking_geral"] = agg.index + 1

    logger.info("  → ranking com %d municípios", len(agg))
    return agg


def build_analise_temporal(df_gold: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Retorna dicionário de DataFrames com distribuições temporais:
      - por_ano
      - por_mes
      - por_hora
      - por_dia_semana
      - por_fase_dia
    """
    logger.info("Calculando análise temporal...")

    def _agg(group_col: str) -> pd.DataFrame:
        return (
            df_gold.groupby(group_col, observed=True)
            .agg(
                total_acidentes=("qtde_acidente", "sum"),
                total_obitos=("qtde_obitos", "sum"),
                total_feridos=("qtde_feridosilesos", "sum"),
            )
            .reset_index()
            .sort_values(group_col)
        )

    return {
        "por_ano": _agg("ano_acidente"),
        "por_mes": _agg("mes_acidente"),
        "por_hora": _agg("hora"),
        "por_dia_semana": _agg("dia_semana"),
        "por_fase_dia": _agg("fase_dia"),
    }


def build_correlacao_frota_acidentes(df_ranking: pd.DataFrame) -> pd.DataFrame:
    """
    Dataset para análise de correlação entre frota, população e acidentes
    por município.
    """
    logger.info("Preparando dataset de correlação frota x acidentes...")

    cols = [
        "uf_acidente", "municipio", "codigo_ibge",
        "qtde_habitantes", "frota_circulante", "taxa_motorizacao",
        "total_acidentes", "total_obitos", "taxa_acidente_100k",
        "taxa_mortalidade",
    ]
    df = df_ranking[cols].copy()

    # Quartil de motorização
    df["quartil_motorizacao"] = pd.qcut(
        df["taxa_motorizacao"].dropna(),
        q=4,
        labels=["Q1_baixo", "Q2", "Q3", "Q4_alto"],
        duplicates="drop",
    )

    logger.info("  → %d municípios no dataset de correlação", len(df))
    return df
