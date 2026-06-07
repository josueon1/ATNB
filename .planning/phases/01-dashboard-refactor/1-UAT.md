---
status: complete
phase: 01-dashboard-refactor
source: [session-context]
started: 2026-05-16
updated: 2026-06-05
---

## Tests

### 1. Cold Start — Dashboard carrega sem erros
expected: Página carrega em localhost:8501 sem traceback. 4 tabs visíveis.
result: passed

### 2. Mapa estadual — sem filtro de UF
expected: |
  Com nenhuma UF selecionada na sidebar, a aba "Visão Geral" exibe um mapa
  choropleth colorido com todos os estados do Brasil. Passando o cursor sobre
  um estado aparece o tooltip com Acidentes, Óbitos e Mortalidade.
result: passed

### 3. Mapa municipal — com UF selecionada
expected: |
  Ao selecionar uma UF (ex: SP) na sidebar, o mapa muda para scatter_mapbox
  com bolhas por município. O mapa fica centralizado e com zoom no estado
  selecionado. Cada bolha tem tamanho e cor proporcionais à métrica escolhida.
result: passed

### 4. Radio de métrica — troca de métrica atualiza mapa
expected: |
  Clicar em "Total de Óbitos" ou "Taxa de Mortalidade (%)" no radio acima do
  mapa atualiza imediatamente as cores/tamanhos do mapa sem recarregar a página.
result: passed

### 5. Aba Temporal — filtros reagem
expected: |
  Selecionar um ano (ex: 2023) e/ou UF na sidebar e ir para a aba
  "Evolução Temporal". O banner azul de info aparece indicando os filtros ativos.
  Os gráficos de Mês, Hora e Dia da Semana exibem dados somente do período/UF filtrado.
result: passed

### 6. Aba Temporal — sem filtros mostra histórico completo
expected: |
  Com "Todos" selecionado e sem UF, a aba Temporal exibe a legenda
  "Exibindo dados históricos completos" e os gráficos mostram todos os anos/UFs.
result: passed

### 7. Aba Correlação — matriz e gráficos visíveis
expected: |
  A aba "Correlação & Indicadores" exibe: matriz de correlação, scatter
  frota×acidentes com linha de tendência OLS, e box plot de taxa/100k por UF.
result: passed

### 8. Aba Fatores — requer seleção de UF
expected: |
  Sem UF selecionada, a aba "Fatores & Causas" exibe mensagem pedindo para
  selecionar pelo menos uma UF. Com UF selecionada, exibe KPIs e gráficos.
result: passed

## Summary

total: 8
passed: 8
issues: 0

## Decisions
- Aba "Machine Learning" removida do dashboard (2026-06-05)
  - src/pipeline/ml.py adicionado ao .gitignore
  - scikit-learn removido do requirements.txt
  - Estilo visual dos mapas (choropleth + scatter_mapbox) mantido
pending: 9
skipped: 0

## Gaps

[none yet]
