import streamlit as st
import plotly.express as px
from src.processing import *

st.set_page_config(layout="wide")

st.title("Analise de dados de acidentes de trânsito no Brasil")

data_frame = load_data()

# =============================
# KPIs
# =============================
col1, col2, col3 = st.columns(3)

col1.metric("Total de Acidentes", f"{len(data_frame):,}")
col2.metric("Estados Analisado", f"{data_frame['uf'].nunique()}")
col3.metric("Principais Causas", f"{data_frame['causa_acidente'].nunique()}")

# =============================
# Gráfico 1 - Por Estado
# =============================
st.subheader("Acidentes por Estado")

estados = acidentes_por_estado(data_frame)

fix_estados = px.bar(estados, 
    x=estados.index, 
    y=estados.values, 
    labels={'x': 'Estado', 'y': 'Número de Acidentes'}, title="Número de Acidentes por Estado")

st.plotly_chart(fix_estados, use_container_width=True)

# =============================
# Gráfico 2 - Por Causa
# =============================
st.subheader("Principais Causas de Acidentes")

causa = acidentes_por_causa(data_frame)

fig_causa = px.bar(
    x=causa.values,
    y=causa.index,
    orientation="h"
)
st.plotly_chart(fig_causa, use_container_width=True)

# =============================
# Gráfico 3 - Por Hora
# =============================
st.subheader("Acidentes por Hora do Dia")

hora = acidentes_por_hora(data_frame)
fig_hora = px.line(
    x=hora.index,
    y=hora.values,
    labels={'x': 'Hora do Dia', 'y': 'Número de Acidentes'},
    title="Número de Acidentes por Hora do Dia"
)
st.plotly_chart(fig_hora, use_container_width=True)

# =============================
# Filtro interativo
# =============================
st.subheader("Filtro por Estado")

estados_selecionados = st.selectbox("Selecione os estados para análise", data_frame['uf'].unique())

df_filtrado = data_frame[data_frame['uf'] == estados_selecionados]

st.write(f"Analisando os dados de acidentes no estado de {estados_selecionados}; {len(df_filtrado):,} acidentes encontrados.")

st.dataframe(df_filtrado.head(50))