# Fluxo da Aplicação — ATNB

## Visão Geral

A aplicação tem dois pontos de entrada independentes:

1. **Pipeline** (`src/pipeline/pipeline.py`) — processa os CSVs brutos e gera arquivos Parquet
2. **Dashboard** (`app/dashboard.py`) — lê os Parquets gerados e exibe a análise no navegador

O pipeline **precisa rodar primeiro**. O dashboard **depende** dos arquivos que o pipeline produz.

---

## 1. Pipeline de Dados

**Como executar:**
```
python -m src.pipeline.pipeline --skip-heavy
```

**Ponto de entrada:** `src/pipeline/pipeline.py` → função `run_pipeline()`

O pipeline segue a arquitetura **Medallion (Bronze → Silver → Gold)**:

```
pipeline.py
│
├── [BRONZE] Ingestão — src/pipeline/ingestion.py
│   ├── ingest_acidentes()       lê  data/acidentes2023.csv                  (8.2M linhas)
│   ├── ingest_vitimas()         lê  data/Vitimas_DadosAbertos_20260312.csv  (12.5M linhas)
│   ├── ingest_localidade()      lê  data/Localidade_20260312.csv            (531k linhas)
│   ├── ingest_volume_trafego()  lê  data/Volume_trafego_mensal.csv          (26k linhas)
│   └── ingest_tipo_veiculo()    lê  data/TipoVeiculo_DadosAbertos_20260312.csv  (310 MB, opcional)
│
├── [SILVER] Transformação — src/pipeline/transform.py
│   ├── transform_acidentes()    limpa tipos, extrai hora (HHMMSS→int), valida coordenadas
│   ├── transform_vitimas()      normaliza strings, cria flag_obito
│   ├── transform_localidade()   deduplica por chv_localidade, calcula taxa_motorizacao
│   ├── transform_volume_trafego()  normaliza colunas
│   └── transform_tipo_veiculo() (se não --skip-heavy)
│
├── [SILVER] Persistência — src/pipeline/persist.py
│   ├── save_localidade_silver()     → data/processed/localidade_silver.parquet
│   ├── save_vitimas_silver()        → data/processed/vitimas_silver/          (particionado por ano)
│   ├── save_volume_trafego_silver() → data/processed/volume_trafego_silver.parquet
│   └── save_tipo_veiculo_silver()   → data/processed/tipo_veiculo_silver.parquet  (se disponível)
│
├── [GOLD] Enriquecimento — src/pipeline/enrich.py
│   ├── enrich_acidentes_localidade()      JOIN acidentes + localidade via chv_localidade
│   ├── aggregate_vitimas_por_acidente()   GROUP BY num_acidente → contagens por gravidade
│   ├── aggregate_veiculos_por_acidente()  GROUP BY num_acidente → tipo predominante
│   ├── build_acidentes_gold()             une os três datasets acima em um só
│   ├── build_ranking_locais()             ranking de municípios com taxa por 100k hab.
│   ├── build_analise_temporal()           distribuições por ano/mês/hora/dia da semana
│   └── build_correlacao_frota_acidentes() correlação entre frota e acidentes
│
└── [GOLD] Persistência — src/pipeline/persist.py
    ├── save_acidentes_gold()    → data/processed/acidentes_gold/  (particionado por ano e UF)
    ├── save_ranking_locais()    → data/processed/ranking_locais.parquet
    ├── save_analise_temporal()  → data/processed/analise_temporal/*.parquet
    └── save_correlacao_frota()  → data/processed/correlacao_frota_acidentes.parquet
```

**Chave de junção entre tabelas:** `chv_localidade`
- Formato: `{UF}{codigo_ibge}{YYYYMM}` (ex: `AC1200401201801`)
- Presente em acidentes, vítimas e localidade

**Argumentos da linha de comando:**
| Argumento       | Efeito                                          |
|-----------------|-------------------------------------------------|
| `--skip-heavy`  | Pula o TipoVeiculo (310 MB), execução mais rápida |
| `--ano 2023`    | Processa somente o ano informado                |

---

## 2. Dashboard

**Como executar:**
```
streamlit run app/dashboard.py
```

**Ponto de entrada:** `app/dashboard.py`

```
dashboard.py
│
├── Importa src/pipeline/persist.py → load_parquet()
│
├── Verifica se data/processed/ existe (senão exibe erro e para)
│
├── Carrega dados (com cache do Streamlit):
│   ├── load_ranking()    → lê ranking_locais.parquet
│   ├── load_temporal()   → lê analise_temporal/*.parquet
│   └── load_correlacao() → lê correlacao_frota_acidentes.parquet
│
├── Sidebar: filtros por Ano, UF e Top N municípios
│
└── Seções do dashboard:
    ├── KPIs principais (total acidentes, óbitos, municípios, taxa mortalidade)
    ├── Top N municípios — gráfico de barras
    ├── Taxa por 100k hab. — heatbar
    ├── Evolução temporal — barras + linha (ano/mês)
    ├── Distribuição por hora, dia da semana e fase do dia
    ├── Correlação frota × acidentes — scatter plot
    └── Tabela completa do ranking
```

---

## 3. Ordem de Execução

O pipeline **precisa rodar antes** do dashboard. Após isso, o dashboard é a única interface necessária:

```
pipeline.py  →  gera Parquets em data/processed/
                        ↓
               dashboard.py  (única interface de análise)
```

---

## 4. Estrutura de Arquivos

```
ATNB/
├── app/
│   └── dashboard.py              ← ponto de entrada do dashboard (Streamlit)
├── src/
│   └── pipeline/
│       ├── __init__.py
│       ├── pipeline.py           ← ponto de entrada do pipeline (orquestrador)
│       ├── ingestion.py          ← camada Bronze: leitura dos CSVs
│       ├── transform.py          ← camada Silver: limpeza e tipagem
│       ├── enrich.py             ← camada Gold: cruzamento e análises
│       └── persist.py            ← leitura e escrita de Parquet
├── data/
│   ├── acidentes2023.csv         ← CSV bruto (não versionado no git)
│   ├── Vitimas_*.csv             ← CSV bruto (não versionado no git)
│   ├── Localidade_*.csv          ← CSV bruto (não versionado no git)
│   ├── TipoVeiculo_*.csv         ← CSV bruto (não versionado no git)
│   ├── Volume_trafego_mensal.csv ← CSV bruto (não versionado no git)
│   └── processed/                ← saída do pipeline (Parquet, não versionado)
├── requirements.txt
└── README.md
```

---

## 5. Como Executar

```
1. (uma vez) Instalar dependências:
   pip install -r requirements.txt

2. Executar o pipeline (gera os Parquets):
   python -m src.pipeline.pipeline --skip-heavy

3. Iniciar o dashboard:
   streamlit run app/dashboard.py
```
