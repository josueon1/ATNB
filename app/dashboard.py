"""
Dashboard ATNB - Análise de Acidentes de Trânsito no Brasil
============================================================
Consome os datasets Parquet gerados pelo pipeline.
Execute o pipeline primeiro:
    python -m src.pipeline.pipeline --skip-heavy
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pyarrow.parquet as pq
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline.persist import load_parquet  # noqa: E402

PROCESSED_DIR = ROOT / "data" / "processed"
GEOJSON_PATH  = ROOT / "data" / "geojson" / "br_states.json"

st.set_page_config(
    page_title="ATNB — Acidentes de Trânsito no Brasil",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Verificação de dados processados ─────────────────────────────────────────
if not PROCESSED_DIR.exists() or not any(PROCESSED_DIR.iterdir()):
    st.error(
        "Dados processados não encontrados. Execute o pipeline primeiro:\n\n"
        "```\npython -m src.pipeline.pipeline --skip-heavy\n```"
    )
    st.stop()


# ── Funções de carregamento com cache ─────────────────────────────────────────
@st.cache_data(show_spinner="Carregando ranking...")
def load_ranking() -> pd.DataFrame:
    return load_parquet(PROCESSED_DIR / "ranking_locais.parquet")


@st.cache_data(show_spinner="Carregando dados temporais...")
def load_temporal(name: str) -> pd.DataFrame:
    return load_parquet(PROCESSED_DIR / "analise_temporal" / f"{name}.parquet")


@st.cache_data(show_spinner="Carregando correlação...")
def load_correlacao() -> pd.DataFrame:
    return load_parquet(PROCESSED_DIR / "correlacao_frota_acidentes.parquet")


@st.cache_data(show_spinner="Carregando acidentes por UF...")
def load_gold_uf(ufs: tuple) -> pd.DataFrame:
    filters = [("uf_acidente", "in", list(ufs))] if ufs else None
    return load_parquet(PROCESSED_DIR / "acidentes_gold", filters=filters)


@st.cache_data(show_spinner="Carregando vítimas por UF...")
def load_vitimas_uf(ufs: tuple) -> pd.DataFrame:
    filters = [("uf_acidente", "in", list(ufs))] if ufs else None
    return load_parquet(PROCESSED_DIR / "vitimas_silver", filters=filters)


@st.cache_data(show_spinner="Carregando dados do ano...")
def load_gold_year_month(year: int, month: int | None, ufs: tuple) -> pd.DataFrame:
    filters: list = [("ano_acidente", "=", year)]
    if ufs:
        filters.append(("uf_acidente", "in", list(ufs)))
    df = load_parquet(PROCESSED_DIR / "acidentes_gold", filters=filters)
    if month is not None:
        df = df[df["mes_acidente"].astype(int) == month]
    return df


@st.cache_data(show_spinner="Calculando análise temporal filtrada...")
def load_temporal_filtrado(ano: int | None, ufs: tuple) -> dict[str, pd.DataFrame]:
    """Agrega acidentes_gold filtrado para uso nas análises temporais."""
    filters: list = []
    if ano is not None:
        filters.append(("ano_acidente", "=", ano))
    if ufs:
        filters.append(("uf_acidente", "in", list(ufs)))
    df = load_parquet(PROCESSED_DIR / "acidentes_gold", filters=filters or None)

    def _agg(col: str) -> pd.DataFrame:
        return (
            df.groupby(col, observed=True)
            .agg(
                total_acidentes=("qtde_acidente", "sum"),
                total_obitos=("qtde_obitos", "sum"),
                total_feridos=("qtde_feridosilesos", "sum"),
            )
            .reset_index()
            .sort_values(col)
        )

    return {
        "por_mes": _agg("mes_acidente"),
        "por_hora": _agg("hora"),
        "por_dia_semana": _agg("dia_semana"),
    }


@st.cache_data(show_spinner="Carregando fatores temporais...")
def load_fatores_temporais(ano: int | None, ufs: tuple, agrupar_por: str = "mes") -> pd.DataFrame:
    filters = []
    if ano is not None and agrupar_por == "mes":
        filters.append(("ano_acidente", "=", int(ano)))
    if ufs:
        filters.append(("uf_acidente", "in", list(ufs)))

    table = pq.read_table(
        str(PROCESSED_DIR / "acidentes_gold"),
        columns=["ano_acidente", "mes_acidente", "qtde_acidente", "qtde_obitos", "cond_pista", "cond_meteorologica"],
        filters=filters or None,
    )
    df = table.to_pandas()

    vt_filters = []
    if ano is not None and agrupar_por == "mes":
        vt_filters.append(("ano_acidente", "=", int(ano)))
    if ufs:
        vt_filters.append(("uf_acidente", "in", list(ufs)))

    vt_table = pq.read_table(
        str(PROCESSED_DIR / "vitimas_silver"),
        columns=["ano_acidente", "mes_acidente", "num_acidente", "susp_alcool", "qtde_obitos"],
        filters=vt_filters or None,
    )
    vt_df = vt_table.to_pandas()

    group_col = "mes_acidente" if agrupar_por == "mes" else "ano_acidente"

    emb = (
        vt_df.query("susp_alcool == 'SIM'")
        .groupby(group_col, observed=True)
        .agg(
            acidentes_embriaguez=("num_acidente", "nunique"),
            obitos_embriaguez=("qtde_obitos", "sum")
        )
        .reset_index()
    )

    conds = {
        "pista_molhada": df["cond_pista"].isin(_PISTA_MOLHADA),
        "buraco": df["cond_pista"] == "COM BURACO",
        "chuva": df["cond_meteorologica"] == "CHUVA",
        "meteo_adversa": df["cond_meteorologica"].isin(_COND_METEO_ADVERSA),
    }

    group_vals = sorted(df[group_col].dropna().unique())
    res = []
    for val in group_vals:
        row = {group_col: val}
        for name, mask in conds.items():
            sub_acidentes = df.loc[mask & (df[group_col] == val), "qtde_acidente"].sum()
            sub_obitos = df.loc[mask & (df[group_col] == val), "qtde_obitos"].sum()
            row[f"acidentes_{name}"] = int(sub_acidentes)
            row[f"obitos_{name}"] = int(sub_obitos)
        res.append(row)

    df_agg = pd.DataFrame(res)
    if not df_agg.empty:
        df_agg = df_agg.merge(emb, on=group_col, how="left")
        df_agg = df_agg.fillna(0)
        for col in df_agg.columns:
            if col != group_col:
                df_agg[col] = df_agg[col].astype(int)
    return df_agg


_COND_METEO_ADVERSA = [
    "CHUVA", "NUBLADO", "GAROACHUVISCO",
    "NEVOEIRO  NEVOA OU FUMACA", "VENTOS FORTES", "NEVE", "GRANIZO",
]
_PISTA_MOLHADA = ["MOLHADA", "ESCORREGADIA"]


def _date_filter(ano: int | None, mes: int | None) -> list | None:
    filters = []
    if ano is not None:
        filters.append(("ano_acidente", "=", int(ano)))
    if mes is not None:
        filters.append(("mes_acidente", "=", int(mes)))
    return filters or None


def _enriquecer_com_causas(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Agrega métricas e fatores de risco por UF ou município."""
    agg = (
        df.groupby(group_cols, as_index=False, observed=True)
        .agg(
            total_acidentes=("qtde_acidente", "sum"),
            total_obitos=("qtde_obitos", "sum"),
            total_feridos=("qtde_feridosilesos", "sum"),
        )
    )
    mask = agg["total_acidentes"] > 0
    agg["taxa_letalidade"] = (
        (agg["total_obitos"] / agg["total_acidentes"].replace(0, pd.NA)) * 100
    ).where(mask).round(2)

    fatores = {
        "acidentes_pista_molhada": df["cond_pista"].isin(_PISTA_MOLHADA),
        "acidentes_buraco": df["cond_pista"] == "COM BURACO",
        "acidentes_chuva": df["cond_meteorologica"] == "CHUVA",
        "acidentes_meteo_adversa": df["cond_meteorologica"].isin(_COND_METEO_ADVERSA),
    }
    for nome, mascara in fatores.items():
        contagem = (
            df.loc[mascara]
            .groupby(group_cols, observed=True)["qtde_acidente"]
            .sum()
            .rename(nome)
        )
        agg = agg.merge(contagem, on=group_cols, how="left")

        nome_obitos = nome.replace("acidentes_", "obitos_")
        contagem_obitos = (
            df.loc[mascara]
            .groupby(group_cols, observed=True)["qtde_obitos"]
            .sum()
            .rename(nome_obitos)
        )
        agg = agg.merge(contagem_obitos, on=group_cols, how="left")

    tipo_rank = (
        df.groupby(group_cols + ["tp_acidente"], observed=True)["qtde_acidente"]
        .sum()
        .reset_index()
        .sort_values(group_cols + ["qtde_acidente"], ascending=[True] * len(group_cols) + [False])
    )
    principal = tipo_rank.drop_duplicates(group_cols)[group_cols + ["tp_acidente"]]
    principal = principal.rename(columns={"tp_acidente": "causa_principal"})
    agg = agg.merge(principal, on=group_cols, how="left")

    for col in fatores:
        agg[col] = agg[col].fillna(0).astype(int)
        nome_obitos = col.replace("acidentes_", "obitos_")
        agg[nome_obitos] = agg[nome_obitos].fillna(0).astype(int)

    agg["causa_principal"] = agg["causa_principal"].fillna("N/D").astype(str)
    return agg


@st.cache_data(show_spinner="Carregando dados por estado...")
def load_estados_com_causas(ano: int | None, mes: int | None = None) -> pd.DataFrame:
    """Agrega acidentes e fatores de risco por UF para o mapa."""
    table = pq.read_table(
        str(PROCESSED_DIR / "acidentes_gold"),
        columns=[
            "num_acidente", "uf_acidente", "qtde_acidente", "qtde_obitos", "qtde_feridosilesos",
            "tp_acidente", "cond_pista", "cond_meteorologica",
        ],
        filters=_date_filter(ano, mes),
    )
    ac_df = table.to_pandas()
    agg = _enriquecer_com_causas(ac_df, ["uf_acidente"])

    vt = pq.read_table(
        str(PROCESSED_DIR / "vitimas_silver"),
        columns=["uf_acidente", "num_acidente", "susp_alcool", "genero", "qtde_obitos"],
        filters=_date_filter(ano, mes),
    )
    vt_df = vt.to_pandas()
    emb = (
        vt_df
        .query("susp_alcool == 'SIM'")
        .groupby("uf_acidente", observed=True)
        .agg(
            acidentes_embriaguez=("num_acidente", "nunique"),
            obitos_embriaguez=("qtde_obitos", "sum")
        )
    )
    agg = agg.merge(emb, on="uf_acidente", how="left")
    agg["acidentes_embriaguez"] = agg["acidentes_embriaguez"].fillna(0).astype(int)
    agg["obitos_embriaguez"] = agg["obitos_embriaguez"].fillna(0).astype(int)

    # Merge victims with accident conditions for gender breakdown
    merged = vt_df.merge(
        ac_df[["num_acidente", "cond_pista", "cond_meteorologica"]],
        on="num_acidente",
        how="inner"
    )

    merged["is_pista_molhada"] = merged["cond_pista"].isin(_PISTA_MOLHADA)
    merged["is_buraco"] = merged["cond_pista"] == "COM BURACO"
    merged["is_chuva"] = merged["cond_meteorologica"] == "CHUVA"
    merged["is_meteo_adversa"] = merged["cond_meteorologica"].isin(_COND_METEO_ADVERSA)
    merged["is_embriaguez"] = merged["susp_alcool"] == "SIM"

    m_mask = merged["genero"] == "MASCULINO"
    f_mask = merged["genero"] == "FEMININO"

    factors = ["embriaguez", "pista_molhada", "chuva", "buraco", "meteo_adversa"]
    for f in factors:
        mask = merged[f"is_{f}"]
        
        env_m = merged[mask & m_mask].groupby("uf_acidente", observed=True).size().rename(f"env_masc_{f}")
        env_f = merged[mask & f_mask].groupby("uf_acidente", observed=True).size().rename(f"env_fem_{f}")
        
        obt_m = merged[mask & m_mask].groupby("uf_acidente", observed=True)["qtde_obitos"].sum().rename(f"obt_masc_{f}")
        obt_f = merged[mask & f_mask].groupby("uf_acidente", observed=True)["qtde_obitos"].sum().rename(f"obt_fem_{f}")
        
        agg = agg.merge(env_m, on="uf_acidente", how="left")
        agg = agg.merge(env_f, on="uf_acidente", how="left")
        agg = agg.merge(obt_m, on="uf_acidente", how="left")
        agg = agg.merge(obt_f, on="uf_acidente", how="left")
        
        agg[f"env_masc_{f}"] = agg[f"env_masc_{f}"].fillna(0).astype(int)
        agg[f"env_fem_{f}"] = agg[f"env_fem_{f}"].fillna(0).astype(int)
        agg[f"obt_masc_{f}"] = agg[f"obt_masc_{f}"].fillna(0).astype(int)
        agg[f"obt_fem_{f}"] = agg[f"obt_fem_{f}"].fillna(0).astype(int)

    return agg


@st.cache_data(show_spinner="Carregando dados municipais...")
def load_municipios_com_causas(ano: int | None, ufs: tuple, mes: int | None = None) -> pd.DataFrame:
    """Agrega acidentes e fatores de risco por município (scatter_mapbox)."""
    filters: list = []
    if ano is not None:
        filters.append(("ano_acidente", "=", int(ano)))
    if mes is not None:
        filters.append(("mes_acidente", "=", int(mes)))
    if ufs:
        filters.append(("uf_acidente", "in", list(ufs)))
    table = pq.read_table(
        str(PROCESSED_DIR / "acidentes_gold"),
        columns=[
            "municipio", "uf_acidente", "num_acidente", "qtde_acidente",
            "qtde_obitos", "qtde_feridosilesos", "tp_acidente", "cond_pista",
            "cond_meteorologica", "latitude_acidente", "longitude_acidente",
        ],
        filters=filters or None,
    )
    df = table.to_pandas()
    df = df[
        df["latitude_acidente"].notna() & (df["latitude_acidente"] != 0) &
        df["longitude_acidente"].notna() & (df["longitude_acidente"] != 0)
    ]
    coords = (
        df.groupby(["municipio", "uf_acidente"], as_index=False, observed=True)
        .agg(lat=("latitude_acidente", "mean"), lon=("longitude_acidente", "mean"))
    )
    agg = _enriquecer_com_causas(df, ["municipio", "uf_acidente"])
    return agg.merge(coords, on=["municipio", "uf_acidente"], how="left").dropna(subset=["lat", "lon"])


@st.cache_data(show_spinner="Carregando fatores por município...")
def load_municipios_fatores(ano: int | None, ufs: tuple, mes: int | None = None) -> pd.DataFrame:
    """Calcula estatísticas de fatores de risco (incluindo sazonalidade) por município."""
    filters = _date_filter(ano, mes)
    if ufs:
        filters = (filters or []) + [("uf_acidente", "in", list(ufs))]
    
    ac_table = pq.read_table(
        str(PROCESSED_DIR / "acidentes_gold"),
        columns=[
            "num_acidente", "municipio", "uf_acidente", "regiao", 
            "mes_acidente", "qtde_acidente", "cond_pista", "cond_meteorologica"
        ],
        filters=filters or None
    )
    df_ac = ac_table.to_pandas()
    
    # Carrega embriaguez das vítimas
    vt_table = pq.read_table(
        str(PROCESSED_DIR / "vitimas_silver"),
        columns=["num_acidente", "susp_alcool"],
        filters=filters or None
    )
    df_vt = vt_table.to_pandas()
    
    acidentes_alcool = set(df_vt.loc[df_vt["susp_alcool"] == "SIM", "num_acidente"])
    df_ac["is_alcool"] = df_ac["num_acidente"].isin(acidentes_alcool).astype(int)
    
    # Codifica fatores
    df_ac["is_pista_molhada"] = df_ac["cond_pista"].isin(_PISTA_MOLHADA).astype(int)
    df_ac["is_buraco"] = (df_ac["cond_pista"] == "COM BURACO").astype(int)
    df_ac["is_chuva"] = (df_ac["cond_meteorologica"] == "CHUVA").astype(int)
    
    # Fator Sazonal de Pico por Região
    picos_regionais = {
        "NORTE": 3,
        "NORDESTE": 1,
        "CENTRO-OESTE": 5,
        "SUDESTE": 10,
        "SUL": 10
    }
    df_ac["reg_upper"] = df_ac["regiao"].astype(str).str.upper()
    df_ac["mes_pico"] = df_ac["reg_upper"].map(picos_regionais)
    df_ac["is_sazonal"] = (df_ac["mes_acidente"].astype(int) == df_ac["mes_pico"]).astype(int)
    
    agg = (
        df_ac.groupby(["municipio", "uf_acidente"], as_index=False, observed=True)
        .agg(
            total_acidentes=("qtde_acidente", "sum"),
            acidentes_embriaguez=("is_alcool", "sum"),
            acidentes_pista_molhada=("is_pista_molhada", "sum"),
            acidentes_chuva=("is_chuva", "sum"),
            acidentes_buraco=("is_buraco", "sum"),
            acidentes_sazonal=("is_sazonal", "sum")
        )
    )
    
    def _predominante(row):
        fatores = {
            "🍷 Álcool": row["acidentes_embriaguez"],
            "🌧️ Pista Molhada": row["acidentes_pista_molhada"],
            "🌦️ Chuva / Tempo Adverso": row["acidentes_chuva"],
            "🕳️ Buracos": row["acidentes_buraco"],
            "📅 Sazonalidade / Pico": row["acidentes_sazonal"]
        }
        if max(fatores.values()) == 0:
            return "Sem Fatores Específicos"
        return max(fatores, key=fatores.get)
        
    agg["Fator Predominante"] = agg.apply(_predominante, axis=1)
    return agg


@st.cache_data(show_spinner="Carregando dados de explosão...")
def load_sunburst_sazonal_data(ano: int | None, ufs: tuple, mes: int | None = None) -> pd.DataFrame:
    """Carrega dados estruturados para o gráfico de explosão (Sunburst) sazonal e geográfico."""
    filters = _date_filter(ano, mes)
    if ufs:
        filters = (filters or []) + [("uf_acidente", "in", list(ufs))]
    
    ac_table = pq.read_table(
        str(PROCESSED_DIR / "acidentes_gold"),
        columns=[
            "num_acidente", "municipio", "uf_acidente", "regiao", 
            "mes_acidente", "qtde_acidente", "cond_pista", "cond_meteorologica"
        ],
        filters=filters or None
    )
    df_ac = ac_table.to_pandas()
    
    # Carrega dados de embriaguez
    vt_table = pq.read_table(
        str(PROCESSED_DIR / "vitimas_silver"),
        columns=["num_acidente", "susp_alcool"],
        filters=filters or None
    )
    df_vt = vt_table.to_pandas()
    
    acidentes_alcool = set(df_vt.loc[df_vt["susp_alcool"] == "SIM", "num_acidente"])
    df_ac["is_alcool"] = df_ac["num_acidente"].isin(acidentes_alcool)
    
    # Classificação exclusiva dos fatores causais
    conds = [
        df_ac["is_alcool"],
        df_ac["cond_pista"].isin(_PISTA_MOLHADA),
        df_ac["cond_meteorologica"] == "CHUVA",
        df_ac["cond_pista"] == "COM BURACO"
    ]
    choices = [
        "🍷 Álcool",
        "🌧️ Pista Molhada",
        "🌦️ Chuva",
        "🕳️ Buracos"
    ]
    df_ac["fator"] = np.select(conds, choices, default="Outros / Sem Fator")
    
    # Mapeia meses
    meses_abreviados = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
    }
    df_ac["mes_nome"] = df_ac["mes_acidente"].map(meses_abreviados)
    
    return (
        df_ac.groupby(["regiao", "mes_nome", "fator", "municipio", "uf_acidente"], observed=True)["qtde_acidente"]
        .sum()
        .reset_index()
    )


@st.cache_data(show_spinner=False)
def load_geojson() -> dict:
    with open(str(GEOJSON_PATH), encoding="utf-8") as f:
        return json.load(f)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Filtros")

    ranking = load_ranking()
    anos_disponiveis = sorted(
        load_temporal("por_ano")["ano_acidente"].dropna().astype(int).unique()
    )
    ano_sel = st.selectbox(
        "Ano de referência",
        options=["Todos"] + anos_disponiveis,
        index=0,
    )
    _MESES_NOME = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
    }
    _mes_raw = st.selectbox(
        "Mês de referência",
        options=["Todos"] + list(_MESES_NOME.keys()),
        format_func=lambda m: "Todos" if m == "Todos" else f"{m:02d} — {_MESES_NOME[m]}",
        index=0,
    )
    mes_sel = None if _mes_raw == "Todos" else int(_mes_raw)
    ufs_disponiveis = sorted(ranking["uf_acidente"].dropna().unique())
    uf_sel = st.multiselect(
        "UF(s)",
        options=ufs_disponiveis,
        default=[],
        placeholder="Todas as UFs",
    )
    top_n = st.slider("Top N municípios", min_value=5, max_value=30, value=10)


# ── Preparação do ranking agregado por município ──────────────────────────────
if ano_sel == "Todos":
    df_ranking_raw = ranking.copy()
    if uf_sel:
        df_ranking_raw = df_ranking_raw[df_ranking_raw["uf_acidente"].isin(uf_sel)]
    df_ranking = (
        df_ranking_raw.groupby(["municipio", "uf_acidente"], as_index=False, observed=True)
        .agg(
            total_acidentes=("total_acidentes", "sum"),
            total_obitos=("total_obitos", "sum"),
            total_feridos=("total_feridos", "sum"),
            taxa_acidente_100k=("taxa_acidente_100k", "mean"),
            taxa_letalidade=("taxa_letalidade", "mean"),
            taxa_mortalidade_100k=("taxa_mortalidade_100k", "mean"),
            ups=("ups", "sum"),
            acidentes_chuva=("acidentes_chuva", "sum"),
            acidentes_noite=("acidentes_noite", "sum"),
        )
        .sort_values("total_acidentes", ascending=False)
        .reset_index(drop=True)
    )
else:
    _gdf_yr = load_gold_year_month(
        int(ano_sel), mes_sel, tuple(sorted(uf_sel)) if uf_sel else ()
    )
    _agg_yr = (
        _gdf_yr.groupby(["uf_acidente", "municipio"], as_index=False, observed=True)
        .agg(
            total_acidentes=("qtde_acidente", "sum"),
            total_obitos=("qtde_obitos", "sum"),
            total_feridos=("qtde_feridosilesos", "sum"),
            _qtde_hab=("qtde_habitantes", "first"),
            acidentes_chuva=("cond_meteorologica", lambda x: (x.astype(str) == "CHUVA").sum()),
            acidentes_noite=("fase_dia", lambda x: x.astype(str).isin(["NOITE", "MADRUGADA"]).sum()),
        )
        .sort_values("total_acidentes", ascending=False)
        .reset_index(drop=True)
    )
    _mask_hab = _agg_yr["_qtde_hab"] > 0
    _agg_yr["taxa_acidente_100k"] = (
        (_agg_yr["total_acidentes"] / _agg_yr["_qtde_hab"]) * 100_000
    ).where(_mask_hab).round(2)
    _agg_yr["taxa_mortalidade_100k"] = (
        (_agg_yr["total_obitos"] / _agg_yr["_qtde_hab"]) * 100_000
    ).where(_mask_hab).round(2)
    _mask_acid = _agg_yr["total_acidentes"] > 0
    _agg_yr["taxa_letalidade"] = (
        (_agg_yr["total_obitos"] / _agg_yr["total_acidentes"]) * 100
    ).where(_mask_acid).round(2)
    _agg_yr["ups"] = (_agg_yr["total_obitos"] * 13) + (_agg_yr["total_feridos"] * 5)
    df_ranking = _agg_yr.drop(columns=["_qtde_hab"])

df_ranking.insert(0, "ranking_geral", df_ranking.index + 1)
df_ranking_top = df_ranking.head(top_n)


# ── Título e KPIs ─────────────────────────────────────────────────────────────
st.title("Análise de Acidentes de Trânsito no Brasil")
st.caption("Fonte: RENAEST / SENATRAN | Pipeline: ATNB")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total de Acidentes", f"{df_ranking['total_acidentes'].sum():,.0f}")
k2.metric("Total de Óbitos", f"{df_ranking['total_obitos'].sum():,.0f}")
k3.metric("Letalidade Média", f"{df_ranking['taxa_letalidade'].mean():.1f}%")
k4.metric("UPS Total", f"{df_ranking['ups'].sum():,.0f}")
k5.metric("Municípios Analisados", f"{df_ranking['municipio'].nunique():,}")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# TABS PRINCIPAIS
# ═══════════════════════════════════════════════════════════════════════════════
tab_geral, tab_temporal, tab_corr, tab_fatores, tab_ts = st.tabs([
    "🗺️ Visão Geral",
    "📈 Evolução Temporal",
    "🔗 Correlação & Indicadores",
    "⚠️ Fatores & Causas",
    "📊 Previsão e Tendência",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — VISÃO GERAL
# ══════════════════════════════════════════════════════════════════════════════
with tab_geral:

    # ── Mapa Geográfico ───────────────────────────────────────────────────────
    _ano_mapa = None if ano_sel == "Todos" else int(ano_sel)
    _ufs_mapa = tuple(sorted(uf_sel)) if uf_sel else ()

    _metrica_mapa = st.radio(
        "Métrica exibida no mapa",
        options=["Total de Acidentes", "Total de Óbitos", "Taxa de Letalidade (%)"],
        horizontal=True,
        key="radio_mapa",
    )
    _col_mapa = {
        "Total de Acidentes": "total_acidentes",
        "Total de Óbitos": "total_obitos",
        "Taxa de Letalidade (%)": "taxa_letalidade",
    }[_metrica_mapa]

    df_estados = load_estados_com_causas(_ano_mapa, mes_sel)

    _labels_mapa = {
        "total_acidentes": "Acidentes",
        "total_obitos": "Óbitos",
        "taxa_letalidade": "Letalidade (%)",
        "uf_acidente": "UF",
        "municipio": "Município",
        "causa_principal": "Tipo mais frequente",
        "acidentes_embriaguez": "Embriaguez",
        "acidentes_pista_molhada": "Pista molhada",
        "acidentes_chuva": "Chuva",
        "acidentes_buraco": "Buracos",
    }

    # ── Mapa estadual — sempre visível (visão nacional) ───────────────────────
    st.subheader("Visão Nacional por Estado")
    st.caption("Passe o mouse sobre um estado para ver as principais causas dos acidentes na região.")
    if GEOJSON_PATH.exists():
        _geojson = load_geojson()
        df_estados["_selecionado"] = df_estados["uf_acidente"].isin(uf_sel) if uf_sel else False
        fig_mapa = px.choropleth(
            df_estados,
            geojson=_geojson,
            locations="uf_acidente",
            featureidkey="properties.SIGLA",
            color=_col_mapa,
            color_continuous_scale="YlOrRd",
            hover_name="uf_acidente",
            custom_data=[
                "total_acidentes", "total_obitos", "taxa_letalidade",
                "causa_principal", "acidentes_embriaguez", "acidentes_pista_molhada",
                "acidentes_chuva", "acidentes_buraco",
            ],
            labels=_labels_mapa,
            fitbounds="locations",
            basemap_visible=False,
            height=480,
        )
        fig_mapa.update_traces(
            hovertemplate=(
                "<b>%{location}</b><br>"
                f"{_metrica_mapa}: %{{z:,.2f}}<br>"
                "Acidentes: %{customdata[0]:,.0f}<br>"
                "Óbitos: %{customdata[1]:,.0f}<br>"
                "Letalidade: %{customdata[2]:.1f}%<br>"
                "<br><b>Principais causas</b><br>"
                "Tipo mais frequente: %{customdata[3]}<br>"
                "Embriaguez: %{customdata[4]:,.0f}<br>"
                "Pista molhada: %{customdata[5]:,.0f}<br>"
                "Chuva: %{customdata[6]:,.0f}<br>"
                "Buracos na pista: %{customdata[7]:,.0f}"
                "<extra></extra>"
            ),
        )
        # Borda destacada nas UFs selecionadas
        if uf_sel:
            _sel_df = df_estados[df_estados["uf_acidente"].isin(uf_sel)]
            fig_mapa.add_trace(go.Choropleth(
                geojson=_geojson,
                locations=_sel_df["uf_acidente"],
                z=[1] * len(_sel_df),
                featureidkey="properties.SIGLA",
                colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                marker=dict(line=dict(color="#3b82f6", width=3)),
                showscale=False,
                hoverinfo="skip",
            ))
        fig_mapa.update_geos(
            showcoastlines=False,
            showland=True, landcolor="#1e293b",
            showocean=True, oceancolor="#0f172a",
            showframe=False,
            bgcolor="rgba(0,0,0,0)",
            projection_type="mercator",
            lataxis_range=[-35, 6],
            lonaxis_range=[-74, -28],
        )
        fig_mapa.update_layout(
            margin=dict(l=0, r=0, t=10, b=10),
            coloraxis_colorbar=dict(title=_metrica_mapa, thickness=14, len=0.7),
            geo=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_mapa, width='stretch')

        if uf_sel:
            df_filtrado = df_estados[df_estados["uf_acidente"].isin(uf_sel)]
            regiao_desc = ", ".join(sorted(uf_sel))
        else:
            df_filtrado = df_estados
            regiao_desc = "Brasil"

        st.markdown(f"#### Fatores e causas em destaque — {regiao_desc}")

        factors_data = {}
        for f in ["embriaguez", "pista_molhada", "chuva", "buraco", "meteo_adversa"]:
            acidentes = int(df_filtrado[f"acidentes_{f}"].sum())
            obitos = int(df_filtrado[f"obitos_{f}"].sum())

            # Gender breakdown
            env_masc = int(df_filtrado[f"env_masc_{f}"].sum())
            env_fem = int(df_filtrado[f"env_fem_{f}"].sum())
            obt_masc = int(df_filtrado[f"obt_masc_{f}"].sum())
            obt_fem = int(df_filtrado[f"obt_fem_{f}"].sum())

            if _col_mapa == "total_acidentes":
                val_str = f"{acidentes:,.0f}"
                breakdown_str = f"♂ {env_masc:,.0f} | ♀ {env_fem:,.0f}"
            elif _col_mapa == "total_obitos":
                val_str = f"{obitos:,.0f}"
                breakdown_str = f"♂ {obt_masc:,.0f} | ♀ {obt_fem:,.0f}"
            else:  # taxa_letalidade
                let = (obitos / acidentes * 100) if acidentes > 0 else 0
                val_str = f"{let:.2f}%"
                breakdown_str = f"♂ {obt_masc:,.0f} | ♀ {obt_fem:,.0f} (óbitos)"

            factors_data[f] = {
                "val": val_str,
                "breakdown": breakdown_str
            }

        cc1, cc2, cc3, cc4, cc5 = st.columns(5)
        with cc1:
            st.metric("Embriaguez", factors_data["embriaguez"]["val"])
            st.caption(factors_data["embriaguez"]["breakdown"])
        with cc2:
            st.metric("Pista molhada", factors_data["pista_molhada"]["val"])
            st.caption(factors_data["pista_molhada"]["breakdown"])
        with cc3:
            st.metric("Chuva", factors_data["chuva"]["val"])
            st.caption(factors_data["chuva"]["breakdown"])
        with cc4:
            st.metric("Buracos", factors_data["buraco"]["val"])
            st.caption(factors_data["buraco"]["breakdown"])
        with cc5:
            st.metric("Meteo. adversa", factors_data["meteo_adversa"]["val"])
            st.caption(factors_data["meteo_adversa"]["breakdown"])
    else:
        st.warning("GeoJSON não encontrado em data/geojson/br_states.json.")

    # ── Drilldown municipal — só aparece quando UF(s) selecionada(s) ──────────
    if uf_sel:
        st.divider()
        st.subheader(f"Detalhe por Município — {', '.join(sorted(uf_sel))}")
        df_munic = load_municipios_com_causas(_ano_mapa, _ufs_mapa, mes_sel)
        if df_munic.empty:
            st.info("Sem dados municipais com coordenadas para os filtros selecionados.")
        else:
            _center_lat = float(df_munic["lat"].mean())
            _center_lon = float(df_munic["lon"].mean())
            _zoom = 5 if len(uf_sel) == 1 else (4 if len(uf_sel) <= 3 else 3)
            fig_munic = px.scatter_mapbox(
                df_munic.sort_values(_col_mapa, ascending=False),
                lat="lat",
                lon="lon",
                size=_col_mapa,
                color=_col_mapa,
                color_continuous_scale="YlOrRd",
                hover_name="municipio",
                hover_data={
                    "uf_acidente": True,
                    "total_acidentes": ":,.0f",
                    "total_obitos": ":,.0f",
                    "taxa_letalidade": ":.2f",
                    "causa_principal": True,
                    "acidentes_pista_molhada": ":,.0f",
                    "acidentes_chuva": ":,.0f",
                    "acidentes_buraco": ":,.0f",
                    "lat": False,
                    "lon": False,
                },
                mapbox_style="open-street-map",
                center={"lat": _center_lat, "lon": _center_lon},
                zoom=_zoom,
                size_max=40,
                height=520,
                labels=_labels_mapa,
            )
            fig_munic.update_layout(
                margin=dict(l=0, r=0, t=10, b=10),
                coloraxis_colorbar=dict(title=_metrica_mapa, thickness=14, len=0.7),
            )
            st.plotly_chart(fig_munic, width='stretch')

    st.divider()

    # ── Ranking de Municípios ─────────────────────────────────────────────────
    st.subheader(f"Top {top_n} Municípios com Mais Acidentes")
    col_left, col_right = st.columns([1.3, 0.7])

    with col_left:
        fig_rank = px.bar(
            df_ranking_top.sort_values("total_acidentes"),
            x="total_acidentes",
            y="municipio",
            color="uf_acidente",
            orientation="h",
            text="total_acidentes",
            labels={
                "total_acidentes": "Total de Acidentes",
                "municipio": "Município",
                "uf_acidente": "UF",
            },
            height=420,
        )
        fig_rank.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_rank.update_layout(margin=dict(l=0, r=20, t=20, b=0), showlegend=True)
        st.plotly_chart(fig_rank, width='stretch')

    with col_right:
        st.markdown("**Ranking por Taxa por 100k hab.**")
        _df_taxa = df_ranking_top[["municipio", "uf_acidente", "taxa_acidente_100k", "taxa_letalidade"]].rename(columns={
            "municipio": "Município", "uf_acidente": "UF",
            "taxa_acidente_100k": "Taxa/100k", "taxa_letalidade": "Letalidade (%)",
        })
        st.dataframe(_df_taxa, hide_index=True, width='stretch', height=400)

    st.divider()

    # ── Tabela completa do ranking ────────────────────────────────────────────
    with st.expander("Tabela completa do ranking de municípios"):
        display_cols = [
            "ranking_geral", "municipio", "uf_acidente", "total_acidentes",
            "total_obitos", "total_feridos", "taxa_acidente_100k", "taxa_letalidade",
            "acidentes_chuva", "acidentes_noite",
        ]
        st.dataframe(
            df_ranking[display_cols].rename(columns={
                "ranking_geral": "Rank",
                "municipio": "Município",
                "uf_acidente": "UF",
                "total_acidentes": "Acidentes",
                "total_obitos": "Óbitos",
                "total_feridos": "Feridos",
                "taxa_acidente_100k": "Taxa/100k hab.",
                "taxa_letalidade": "Letalidade (%)",
                "acidentes_chuva": "Em chuva",
                "acidentes_noite": "À noite",
            }),
            width='stretch',
            height=400,
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — EVOLUÇÃO TEMPORAL
# ══════════════════════════════════════════════════════════════════════════════
with tab_temporal:

    # Decide a fonte de dados: filtrada (dinâmica) ou pré-agregada (global)
    _any_filter = ano_sel != "Todos" or bool(uf_sel)
    if _any_filter:
        _t = load_temporal_filtrado(
            None if ano_sel == "Todos" else int(ano_sel),
            tuple(sorted(uf_sel)) if uf_sel else (),
        )
        _filtro_desc = []
        if ano_sel != "Todos":
            _filtro_desc.append(f"Ano: {ano_sel}")
            if mes_sel:
                _filtro_desc.append(f"Mês: {_MESES_NOME[mes_sel]}")
        if uf_sel:
            _filtro_desc.append(f"UF: {', '.join(sorted(uf_sel))}")
        st.info(f"Dados filtrados por — {' | '.join(_filtro_desc)}")
    else:
        _t = None
        st.caption("Exibindo dados históricos completos (todos os anos e UFs).")

    # ── Evolução Anual — sempre exibe todos os anos (tendência histórica) ─────
    st.subheader("Evolução Anual de Acidentes e Óbitos")
    por_ano = load_temporal("por_ano")

    fig_ano = go.Figure()
    fig_ano.add_trace(go.Bar(
        x=por_ano["ano_acidente"].astype(int),
        y=por_ano["total_acidentes"],
        name="Acidentes",
        marker_color="#3b82f6",
        opacity=0.8,
    ))
    # Destaca o ano selecionado
    if ano_sel != "Todos":
        _ano_int = int(ano_sel)
        _row = por_ano[por_ano["ano_acidente"].astype(int) == _ano_int]
        if not _row.empty:
            fig_ano.add_trace(go.Bar(
                x=[_ano_int],
                y=[_row["total_acidentes"].iloc[0]],
                name=f"Ano selecionado ({_ano_int})",
                marker_color="#f59e0b",
            ))
    fig_ano.add_trace(go.Scatter(
        x=por_ano["ano_acidente"].astype(int),
        y=por_ano["total_obitos"],
        name="Óbitos",
        mode="lines+markers",
        marker_color="#ef4444",
        yaxis="y2",
    ))
    fig_ano.update_layout(
        yaxis=dict(title="Total de Acidentes"),
        yaxis2=dict(title="Total de Óbitos", overlaying="y", side="right"),
        legend=dict(orientation="h"),
        height=320,
        margin=dict(t=10, b=10),
    )
    st.plotly_chart(fig_ano, width='stretch')

    st.divider()

    # ── Acidentes por Mês ─────────────────────────────────────────────────────
    st.subheader("Acidentes por Mês")
    por_mes = (_t["por_mes"] if _any_filter else load_temporal("por_mes"))
    por_mes = por_mes.sort_values("mes_acidente")
    por_mes["mes_nome"] = por_mes["mes_acidente"].map({
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
    })

    fig_mes = go.Figure()
    fig_mes.add_trace(go.Bar(
        x=por_mes["mes_nome"],
        y=por_mes["total_acidentes"],
        name="Acidentes",
        marker_color="#969292",
        text=por_mes["total_acidentes"],
        texttemplate="%{text:,.0f}",
        textposition="outside",
    ))
    fig_mes.add_trace(go.Scatter(
        x=por_mes["mes_nome"],
        y=por_mes["total_obitos"],
        name="Óbitos",
        mode="lines+markers",
        marker_color="#ef4444",
        yaxis="y2",
    ))
    fig_mes.update_layout(
        yaxis=dict(title="Total de Acidentes"),
        yaxis2=dict(title="Total de Óbitos", overlaying="y", side="right"),
        legend=dict(orientation="h"),
        height=340,
        margin=dict(t=10, b=10),
    )
    st.plotly_chart(fig_mes, width='stretch')

    # ── Evolução Mensal dos Fatores e Causas de Risco ─────────────────────
    st.subheader("Evolução Mensal dos Fatores e Causas de Risco")
    st.caption("Acompanhe o volume de acidentes e óbitos causados por fatores específicos ao longo dos meses do ano.")

    col_fat1, col_fat2 = st.columns(2)
    with col_fat1:
        _m_fatores_temp = st.radio(
            "Métrica de fatores",
            options=["Acidentes", "Óbitos"],
            horizontal=True,
            key="radio_fatores_temp",
        )
    with col_fat2:
        _regiao_fatores = st.selectbox(
            "Região para análise temporal",
            options=["Todas as Regiões", "Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"],
            key="select_regiao_fatores"
        )

    MAP_REGIAO_UFS = {
        "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
        "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
        "Centro-Oeste": ["DF", "GO", "MT", "MS"],
        "Sudeste": ["ES", "MG", "RJ", "SP"],
        "Sul": ["PR", "RS", "SC"]
    }

    _ufs_fatores = ()
    if _regiao_fatores != "Todas as Regiões":
        _ufs_fatores = tuple(MAP_REGIAO_UFS[_regiao_fatores])

    _df_fat_temp = load_fatores_temporais(
        None if ano_sel == "Todos" else int(ano_sel),
        _ufs_fatores,
        agrupar_por="mes"
    )

    if not _df_fat_temp.empty:
        # Determine cols to plot
        cols_to_plot = [
            "acidentes_embriaguez", "acidentes_pista_molhada",
            "acidentes_chuva", "acidentes_buraco", "acidentes_meteo_adversa"
        ] if _m_fatores_temp == "Acidentes" else [
            "obitos_embriaguez", "obitos_pista_molhada",
            "obitos_chuva", "obitos_buraco", "obitos_meteo_adversa"
        ]

        labels_mapping = {
            "acidentes_embriaguez": "Embriaguez",
            "acidentes_pista_molhada": "Pista molhada",
            "acidentes_chuva": "Chuva",
            "acidentes_buraco": "Buracos",
            "acidentes_meteo_adversa": "Meteo. adversa",
            "obitos_embriaguez": "Embriaguez",
            "obitos_pista_molhada": "Pista molhada",
            "obitos_chuva": "Chuva",
            "obitos_buraco": "Buracos",
            "obitos_meteo_adversa": "Meteo. adversa",
        }

        # Prepare formatting for X-axis
        _df_fat_temp["mes_nome"] = _df_fat_temp["mes_acidente"].map({
            1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
        })

        df_long = _df_fat_temp.melt(
            id_vars=["mes_nome"],
            value_vars=cols_to_plot,
            var_name="Fator",
            value_name="Total"
        )
        df_long["Fator"] = df_long["Fator"].map(labels_mapping)

        fig_fat_temp = px.line(
            df_long,
            x="mes_nome",
            y="Total",
            color="Fator",
            markers=True,
            labels={"mes_nome": "Mês", "Total": "Total de " + _m_fatores_temp, "Fator": "Fator de Risco"},
            height=400,
        )
        fig_fat_temp.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig_fat_temp, width='stretch')
    else:
        st.info("Sem dados de fatores para os filtros selecionados.")

    st.divider()

    # ── Acidentes por Hora do Dia ─────────────────────────────────────────────
    st.subheader("Acidentes por Hora do Dia")
    por_hora = (_t["por_hora"] if _any_filter else load_temporal("por_hora"))
    por_hora = por_hora.dropna(subset=["hora"])
    por_hora = por_hora[por_hora["hora"] <= 23].copy()
    por_hora["hora_fmt"] = por_hora["hora"].apply(lambda h: f"{int(h):02d}:00")
    fig_hora = px.area(
        por_hora,
        x="hora_fmt",
        y="total_acidentes",
        labels={"hora_fmt": "Hora", "total_acidentes": "Acidentes"},
        height=320,
    )
    fig_hora.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(fig_hora, width='stretch')

    st.divider()

    # ── Acidentes por Dia da Semana ───────────────────────────────────────────
    st.subheader("Acidentes por Dia da Semana")
    por_dia = (_t["por_dia_semana"] if _any_filter else load_temporal("por_dia_semana"))
    ordem_dias = [
        "SEGUNDA-FEIRA", "TERCA-FEIRA", "QUARTA-FEIRA",
        "QUINTA-FEIRA", "SEXTA-FEIRA", "SABADO", "DOMINGO",
    ]
    por_dia["dia_semana"] = pd.Categorical(
        por_dia["dia_semana"].astype(str), categories=ordem_dias, ordered=True
    )
    por_dia = por_dia.dropna(subset=["dia_semana"]).sort_values("dia_semana")
    fig_dia = px.bar(
        por_dia,
        x="total_acidentes",
        y="dia_semana",
        orientation="h",
        color="total_obitos",
        color_continuous_scale="OrRd",
        labels={"dia_semana": "Dia", "total_acidentes": "Acidentes", "total_obitos": "Óbitos"},
        height=380,
    )
    fig_dia.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(fig_dia, width='stretch')

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — PREVISÃO E TENDÊNCIA
# ══════════════════════════════════════════════════════════════════════════════
with tab_ts:
    st.subheader("Análise Preditiva e Decomposição Sazonal")
    st.markdown("Esta seção utiliza dados contínuos de acidentes agregados por mês/ano. Os modelos estatísticos ajudam a identificar a tendência global, isolar flutuações sazonais e prever cenários futuros.")

    import statsmodels.api as sm
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    import pandas as pd
    
    try:
        ts_df = pd.read_parquet(PROCESSED_DIR / "analise_temporal" / "por_ano_mes.parquet")
        ts_df['data'] = pd.to_datetime(ts_df['data'])
        ts_df = ts_df.set_index('data')
        
        # O modelo precisa de uma frequência definida
        ts_df = ts_df.asfreq('MS')

        # Decomposição STL
        st.markdown("### Decomposição Sazonal (Tendência e Sazonalidade)")
        st.caption("A decomposição separa o volume real em três partes: o que é Tendência Histórica, o que é Sazonalidade (padrões de meses específicos) e os Resíduos (anomalias).")
        
        decomp = sm.tsa.seasonal_decompose(ts_df['total_acidentes'].dropna(), model='additive')
        
        fig_decomp = go.Figure()
        fig_decomp.add_trace(go.Scatter(x=decomp.trend.index, y=decomp.trend, name="Tendência", line=dict(color="#3b82f6", width=3)))
        fig_decomp.add_trace(go.Scatter(x=decomp.seasonal.index, y=decomp.seasonal, name="Sazonalidade", line=dict(color="#f59e0b")))
        fig_decomp.add_trace(go.Scatter(x=decomp.resid.index, y=decomp.resid, name="Resíduos (Ruído)", mode='markers', marker=dict(color="#ef4444", size=4)))
        
        fig_decomp.update_layout(height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_decomp, width='stretch')

        st.divider()

        # Previsão Holt-Winters
        st.markdown("### Previsão para os próximos 12 meses (Holt-Winters)")
        st.caption("Projeção baseada em suavização exponencial, respeitando a tendência e a sazonalidade observada no histórico.")
        
        hw_model = ExponentialSmoothing(
            ts_df['total_acidentes'].dropna(),
            trend='add',
            seasonal='add',
            seasonal_periods=12
        ).fit()
        
        forecast = hw_model.forecast(12)
        forecast_idx = pd.date_range(start=ts_df.index[-1] + pd.DateOffset(months=1), periods=12, freq='MS')
        
        fig_fcst = go.Figure()
        fig_fcst.add_trace(go.Scatter(x=ts_df.index, y=ts_df['total_acidentes'], name="Histórico Real", line=dict(color="#94a3b8")))
        fig_fcst.add_trace(go.Scatter(x=forecast_idx, y=forecast, name="Previsão (12 meses)", line=dict(color="#8b5cf6", dash="dot", width=3)))
        
        fig_fcst.update_layout(height=400, yaxis_title="Total de Acidentes", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_fcst, width='stretch')

    except Exception as e:
        st.error(f"Erro ao carregar ou processar séries temporais: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CORRELAÇÃO & INDICADORES
# ══════════════════════════════════════════════════════════════════════════════
with tab_corr:
    st.subheader("Análise de Correlação: Frota Circulante × Total de Acidentes por Município")
    
    col_corr1, col_corr2 = st.columns(2)
    with col_corr1:
        # Seletor de Motivos (Fatores)
        _motivo_corr = st.selectbox(
            "Fator/Motivo de Acidente a correlacionar (Eixo Y)",
            options=[
                "Geral (Todos os Acidentes)", 
                "🍷 Álcool", 
                "🌧️ Pista Molhada", 
                "🌦️ Chuva", 
                "🕳️ Buracos",
                "📅 Sazonalidade / Pico"
            ],
            key="select_motivo_corr"
        )

    st.caption(
        "Escala logarítmica em ambos os eixos. "
        "Tamanho do ponto = total de óbitos. "
        "Passe o cursor para ver taxas e estatísticas detalhadas."
    )

    # Definição do mapeamento de colunas com base no motivo selecionado
    y_col = {
        "Geral (Todos os Acidentes)": "total_acidentes",
        "🍷 Álcool": "acidentes_com_alcool",
        "🌧️ Pista Molhada": "acidentes_pista_molhada",
        "🌦️ Chuva": "acidentes_chuva",
        "🕳️ Buracos": "acidentes_buraco",
        "📅 Sazonalidade / Pico": "acidentes_sazonal"
    }[_motivo_corr]

    y_label = {
        "Geral (Todos os Acidentes)": "Total de Acidentes (log)",
        "🍷 Álcool": "Acidentes com Álcool (log)",
        "🌧️ Pista Molhada": "Acidentes em Pista Molhada (log)",
        "🌦️ Chuva": "Acidentes em Chuva (log)",
        "🕳️ Buracos": "Acidentes com Buraco (log)",
        "📅 Sazonalidade / Pico": "Acidentes em Meses de Pico (log)"
    }[_motivo_corr]

    df_corr = load_correlacao()
    import scipy.stats as stats

    df_corr_plot = df_corr[
        (df_corr["frota_circulante"] > 0) & (df_corr[y_col] > 0)
    ].copy()
    if uf_sel:
        df_corr_plot = df_corr_plot[df_corr_plot["uf_acidente"].isin(uf_sel)]
    
    top_municipios = df_ranking.head(top_n)["municipio"].unique()
    df_corr_plot = df_corr_plot[df_corr_plot["municipio"].isin(top_municipios)]

    if ano_sel != "Todos":
        st.caption(f"ℹ️ O gráfico de frota usa dados históricos agregados — o filtro de ano não se aplica aqui.")

    fig_corr = px.scatter(
        df_corr_plot,
        x="frota_circulante",
        y=y_col,
        color="uf_acidente",
        size="total_obitos",
        size_max=30,
        hover_name="municipio",
        hover_data={
            "taxa_acidente_100k": True,
            "taxa_letalidade": True,
            "acidentes_com_alcool": ":,",
            "acidentes_pista_molhada": ":,",
            "acidentes_chuva": ":,",
            "acidentes_buraco": ":,",
            "acidentes_sazonal": ":,"
        },
        log_x=True,
        log_y=True,
        labels={
            "frota_circulante": "Frota Circulante (log)",
            y_col: y_label,
            "uf_acidente": "UF",
            "acidentes_com_alcool": "🍷 Álcool",
            "acidentes_pista_molhada": "🌧️ Pista Molhada",
            "acidentes_chuva": "🌦️ Chuva",
            "acidentes_buraco": "🕳️ Buracos",
            "acidentes_sazonal": "📅 Sazonalidade / Pico"
        },
        height=460,
    )

    # Linha de tendência global para as cidades exibidas
    if len(df_corr_plot) > 1:
        _lx = np.log10(df_corr_plot["frota_circulante"])
        _ly = np.log10(df_corr_plot[y_col])
        _coef = np.polyfit(_lx, _ly, 1)

        r_val, p_val = stats.pearsonr(_lx, _ly)
        r_squared = r_val ** 2
        p_text = "p < 0.001" if p_val < 0.001 else f"p = {p_val:.3f}"

        _x_range = np.linspace(_lx.min(), _lx.max(), 100)
        _trend_x = 10 ** _x_range
        _trend_y = 10 ** np.polyval(_coef, _x_range)

        fig_corr.add_trace(go.Scatter(
            x=_trend_x, y=_trend_y,
            mode="lines",
            name=f"Tendência Global (β={_coef[0]:.2f}, R²={r_squared:.2f}, {p_text})",
            line=dict(color="black", width=2, dash="dash"),
        ))

    fig_corr.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(fig_corr, width='stretch')

    st.divider()

    # ── Distribuição dos índices por UF (Box plot) ────────────────────────────
    st.subheader(f"Distribuição da Taxa de Acidentes por 100k hab. (Top {top_n} Municípios)")
    _df_box = df_ranking.dropna(subset=["taxa_acidente_100k"]).head(top_n)
    _uf_order = (
        _df_box.groupby("uf_acidente", observed=True)["taxa_acidente_100k"]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )
    fig_box = px.box(
        _df_box,
        x="uf_acidente",
        y="taxa_acidente_100k",
        color="uf_acidente",
        points="all",
        category_orders={"uf_acidente": _uf_order},
        labels={"uf_acidente": "UF", "taxa_acidente_100k": "Taxa/100k hab."},
        height=440,
    )
    fig_box.update_layout(showlegend=False, margin=dict(t=10, b=10))
    st.plotly_chart(fig_box, width='stretch')

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — FATORES & CAUSAS
# ══════════════════════════════════════════════════════════════════════════════
with tab_fatores:
    st.subheader("Fatores, Causas e Locais de Acidentes")

    # 1. SAZONALIDADE REGIONAL (HEATMAP)
    st.markdown("#### Sazonalidade Regional: O Comportamento de cada Região")
    st.caption("Como a onda de acidentes viaja pelo país durante o ano? Cada região apresenta seu próprio mês de pico consolidado.")
    try:
        df_reg = pd.read_parquet(PROCESSED_DIR / "analise_temporal" / "regional_seasonality.parquet")
        meses_nome = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 
                      7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
        df_reg["mes_nome"] = df_reg["mes_acidente"].map(meses_nome)
        df_reg = df_reg.sort_values(by=["regiao", "mes_acidente"])
        pivot_reg = df_reg.pivot(index="regiao", columns="mes_nome", values="pct_acidentes")
        ordem_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        pivot_reg = pivot_reg[ordem_meses]
        ordem_regioes = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']
        pivot_reg = pivot_reg.reindex(ordem_regioes)
        
        fig_heat = px.imshow(
            pivot_reg,
            labels=dict(x="Mês", y="Região", color="% do Ano na Região"),
            x=ordem_meses,
            y=ordem_regioes,
            color_continuous_scale="Reds",
            aspect="auto",
            title="Concentração de Acidentes no Ano por Região"
        )
        fig_heat.update_xaxes(side="top")
        fig_heat.update_layout(height=360)
        st.plotly_chart(fig_heat, width='stretch')
    except Exception as e:
        st.error(f"Erro ao carregar sazonalidade regional: {e}")

    st.divider()

    # 2. GRÁFICO INTEGRADO: SAZONALIDADE, FATORES E MUNICÍPIOS (GRÁFICO DE LINHAS)
    st.markdown("#### Cruzamento Sazonal e Fatores de Risco por Município")
    st.caption("Evolução mensal de acidentes causados por fatores de risco específicos nas principais cidades (Top N). Use a legenda lateral para isolar municípios ou fatores.")
    
    _regiao_cruzado = st.selectbox(
        "Selecione a Região para análise por município",
        options=["Todas as Regiões", "Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"],
        key="select_regiao_cruzado"
    )
    
    try:
        _ano_sun = None if ano_sel == "Todos" else int(ano_sel)
        MAP_REGIAO_UFS = {
            "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
            "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
            "Centro-Oeste": ["DF", "GO", "MT", "MS"],
            "Sudeste": ["ES", "MG", "RJ", "SP"],
            "Sul": ["PR", "RS", "SC"]
        }
        _ufs_sun = tuple(MAP_REGIAO_UFS[_regiao_cruzado]) if _regiao_cruzado != "Todas as Regiões" else ()
        df_sun = load_sunburst_sazonal_data(_ano_sun, _ufs_sun, mes_sel)
        
        if df_sun.empty:
            st.info("Sem dados suficientes para gerar o gráfico sazonal.")
        else:
            if _regiao_cruzado != "Todas as Regiões":
                ufs_regiao = MAP_REGIAO_UFS[_regiao_cruzado]
                df_ranking_reg = df_ranking[df_ranking["uf_acidente"].isin(ufs_regiao)]
                df_ranking_top = df_ranking_reg.head(top_n)
            else:
                df_ranking_top = df_ranking.head(top_n)

            df_sun["mun_uf"] = df_sun["municipio"].astype(str) + " - " + df_sun["uf_acidente"].astype(str)
            df_ranking_top_keys = df_ranking_top["municipio"].astype(str) + " - " + df_ranking_top["uf_acidente"].astype(str)
            df_cruzado = df_sun[df_sun["mun_uf"].isin(df_ranking_top_keys)].copy()
            
            # Filtra fatores sem relevância para focar nos 4 fatores causadores principais
            df_cruzado = df_cruzado[df_cruzado["fator"] != "Outros / Sem Fator"].copy()
            
            if df_cruzado.empty:
                st.info("Sem dados nos Top N municípios para gerar a visualização.")
            else:
                ordem_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
                df_cruzado["mes_nome"] = pd.Categorical(df_cruzado["mes_nome"], categories=ordem_meses, ordered=True)
                df_cruzado = df_cruzado.sort_values(["mes_nome", "mun_uf"])
                
                df_cruzado = df_cruzado.rename(columns={
                    "mun_uf": "Localidade",
                    "mes_nome": "Mês",
                    "qtde_acidente": "Acidentes",
                    "fator": "Fator de Risco"
                })

                # Criação do Gráfico de Linhas Cruzado
                fig_cruzado = px.line(
                    df_cruzado,
                    x="Mês",
                    y="Acidentes",
                    color="Localidade",
                    line_dash="Fator de Risco",
                    markers=True,
                    category_orders={"Mês": ordem_meses},
                    color_discrete_sequence=px.colors.qualitative.Alphabet,
                    title="Tendência Temporal dos Fatores por Cidade",
                    height=580,
                )
                fig_cruzado.update_layout(
                    margin=dict(t=80, b=20, l=10, r=10),
                    legend=dict(orientation="v", yanchor="top", y=1.0, xanchor="left", x=1.02)
                )
                st.plotly_chart(fig_cruzado, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao gerar gráfico de linhas multidimensional: {e}")

    st.divider()

    # 3. DETALHE LOCAL (UF) - TIPOS, BAIRROS E RUAS
    st.markdown("#### Detalhamento de Logradouros e Tipos de Acidentes")
    if not uf_sel:
        st.info("ℹ️ Selecione ao menos uma UF no painel lateral esquerdo para carregar o detalhamento local (Tipos de acidentes, bairros e ruas).")
    else:
        try:
            _gdf = load_gold_uf(tuple(sorted(uf_sel)))
            _vdf = load_vitimas_uf(tuple(sorted(uf_sel)))

            if ano_sel != "Todos":
                _gdf = _gdf[_gdf["ano_acidente"] == int(ano_sel)]
                _vdf = _vdf[_vdf["ano_acidente"] == int(ano_sel)]
            if mes_sel is not None:
                _gdf = _gdf[_gdf["mes_acidente"] == int(mes_sel)]
                _vdf = _vdf[_vdf["mes_acidente"] == int(mes_sel)]

            st.markdown("##### Tipos de Acidentes na Região Selecionada")
            df_tipos = (
                _gdf.groupby("tp_acidente", observed=True)
                .agg(total_acidentes=("qtde_acidente", "sum"), total_obitos=("qtde_obitos", "sum"), total_feridos=("qtde_feridosilesos", "sum"))
                .reset_index().dropna(subset=["tp_acidente"]).sort_values("total_acidentes", ascending=False).reset_index(drop=True)
            )
            df_tipos.insert(0, "rank", df_tipos.index + 1)
            df_tipos["mortalidade"] = (df_tipos["total_obitos"] / df_tipos["total_acidentes"].replace(0, pd.NA) * 100).round(2)

            tipo_l, tipo_r = st.columns([1.3, 0.7])
            with tipo_l:
                fig_tipos = px.bar(
                    df_tipos.sort_values("total_acidentes"),
                    x="total_acidentes", y="tp_acidente", orientation="h", text="total_acidentes",
                    color="total_acidentes", color_continuous_scale="Blues",
                    labels={"total_acidentes": "Total de Acidentes", "tp_acidente": "Tipo"}, height=460,
                )
                fig_tipos.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
                fig_tipos.update_layout(margin=dict(l=0, r=30, t=10, b=10), coloraxis_showscale=False)
                st.plotly_chart(fig_tipos, use_container_width=True)

            with tipo_r:
                st.dataframe(
                    df_tipos.rename(columns={
                        "rank": "#", "tp_acidente": "Tipo de Acidente", "total_acidentes": "Acidentes",
                        "total_obitos": "Óbitos", "total_feridos": "Feridos", "mortalidade": "Letalidade (%)"
                    }),
                    hide_index=True, height=460, use_container_width=True
                )

            st.divider()

            # Bairros e Ruas com Mais Acidentes
            st.markdown("##### Bairros e Ruas com Maior Número de Acidentes")

            # Strings que equivalem a "sem informação" — tratadas como nulo
            _VALORES_NULOS = {
                "SEM CORRELACAO", "NAO INFORMADO", "NAO INFORMADA",
                "DESCONHECIDO", "DESCONHECIDA", "NÃO INFORMADO",
                "NÃO INFORMADA", "NONE", "NULL", "", "0",
            }

            df_bairros = (
                _gdf.groupby(["municipio", "bairro_acidente"], observed=True, dropna=False)
                .agg(total_acidentes=("qtde_acidente", "sum"), total_obitos=("qtde_obitos", "sum"))
                .reset_index()
            )
            df_bairros = df_bairros[
                df_bairros["bairro_acidente"].notna() &
                (~df_bairros["bairro_acidente"].astype(str).str.upper().str.strip().isin(_VALORES_NULOS))
            ]
            df_bairros["total_obitos"] = df_bairros["total_obitos"].fillna(0).astype(int)
            df_bairros = df_bairros.sort_values("total_acidentes", ascending=False).head(20).reset_index(drop=True)
            df_bairros.insert(0, "rank", df_bairros.index + 1)

            _has_rua = "end_acidente" in _gdf.columns
            if _has_rua:
                df_ruas = (
                    _gdf.groupby(["municipio", "bairro_acidente", "end_acidente"], observed=True, dropna=False)
                    .agg(total_acidentes=("qtde_acidente", "sum"), total_obitos=("qtde_obitos", "sum"))
                    .reset_index()
                )
                # Remove ruas nulas ou equivalentes a "sem informação"
                df_ruas = df_ruas[
                    df_ruas["end_acidente"].notna() &
                    (~df_ruas["end_acidente"].astype(str).str.upper().str.strip().isin(_VALORES_NULOS))
                ]
                df_ruas["total_obitos"] = df_ruas["total_obitos"].fillna(0).astype(int)
                # Bairro nulo na tabela de ruas → exibe "—"
                _bairro_str = df_ruas["bairro_acidente"].astype(str)
                df_ruas["bairro_acidente"] = _bairro_str.where(
                    _bairro_str.notna() &
                    (_bairro_str.str.upper().str.strip() != "NAN") &
                    (~_bairro_str.str.upper().str.strip().isin(_VALORES_NULOS)),
                    other="—"
                )
                df_ruas = df_ruas.sort_values("total_acidentes", ascending=False).head(20).reset_index(drop=True)
                df_ruas.insert(0, "rank", df_ruas.index + 1)


            rl1, rl2 = st.columns(2)
            with rl1:
                st.markdown("**Top 20 Bairros**")
                st.dataframe(
                    df_bairros.rename(columns={"rank": "#", "municipio": "Município", "bairro_acidente": "Bairro", "total_acidentes": "Acidentes", "total_obitos": "Óbitos"}),
                    hide_index=True, height=540, use_container_width=True
                )
            with rl2:
                if _has_rua:
                    st.markdown("**Top 20 Ruas / Avenidas**")
                    st.dataframe(
                        df_ruas.rename(columns={"rank": "#", "municipio": "Município", "bairro_acidente": "Bairro", "end_acidente": "Rua / Avenida", "total_acidentes": "Acidentes", "total_obitos": "Óbitos"}),
                        hide_index=True, height=540, use_container_width=True
                    )
                else:
                    st.info("Dados de logradouro não disponíveis.")
        except Exception as e:
            st.error(f"Erro ao carregar o detalhamento local por UF: {e}")

