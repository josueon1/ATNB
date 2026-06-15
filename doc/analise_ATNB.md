# Relatório Consolidado: Análise Nacional de Acidentes de Trânsito no Brasil (ATNB)

Este documento consolida os objetivos, a metodologia, a análise de dados e as conclusões do projeto **ATNB (Análise de Trânsito Nacional do Brasil)**. O trabalho baseia-se em um pipeline de Big Data orquestrado em Python que processou mais de **8,27 milhões de ocorrências** registradas no país entre os anos de 2018 e 2025.

---

## 1. Visão Geral do Projeto

### 📌 Objetivo e Relevância
O trânsito brasileiro é um dos mais violentos do mundo, gerando custos sociais de bilhões de reais e milhares de perdas de vidas anualmente. O objetivo do projeto ATNB é aplicar técnicas modernas de engenharia de dados, Big Data e modelagem estatística para identificar padrões estruturais, sazonalidades temporais e o real impacto dos principais fatores de risco na gravidade física das ocorrências.

### 🛠️ Arquitetura do Pipeline de Dados (Medalhão)
Para dar conta do grande volume de dados (mais de 12 milhões de registros de vítimas e 8 milhões de registros de acidentes), implementamos uma arquitetura de dados organizada em camadas no diretório `data/processed`:
1. **Bronze (Ingestão)**: Leitura otimizada de CSVs brutos em blocos de memória (*chunks*) usando Pandas para conter picos de consumo de RAM.
2. **Silver (Transformação e Padronização)**: Limpeza e tipagem dos campos, normalização de strings, validação geográfica e enriquecimento com flags binárias para análise estatística.
3. **Gold (Cruzamento e Agrupamento)**: União das fontes de acidentes, veículos e vítimas por meio da chave temporal-geográfica `chv_localidade`. Geração das tabelas agregadas e exportação no formato **Parquet** particionado por ano e UF, otimizando o carregamento rápido de dados no Dashboard.

---

## 2. Metodologia Científica e Indicadores

Para elevar o rigor técnico do projeto, as seguintes correções conceituais e métricas de engenharia de tráfego foram implementadas na camada Gold:

### 📐 Unidade Padrão de Severidade (UPS)
Utilizada no ranqueamento dos municípios mais perigosos do país para medir o impacto social de forma ponderada, em vez de focar apenas no volume bruto de acidentes leves. A fórmula adotada no pipeline foi:
$$\text{UPS} = (\text{Total de Óbitos} \times 13) + (\text{Total de Feridos} \times 5)$$

### 📊 Letalidade (%) vs. Mortalidade (por 100k hab.)
*   **Letalidade (%)**: Proporção de acidentes que resultam em morte. Mede a gravidade e o potencial de óbito de cada colisão.
    $$\text{Letalidade} = \left( \frac{\text{Total de Óbitos}}{\text{Total de Acidentes}} \right) \times 100$$
*   **Mortalidade (por 100k hab.)**: Impacto da violência do trânsito na população do município.
    $$\text{Mortalidade} = \left( \frac{\text{Total de Óbitos}}{\text{População}} \right) \times 100.000$$

### 📈 Escala Logarítmica para Evitar Correlação Espúria
Ao correlacionar a frota circulante de cada município com o total de acidentes, aplicamos escala logarítmica em ambos os eixos no gráfico de dispersão. Isso impede que a diferença populacional massiva entre metrópoles e pequenas cidades crie uma correlação linear espúria perfeita ($R \approx 1$), permitindo estimar a verdadeira tendência e calcular a correlação de Pearson ($R²$ e P-valor) de forma precisa.

---

## 3. Análise de Dados e Resultados

### 📈 Decomposição Sazonal (Modelo STL)
A decomposição estatística do volume mensal de acidentes separou os dados reais em três componentes chaves:

1.  **Tendência Estrutural**: Revela um constante agravamento na segurança do trânsito no país. O patamar basal subiu de **62.942 acidentes/mês** em Julho de 2018 para **93.334 acidentes/mês** em Junho de 2025 (um crescimento estrutural de **+48%**).
2.  **Sazonalidade Mensal (DNS do Trânsito)**:
    *   **🔴 Meses de Maior Risco (Picos)**: Outubro (**+4.278 acidentes** acima da média basal) e Dezembro (**+3.828 acidentes**, devido às viagens e feriados de fim de ano).
    *   **🟢 Meses de Menor Risco (Vales)**: Janeiro (**-4.555 acidentes** da média basal) e Abril (**-4.034 acidentes**).
3.  **Isolamento de Anomalias (Resíduos)**:
    *   **Lockdowns da COVID-19**: O modelo STL isolou perfeitamente os efeitos da pandemia em **Abril de 2020 (-21.241 acidentes** extras abaixo do padrão) e **Maio de 2020 (-13.529 acidentes)**.
    *   **Carnaval de 2020**: Detectou-se uma anomalia positiva acentuada em **Fevereiro de 2020 (+11.518 acidentes)**, marcando o último carnaval antes das restrições sanitárias.

### 🔬 Impacto dos Fatores de Risco (Regressão Logística)
Rodamos um modelo de **Regressão Logística** multivariada sobre o histórico de **8,27 milhões de acidentes** para determinar a probabilidade associada de óbito baseado em fatores ambientais e comportamentais ($p < 0.001$):

| Fator de Risco | Odds Ratio (OR) | Significado e Risco Associado |
| :--- | :--- | :--- |
| **🕳️ Pista com Buracos** | **2,92** | Multiplica a chance de óbito no acidente por **2,92x** (risco **+192%** maior). |
| **Nighttime (Noite/Madrugada)** | **1,92** | Multiplica a chance de óbito por **1,92x** (risco **+92%** maior). |
| **Finais de Semana** | **1,67** | Multiplica a chance de óbito por **1,67x** (risco **+67%** maior). |
| **Tempo Adverso (Chuva)** | **1,41** | Multiplica a chance de óbito por **1,41x** (risco **+41%** maior). |

---

## 4. Conclusões e Recomendações

1.  **Aumento Estrutural Preocupante**: O crescimento de quase 50% na base estrutural de acidentes (tendência STL) indica que as políticas públicas atuais de trânsito e engenharia de tráfego são insuficientes para conter o avanço do volume total de veículos.
2.  **Infraestrutura como Maior Agravante**: Pistas degradadas com buracos, embora causem menor número bruto de ocorrências, apresentam a **maior razão de chances de letalidade (OR = 2,92)**. Isso aponta que buracos em alta velocidade em rodovias (onde comumente ocorrem capotamentos e colisões frontais por desvio) são extremamente mortais.
3.  **Políticas Públicas Recomendadas**:
    *   **Manutenção Asfáltica**: Priorização absoluta e imediata de recapeamento asfáltico em rodovias de alta velocidade.
    *   **Fiscalização e Iluminação Noturna**: Reforço de radares de velocidade e iluminação ativa em trechos rodoviários perigosos, mitigando o risco do período noturno (OR = 1,92) e fins de semana (OR = 1,67).
    *   **Campanhas Sazonais**: Concentrar esforços e campanhas educativas e de policiamento em Outubro e Dezembro, os meses historicamente com pior sazonalidade.
