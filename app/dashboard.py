"""
Dashboard ATNB - Análise de Acidentes de Trânsito no Brasil
============================================================
Consome os datasets Parquet gerados pelo pipeline.
Execute o pipeline primeiro:
    python -m src.pipeline.pipeline --skip-heavy
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Garante que o módulo src seja encontrado
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline.persist import load_parquet  # noqa: E402

PROCESSED_DIR = ROOT / "data" / "processed"

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


# ── Carregamento com cache ────────────────────────────────────────────────────
@st.cache_data(show_spinner="Carregando dados...")
def load_ranking() -> pd.DataFrame:
    return load_parquet(PROCESSED_DIR / "ranking_locais.parquet")


@st.cache_data(show_spinner="Carregando dados temporais...")
def load_temporal(name: str) -> pd.DataFrame:
    return load_parquet(PROCESSED_DIR / "analise_temporal" / f"{name}.parquet")


@st.cache_data(show_spinner="Carregando correlação...")
def load_correlacao() -> pd.DataFrame:
    return load_parquet(PROCESSED_DIR / "correlacao_frota_acidentes.parquet")


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
    ufs_disponiveis = sorted(ranking["uf_acidente"].dropna().unique())
    uf_sel = st.multiselect(
        "UF(s)",
        options=ufs_disponiveis,
        default=[],
        placeholder="Todas as UFs",
    )
    top_n = st.slider("Top N municípios", min_value=5, max_value=30, value=10)

# ── Aplicar filtros ao ranking ────────────────────────────────────────────────
df_ranking = ranking.copy()
if uf_sel:
    df_ranking = df_ranking[df_ranking["uf_acidente"].isin(uf_sel)]
df_ranking_top = df_ranking.head(top_n)

# ── Título ────────────────────────────────────────────────────────────────────
st.title("Análise de Acidentes de Trânsito no Brasil")
st.caption("Fonte: RENAEST / SENATRAN | Pipeline: ATNB")

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total de Acidentes", f"{df_ranking['total_acidentes'].sum():,.0f}")
k2.metric("Total de Óbitos", f"{df_ranking['total_obitos'].sum():,.0f}")
k3.metric("Taxa de Mortalidade", f"{df_ranking['taxa_mortalidade'].mean():.1f}%")
k4.metric("Municípios Analisados", f"{df_ranking['municipio'].nunique():,}")

st.divider()

# ── Linha 1: Ranking e Taxa por 100k ─────────────────────────────────────────
col_left, col_right = st.columns([1.2, 0.8])

with col_left:
    st.subheader(f"Top {top_n} Municípios com Mais Acidentes")
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
    st.plotly_chart(fig_rank, use_container_width=True)

with col_right:
    st.subheader("Taxa de Acidente por 100k Habitantes")
    df_taxa = df_ranking_top.dropna(subset=["taxa_acidente_100k"])
    fig_taxa = px.bar(
        df_taxa.sort_values("taxa_acidente_100k"),
        x="taxa_acidente_100k",
        y="municipio",
        orientation="h",
        color="taxa_mortalidade",
        color_continuous_scale="Reds",
        labels={
            "taxa_acidente_100k": "Acidentes / 100k hab.",
            "municipio": "Município",
            "taxa_mortalidade": "Mortalidade %",
        },
        height=420,
    )
    fig_taxa.update_layout(margin=dict(l=0, r=20, t=20, b=0))
    st.plotly_chart(fig_taxa, use_container_width=True)

st.divider()

# ── Linha 2: Evolução temporal ────────────────────────────────────────────────
st.subheader("Evolução Temporal de Acidentes e Óbitos")
por_ano = load_temporal("por_ano")

fig_ano = go.Figure()
fig_ano.add_trace(go.Bar(
    x=por_ano["ano_acidente"].astype(int),
    y=por_ano["total_acidentes"],
    name="Acidentes",
    marker_color="#3b82f6",
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
st.plotly_chart(fig_ano, use_container_width=True)

# ── Linha 3: Distribuições ────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("Por Hora do Dia")
    por_hora = load_temporal("por_hora")
    por_hora = por_hora.dropna(subset=["hora"])
    fig_hora = px.area(
        por_hora,
        x="hora",
        y="total_acidentes",
        labels={"hora": "Hora", "total_acidentes": "Acidentes"},
        height=300,
    )
    fig_hora.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(fig_hora, use_container_width=True)

with c2:
    st.subheader("Por Dia da Semana")
    por_dia = load_temporal("por_dia_semana")
    ordem_dias = ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SABADO", "DOMINGO"]
    por_dia["dia_semana"] = pd.Categorical(
        por_dia["dia_semana"].astype(str), categories=ordem_dias, ordered=True
    )
    por_dia = por_dia.dropna(subset=["dia_semana"]).sort_values("dia_semana")
    fig_dia = px.bar(
        por_dia,
        x="dia_semana",
        y="total_acidentes",
        color="total_obitos",
        color_continuous_scale="OrRd",
        labels={
            "dia_semana": "Dia", "total_acidentes": "Acidentes",
            "total_obitos": "Óbitos",
        },
        height=300,
    )
    fig_dia.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(fig_dia, use_container_width=True)

with c3:
    st.subheader("Por Fase do Dia")
    por_fase = load_temporal("por_fase_dia")
    por_fase = por_fase.dropna(subset=["fase_dia"])
    fig_fase = px.pie(
        por_fase,
        values="total_acidentes",
        names="fase_dia",
        hole=0.4,
        height=300,
    )
    fig_fase.update_layout(margin=dict(t=10, b=0))
    st.plotly_chart(fig_fase, use_container_width=True)

st.divider()

# ── Linha 4: Correlação frota x acidentes ────────────────────────────────────
st.subheader("Correlação: Frota Circulante x Total de Acidentes por Município")
df_corr = load_correlacao()
df_corr_plot = df_corr[
    (df_corr["frota_circulante"] > 0) & (df_corr["total_acidentes"] > 0)
].copy()

if uf_sel:
    df_corr_plot = df_corr_plot[df_corr_plot["uf_acidente"].isin(uf_sel)]

fig_corr = px.scatter(
    df_corr_plot,
    x="frota_circulante",
    y="total_acidentes",
    color="uf_acidente",
    size="total_obitos",
    size_max=30,
    hover_name="municipio",
    hover_data={"taxa_acidente_100k": True, "taxa_mortalidade": True},
    log_x=True,
    log_y=True,
    labels={
        "frota_circulante": "Frota Circulante (log)",
        "total_acidentes": "Total de Acidentes (log)",
        "uf_acidente": "UF",
    },
    height=420,
)
fig_corr.update_layout(margin=dict(t=10, b=10))
st.plotly_chart(fig_corr, use_container_width=True)

# ── Tabela completa ───────────────────────────────────────────────────────────
with st.expander("Tabela completa do ranking de municípios"):
    display_cols = [
        "ranking_geral", "municipio", "uf_acidente", "total_acidentes",
        "total_obitos", "total_feridos", "taxa_acidente_100k", "taxa_mortalidade",
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
            "taxa_mortalidade": "Mortalidade (%)",
            "acidentes_chuva": "Em chuva",
            "acidentes_noite": "À noite",
        }),
        use_container_width=True,
        height=400,
    )