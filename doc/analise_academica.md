# Análise Crítica e Recomendações Acadêmicas (Projeto ATNB)

Este documento apresenta uma revisão crítica do projeto **ATNB (Análise de Trânsito Nacional do Brasil)** sob a perspectiva acadêmica de análise de dados e Big Data. O objetivo é validar a consistência metodológica, identificar o que deve ser removido, refinado ou implementado para elevar o rigor científico e o valor analítico do trabalho (ideal para TCC ou publicação científica).

---

## 1. O que não faz sentido na lógica atual (Erros Metodológicos e Limitações)

### ❌ Confusão Conceitual: Mortalidade vs. Letalidade
No arquivo `dashboard.py` (e na agregação da Gold), a variável `taxa_mortalidade` é calculada como:
$$\text{Taxa de Letalidade} = \left( \frac{\text{Total de Óbitos}}{\text{Total de Acidentes}} \right) \times 100$$
*   **Crítica**: Na saúde pública e na epidemiologia (conforme convenção do DataSUS), essa fórmula calcula a **Letalidade** (a proporção de acidentes que resultam em morte).
*   **Correção**: A **Mortalidade** real deve medir o impacto das mortes na população geral do município, sendo calculada como:
    $$\text{Taxa de Mortalidade} = \left( \frac{\text{Total de Óbitos}}{\text{População}} \right) \times 100.000$$
*   **Impacto**: Chamar letalidade de mortalidade é um erro conceitual grave que seria facilmente penalizado por uma banca acadêmica.

### ❌ Análise Temporal Cruzada com Dados Demográficos Estáticos
A base de acidentes (`acidentes2023.csv`) engloba registros históricos de vários anos (2018 a 2025). Contudo, a base de localidade (`Localidade_20260312.csv`) fornece apenas um instantâneo recente da população e da frota.
*   **Crítica**: Ao calcular taxas de acidentes por 100k habitantes para o ano de 2018 usando a população de 2025/2026, introduz-se uma distorção matemática (subestimando a taxa histórica de acidentes, visto que a população de 2018 era menor).
*   **Correção**: O ideal para um projeto de Big Data seria utilizar uma tabela demográfica histórica que permitisse um cruzamento temporal exato por ano ($Ano_{Acidente} = Ano_{Referência}$). Se não houver dados históricos disponíveis, essa limitação metodológica deve ser explicitada no trabalho.

### ❌ Correlação Espúria na Matriz de Pearson
A matriz de correlação calcula a relação linear entre os números absolutos de acidentes, óbitos e feridos por município.
*   **Crítica**: Como municípios têm escalas populacionais vastamente diferentes (ex: São Paulo vs. uma pequena cidade do interior), as variáveis absolutas sempre apresentarão correlação positiva quase perfeita ($r \approx 1$). Isso é conhecido na estatística como **correlação espúria por escala**.
*   **Correção**: Para a matriz de correlação fazer sentido acadêmico, devem-se correlacionar variáveis normalizadas (taxa de acidentes por 100k hab., taxa de letalidade, taxa de motorização da população).

### ❌ Dados Órfãos na Pipeline (Volume de Tráfego)
A pipeline ingere e processa `Volume_trafego_mensal.csv`, salvando-o como `volume_trafego_silver.parquet`. No entanto, esse dado não é consumido pelo dashboard.
*   **Crítica**: Em arquiteturas de Big Data, processar e persistir dados que não geram valor de visualização ou decisão é um desperdício de processamento e armazenamento.
*   **Correção**: Deve-se decidir entre implementar esses dados no Dashboard (ex: plotar fluxo de tráfego vs. acidentes) ou remover essa etapa da pipeline para fins de simplificação e eficiência.

---

## 2. O que deve ser removido ou simplificado

*   **Matriz de Correlação com Valores Absolutos**: Remover os valores absolutos da correlação e substituí-los pelas taxas normalizadas.
*   **Etapas Mortas da Pipeline**: Se o arquivo `Volume_trafego_mensal.csv` (restrito apenas a Fortaleza) não puder ser cruzado nacionalmente com os dados de acidentes de forma coerente, deve ser removido da pipeline.

---

## 3. O que deve ser implementado (Diferenciais Acadêmicos)

### 📊 Correção dos Termos no Dashboard
1.  Renomear a atual `taxa_mortalidade` para **Letalidade (%)**.
2.  Criar a métrica real de **Mortalidade por 100k hab.** utilizando a população do município.

### 📈 Exibição dos Modelos de Machine Learning
Aproveitar o script `src/pipeline/ml.py` que já treina os classificadores (Decision Tree, MLP, SVC). O dashboard deve conter uma aba **"Análise Preditiva"** exibindo:
1.  Métricas de avaliação dos modelos (Acurácia, Precisão, Recall e F1-score).
2.  Gráfico de **Feature Importance** (quais variáveis, como uso de cinto de segurança ou consumo de álcool, mais pesam na gravidade da lesão do envolvido).

### 📐 Unidade Padrão de Severidade (UPS)
Um indicador clássico na engenharia de tráfego. Em vez de ranquear cidades pelo mero volume bruto de acidentes, ranqueá-las pelo custo social e severidade das ocorrências.
$$\text{UPS} = (\text{Óbitos} \times 13) + (\text{Feridos} \times 5) + (\text{Acidentes sem Vítimas} \times 1)$$
*   Isso dará um peso científico muito maior ao ranqueamento dos trechos rodoviários e municípios mais perigosos.

### 🔬 Testes Estatísticos no Gráfico de Dispersão
Na aba de correlação (Dispersão Frota x Acidentes), além de exibir a linha de tendência, é fundamental para o rigor científico exibir:
*   O coeficiente de determinação ($R^2$), indicando a porcentagem de variação explicada.
*   O P-valor, para comprovar a significância estatística da correlação.

---

## 4. Plano de Ação para Implementação

| Etapa | Ação | Arquivos Afetados | Status |
| :--- | :--- | :--- | :--- |
| **1. Correção Conceitual** | Corrigir o termo Letalidade, recalculando a Mortalidade com base em `qtde_habitantes`. | `enrich.py`, `dashboard.py` | 📝 Planejado |
| **2. Limpeza da Pipeline** | Remover a ingestão órfã de volume de tráfego, ou integrá-la ao Dashboard. | `ingestion.py`, `transform.py`, `pipeline.py` | 📝 Planejado |
| **3. Matriz de Correlação** | Atualizar a correlação para usar taxas em vez de totais absolutos. | `enrich.py`, `dashboard.py` | 📝 Planejado |
| **4. Implementação da UPS** | Adicionar o cálculo da Unidade Padrão de Severidade no ranking de municípios. | `enrich.py`, `dashboard.py` | 📝 Planejado |
| **5. Aba de Machine Learning** | Integrar o `ml.py` com o Streamlit para exibir métricas e importâncias das features. | `dashboard.py` | 📝 Planejado |
