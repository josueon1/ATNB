# 🚗 Análise de Dados de Trânsito no Brasil

## 📌 Objetivo

Este projeto tem como objetivo analisar dados públicos de trânsito no Brasil utilizando técnicas de Big Data com Python.

A análise busca identificar padrões relacionados a:

* acidentes de trânsito
* distribuição geográfica
* causas de acidentes
* horários com maior incidência

---

## 📊 Fonte dos Dados

Os dados utilizados são provenientes de bases públicas:

* Polícia Rodoviária Federal (PRF)
* SENATRAN (Secretaria Nacional de Trânsito)
* Portal Brasileiro de Dados Abertos

Todos os dados são anonimizados e não contêm informações pessoais sensíveis.

---

## 🛠️ Tecnologias Utilizadas

* Python 3
* Pandas
* NumPy
* Plotly
* Streamlit

---

## 📁 Estrutura do Projeto

data/ → datasets utilizados
notebooks/ → análise exploratória
src/ → scripts de processamento
app/ → dashboard interativo

---

## 🔍 Etapas do Projeto

1. Coleta de dados públicos
2. Limpeza e tratamento dos dados
3. Análise exploratória
4. Cruzamento de dados
5. Visualização de dados
6. Criação de dashboard

---

## 📈 Visualizações

O projeto apresenta:

* gráficos de acidentes por estado
* análise por horário
* principais causas de acidentes
* distribuição geográfica

Todos os gráficos são interativos e executados no navegador.

---

## ▶️ Como Executar

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Rodar a Pipeline de Dados

Executa as camadas Bronze → Silver → Gold → Parquet:

```bash
python -m src.pipeline.pipeline
```

Opções disponíveis:

```bash
# Pula o arquivo TipoVeiculo (310 MB) para execução mais rápida
python -m src.pipeline.pipeline --skip-heavy

# Processa apenas um ano específico
python -m src.pipeline.pipeline --ano 2023
```

### 3. Rodar o Dashboard

```bash
streamlit run app/dashboard.py
```

---

## 🎯 Resultados Esperados

* Identificar regiões com maior número de acidentes
* Entender os principais fatores de risco
* Analisar padrões de comportamento no trânsito

---

## 👨‍💻 Autor

Projeto acadêmico desenvolvido para disciplina de Big Data em Python.

Fábio Macieira
Josué Ferreira
Victor Martins


## Como rodar o projeto

### Criando o ambiente virtual

```bash
python -m venv .venv
```

### Ativando o ambiente

```bash
# Windows
.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate
```

### Instalar as dependências

```bash
pip install -r requirements.txt
```

### Rodar a pipeline

```bash
python -m src.pipeline.pipeline
```

### Rodar o dashboard

```bash
streamlit run app/dashboard.py
```

### Desativar o ambiente quando terminar

```bash
deactivate
```