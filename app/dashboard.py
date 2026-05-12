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
    mes_sel: int | None = None
    if ano_sel != "Todos":
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
            taxa_mortalidade=("taxa_mortalidade", "mean"),
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
    _mask_acid = _agg_yr["total_acidentes"] > 0
    _agg_yr["taxa_mortalidade"] = (
        (_agg_yr["total_obitos"] / _agg_yr["total_acidentes"]) * 100
    ).where(_mask_acid).round(2)
    df_ranking = _agg_yr.drop(columns=["_qtde_hab"])

df_ranking.insert(0, "ranking_geral", df_ranking.index + 1)
df_ranking_top = df_ranking.head(top_n)


# ── Título e KPIs ─────────────────────────────────────────────────────────────
st.title("Análise de Acidentes de Trânsito no Brasil")
st.caption("Fonte: RENAEST / SENATRAN | Pipeline: ATNB")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total de Acidentes", f"{df_ranking['total_acidentes'].sum():,.0f}")
k2.metric("Total de Óbitos", f"{df_ranking['total_obitos'].sum():,.0f}")
k3.metric("Taxa de Mortalidade", f"{df_ranking['taxa_mortalidade'].mean():.1f}%")
k4.metric("Municípios Analisados", f"{df_ranking['municipio'].nunique():,}")

st.divider()

# ── Ranking de Municípios e Taxa por 100k ─────────────────────────────────────
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

st.divider()

# ── Evolução Temporal de Acidentes e Óbitos ───────────────────────────────────
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

st.divider()

# ── Acidentes por Mês ─────────────────────────────────────────────────────────
st.subheader("Acidentes por Mês")
por_mes = load_temporal("por_mes")
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
st.plotly_chart(fig_mes, use_container_width=True)

st.divider()

# ── Acidentes por Hora do Dia ─────────────────────────────────────────────────
st.subheader("Acidentes por Hora do Dia")
por_hora = load_temporal("por_hora")
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
st.plotly_chart(fig_hora, use_container_width=True)

st.divider()

# ── Acidentes por Dia da Semana ───────────────────────────────────────────────
st.subheader("Acidentes por Dia da Semana")
por_dia = load_temporal("por_dia_semana")
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
st.plotly_chart(fig_dia, use_container_width=True)

st.divider()

# ── Matriz de Correlação ──────────────────────────────────────────────────────
st.subheader("Matriz de Correlação entre Indicadores de Acidentes")

# Observação: a matriz exibe o coeficiente de Pearson (−1 a +1) entre os
# indicadores numéricos do ranking de municípios.
# • Valores próximos de +1 → forte correlação positiva (ex.: mais acidentes, mais óbitos)
# • Valores próximos de  0 → sem relação linear entre as variáveis
# • Valores próximos de −1 → correlação negativa (ex.: taxa alta em municípios pequenos)
# A diagonal principal é sempre 1 (variável correlacionada com ela mesma).
# Use os filtros de UF e Ano para explorar padrões regionais específicos.

_corr_cols = {
    "total_acidentes":  "Acidentes",
    "total_obitos":     "Óbitos",
    "total_feridos":    "Feridos",
    # "taxa_mortalidade": "Mortalidade (%)",
    "acidentes_chuva":  "Em chuva",
    "acidentes_noite":  "À noite",
}

_df_corr_matrix = (
    df_ranking[list(_corr_cols.keys())]
    .rename(columns=_corr_cols)
    .corr(numeric_only=True)
)

fig_matrix = px.imshow(
    _df_corr_matrix,
    text_auto=".2f",
    color_continuous_scale="RdBu_r",
    zmin=-1,
    zmax=1,
    aspect="auto",
    labels={"color": "Pearson r"},
    height=460,
)
fig_matrix.update_traces(textfont_size=12)
fig_matrix.update_layout(
    margin=dict(l=10, r=10, t=10, b=10),
    coloraxis_colorbar=dict(title="r", tickvals=[-1, -0.5, 0, 0.5, 1]),
)
st.plotly_chart(fig_matrix, use_container_width=True)

st.divider()

# ── Correlação: Frota x Acidentes ────────────────────────────────────────────
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

st.divider()

# ── Tabela completa do ranking ────────────────────────────────────────────────
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

st.divider()

# ── Fatores, Causas e Locais de Acidentes ─────────────────────────────────────
st.subheader("Fatores, Causas e Locais de Acidentes")

if not uf_sel:
    st.info("Selecione ao menos uma UF no painel lateral para visualizar esta análise.")
else:
    _gdf = load_gold_uf(tuple(sorted(uf_sel)))
    _vdf = load_vitimas_uf(tuple(sorted(uf_sel)))

    # ── KPIs de Causas ───────────────────────────────────────────────────────
    st.markdown("#### Fatores de Risco — Acidentes por Causa")

    _COND_ADVERSE = [
        "CHUVA", "NUBLADO", "GAROACHUVISCO",
        "NEVOEIRO  NEVOA OU FUMACA", "VENTOS FORTES", "NEVE", "GRANIZO",
    ]

    _acid_alcool  = int(_vdf[_vdf["susp_alcool"] == "SIM"]["num_acidente"].nunique())
    _acid_buraco  = int(_gdf[_gdf["cond_pista"] == "COM BURACO"]["qtde_acidente"].sum())
    _acid_molhada = int(_gdf[_gdf["cond_pista"].isin(["MOLHADA", "ESCORREGADIA"])]["qtde_acidente"].sum())
    _acid_meteo   = int(_gdf[_gdf["cond_meteorologica"].isin(_COND_ADVERSE)]["qtde_acidente"].sum())
    _veic_pred    = _gdf["veiculo_predominante"].dropna().mode()
    _veic_top     = _veic_pred.iloc[0].title() if len(_veic_pred) > 0 else "N/D"

    ca1, ca2, ca3, ca4 = st.columns(4)
    ca1.metric("Bebida Alcoólica", f"{_acid_alcool:,.0f}",
               help="Acidentes com suspeita de álcool/entorpecente (susp_alcool = SIM)")
    ca2.metric("Buracos na Pista", f"{_acid_buraco:,.0f}",
               help="cond_pista = COM BURACO")
    ca3.metric("Pista Molhada", f"{_acid_molhada:,.0f}",
               help="cond_pista = MOLHADA ou ESCORREGADIA")
    ca4.metric("Cond. Meteorológicas", f"{_acid_meteo:,.0f}",
               help="Chuva, nevoeiro, granizo, neve ou ventos fortes")

    cb1, cb2, cb3, cb4 = st.columns(4)
    cb1.metric("Veículo Predominante", _veic_top,
               help="Tipo de veículo com maior participação nos acidentes da UF")
    cb2.metric("Entorpecentes", f"{_acid_alcool:,.0f}",
               help="Base SENATRAN não distingue álcool de outras drogas — mesmo indicador")
    cb3.metric("Defeitos no Veículo", "N/D",
               help="Dado não disponível na base SENATRAN/RENAEST")
    cb4.metric("Falta de Sinalização", "N/D",
               help="Dado não disponível na base SENATRAN/RENAEST")

    st.caption("Fontes: SENATRAN/RENAEST — acidentes_gold e vitimas_silver. N/D = dado não coletado.")

    st.divider()

    # ── Tipos de Acidentes ────────────────────────────────────────────────────
    st.markdown("#### Tipos de Acidentes")

    df_tipos = (
        _gdf.groupby("tp_acidente", observed=True)
        .agg(
            total_acidentes=("qtde_acidente", "sum"),
            total_obitos=("qtde_obitos", "sum"),
            total_feridos=("qtde_feridosilesos", "sum"),
        )
        .reset_index()
        .dropna(subset=["tp_acidente"])
        .sort_values("total_acidentes", ascending=False)
        .reset_index(drop=True)
    )
    df_tipos.insert(0, "rank", df_tipos.index + 1)
    df_tipos["mortalidade"] = (
        df_tipos["total_obitos"] / df_tipos["total_acidentes"].replace(0, pd.NA) * 100
    ).round(2)

    tipo_l, tipo_r = st.columns([1.3, 0.7])

    with tipo_l:
        fig_tipos = px.bar(
            df_tipos.sort_values("total_acidentes"),
            x="total_acidentes",
            y="tp_acidente",
            orientation="h",
            text="total_acidentes",
            color="total_acidentes",
            color_continuous_scale="Blues",
            labels={"total_acidentes": "Total de Acidentes", "tp_acidente": "Tipo"},
            height=460,
        )
        fig_tipos.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_tipos.update_layout(margin=dict(l=0, r=30, t=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig_tipos, use_container_width=True)

    with tipo_r:
        st.dataframe(
            df_tipos.rename(columns={
                "rank": "#",
                "tp_acidente": "Tipo de Acidente",
                "total_acidentes": "Acidentes",
                "total_obitos": "Óbitos",
                "total_feridos": "Feridos",
                "mortalidade": "Mortalidade (%)",
            }),
            hide_index=True,
            height=460,
            use_container_width=True,
        )

    st.divider()

    # ── Veículos Envolvidos ───────────────────────────────────────────────────
    st.markdown("#### Acidentes por Tipo de Veículo")

    df_veic = (
        _gdf.groupby("veiculo_predominante", observed=True)
        .agg(total_acidentes=("qtde_acidente", "sum"))
        .reset_index()
        .dropna(subset=["veiculo_predominante"])
        .sort_values("total_acidentes", ascending=False)
        .head(12)
    )
    fig_veic = px.bar(
        df_veic.sort_values("total_acidentes"),
        x="total_acidentes",
        y="veiculo_predominante",
        orientation="h",
        text="total_acidentes",
        color="total_acidentes",
        color_continuous_scale="Greens",
        labels={"total_acidentes": "Acidentes", "veiculo_predominante": "Tipo de Veículo"},
        height=440,
    )
    fig_veic.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig_veic.update_layout(margin=dict(l=0, r=30, t=10, b=10), coloraxis_showscale=False)
    st.plotly_chart(fig_veic, use_container_width=True)

    st.divider()

    # ── Bairros e Ruas com Mais Acidentes ─────────────────────────────────────
    st.markdown("#### Bairros e Ruas com Maior Número de Acidentes")

    df_bairros = (
        _gdf.groupby(["municipio", "bairro_acidente"], observed=True, dropna=False)
        .agg(total_acidentes=("qtde_acidente", "sum"), total_obitos=("qtde_obitos", "sum"))
        .reset_index()
        .dropna(subset=["bairro_acidente"])
        .sort_values("total_acidentes", ascending=False)
        .head(20)
        .reset_index(drop=True)
    )
    df_bairros.insert(0, "rank", df_bairros.index + 1)

    _has_rua = "end_acidente" in _gdf.columns

    if _has_rua:
        df_ruas = (
            _gdf.groupby(
                ["municipio", "bairro_acidente", "end_acidente"],
                observed=True, dropna=False,
            )
            .agg(total_acidentes=("qtde_acidente", "sum"), total_obitos=("qtde_obitos", "sum"))
            .reset_index()
            .dropna(subset=["end_acidente"])
            .sort_values("total_acidentes", ascending=False)
            .head(20)
            .reset_index(drop=True)
        )
        df_ruas.insert(0, "rank", df_ruas.index + 1)

    rl1, rl2 = st.columns(2)

    with rl1:
        st.markdown("**Top 20 Bairros**")
        st.dataframe(
            df_bairros.rename(columns={
                "rank": "#", "municipio": "Município",
                "bairro_acidente": "Bairro",
                "total_acidentes": "Acidentes", "total_obitos": "Óbitos",
            }),
            hide_index=True,
            height=540,
            use_container_width=True,
        )

    with rl2:
        if _has_rua:
            st.markdown("**Top 20 Ruas / Avenidas**")
            st.dataframe(
                df_ruas.rename(columns={
                    "rank": "#", "municipio": "Município",
                    "bairro_acidente": "Bairro", "end_acidente": "Rua / Avenida",
                    "total_acidentes": "Acidentes", "total_obitos": "Óbitos",
                }),
                hide_index=True,
                height=540,
                use_container_width=True,
            )
        else:
            st.info(
                "Dados de logradouro (end_acidente) não disponíveis. "
                "Re-execute o pipeline para incluir este campo."
            )

st.divider()

# ── Aprendizado de Máquina ────────────────────────────────────────────────────
st.subheader("Aprendizado de Máquina — Previsão de Gravidade de Lesão")
st.caption(
    "Classifica a gravidade da lesão (SEM FERIMENTO / LEVE / GRAVE / ÓBITO) "
    "com base em faixa etária, gênero, tipo de envolvido, equipamento de segurança, "
    "suspeita de álcool e mês do acidente."
)

with st.expander("Treinar e avaliar modelos (scikit-learn)", expanded=False):
    from src.pipeline.ml import FEATURES, run_ml_pipeline  # noqa: E402

    ml_col1, ml_col2, ml_col3 = st.columns(3)
    with ml_col1:
        ano_ml = st.selectbox(
            "Ano dos dados",
            options=anos_disponiveis,
            index=len(anos_disponiveis) - 1,
            key="ml_ano",
        )
    with ml_col2:
        sample_ml = st.select_slider(
            "Amostras para treino+teste",
            options=[5_000, 10_000, 20_000, 30_000, 50_000],
            value=20_000,
            key="ml_sample",
        )
    with ml_col3:
        modelos_sel = st.multiselect(
            "Modelos",
            options=["DecisionTree", "MLP", "SVC"],
            default=["DecisionTree", "MLP", "SVC"],
            key="ml_models",
        )

    _model_map = {"DecisionTree": "dt", "MLP": "mlp", "SVC": "svc"}
    models_keys = [_model_map[m] for m in modelos_sel if m in _model_map]

    if st.button("Treinar modelos", type="primary", disabled=not models_keys):

        @st.cache_data(show_spinner="Treinando modelos...")
        def _cached_ml(ano: int, n: int, keys: tuple) -> dict:
            return run_ml_pipeline(PROCESSED_DIR, ano=ano, sample_n=n, models=list(keys))

        with st.spinner("Treinando... isso pode levar de 30 s a 2 min dependendo dos modelos."):
            ml_results = _cached_ml(ano_ml, sample_ml, tuple(sorted(models_keys)))

        st.success("Modelos treinados com sucesso!")

        resumo = []
        for key, res in ml_results.items():
            row = {"Modelo": res["modelo"], "Acurácia (test)": f"{res['acuracia']:.4f}"}
            if "cv_mean" in res:
                row["Cross-Val (média ± std)"] = f"{res['cv_mean']:.4f} ± {res['cv_std']:.4f}"
            else:
                row["Cross-Val (média ± std)"] = "—"
            resumo.append(row)

        st.dataframe(pd.DataFrame(resumo), use_container_width=True, hide_index=True)

        st.markdown("**Previsões de exemplo (5 amostras do conjunto de teste):**")
        for key, res in ml_results.items():
            st.write(f"`{res['modelo']}` → {res['y_pred_sample']}")

        if "dt" in ml_results and "feature_importances" in ml_results["dt"]:
            fi = ml_results["dt"]["feature_importances"]
            df_fi = (
                pd.DataFrame({"Feature": list(fi.keys()), "Importância": list(fi.values())})
                .sort_values("Importância", ascending=True)
            )
            fig_fi = px.bar(
                df_fi,
                x="Importância",
                y="Feature",
                orientation="h",
                title="Importância das Features — Decision Tree",
                height=300,
                color="Importância",
                color_continuous_scale="Blues",
            )
            fig_fi.update_layout(margin=dict(t=40, b=10), coloraxis_showscale=False)
            st.plotly_chart(fig_fi, use_container_width=True)

        with st.expander("Relatório detalhado por classe"):
            for key, res in ml_results.items():
                st.markdown(f"**{res['modelo']}**")
                report_df = (
                    pd.DataFrame(res["report"])
                    .T.drop(index=["accuracy", "macro avg", "weighted avg"], errors="ignore")
                    .round(4)
                )
                st.dataframe(
                    report_df[["precision", "recall", "f1-score", "support"]],
                    use_container_width=True,
                )
                st.markdown("---")
