# Relatório Executivo: Decomposição Sazonal do Trânsito Brasileiro

Este relatório traduz os cálculos estatísticos complexos do modelo STL (Seasonal-Trend Decomposition) em *insights* de negócios diretos, usando **os dados reais que estão processados no projeto ATNB**.

> [!NOTE]
> O modelo matemático desmonta o volume total de acidentes de cada mês em três componentes isolados: **Tendência** (crescimento/queda estrutural), **Sazonalidade** (efeito fixo dos meses do ano) e **Resíduos** (eventos atípicos imprevisíveis).

---

## 1. Tendência Histórica (O quadro geral)

A tendência ignora se é época de férias ou chuva; ela mostra o movimento "estrutural" do trânsito.

- **Ponto de Partida (Julho de 2018):** O patamar basal da tendência era de **62.942 acidentes/mês**.
- **Cenário Atual (Junho de 2025):** A tendência subiu de forma alarmante, alcançando um patamar basal de **93.334 acidentes/mês**.

> [!CAUTION]
> **Conclusão de Tendência:** Há um forte e constante agravamento na segurança viária nacional. Independentemente da época do ano, o volume basal mensal de acidentes aumentou em mais de 48% entre 2018 e 2025.

---

## 2. A Sazonalidade (O DNA do Trânsito Anual)

O algoritmo calculou com exatidão o "peso" de cada mês na quantidade de acidentes. Mesmo se o trânsito parar de piorar em sua tendência, os meses do ano sempre aplicarão os seguintes "bônus" ou "descontos":

### 🔴 Os Meses de Maior Risco (Picos Sazonais)
Estes meses adicionam milhares de acidentes a mais do que o "normal":
1. **Outubro:** O pior mês estatisticamente. O mero fato de estarmos em Outubro adiciona **+4.278 acidentes** à conta nacional.
2. **Dezembro:** Devido às festas de fim de ano e feriados, adiciona **+3.828 acidentes**.
3. **Agosto:** Adiciona **+2.872 acidentes**.

### 🟢 Os Meses de Menor Risco (Vales Sazonais)
1. **Janeiro:** Historicamente, retira **-4.555 acidentes** da média basal.
2. **Abril:** Retira **-4.034 acidentes**.
3. **Fevereiro:** Retira **-3.028 acidentes**.

---

## 3. Anomalias (Resíduos Extremos)

Os resíduos são a diferença que sobrou depois que descontamos a Tendência e a Sazonalidade. Quando um resíduo é enorme (anomalia), significa que **algum evento histórico extremo aconteceu naquele mês**.

A inteligência estatística identificou as seguintes anomalias extremas no banco de dados:

* **Fevereiro de 2020 (+11.518 acidentes extras):** Uma explosão anormal de acidentes que não era esperada pela tendência nem pela sazonalidade. *(Hipótese: Último grande Carnaval pré-pandemia com recorde histórico de viagens).*
* **Abril de 2020 (-21.241 acidentes da média):** A maior queda de toda a série histórica. 
* **Maio de 2020 (-13.529 acidentes da média):** Continuação da queda acentuada.

> [!TIP]
> O modelo detectou perfeitamente e isolou matematicamente o **Efeito dos Lockdowns da COVID-19**. O mês de Abril de 2020 não caiu apenas porque Abril é um mês calmo; a estatística prova que houve uma anomalia externa colossal que retirou mais de 21 mil acidentes das estradas além do normal.

---

## 4. Fatores de Risco e Regressão Logística (Rigor Científico)

Para além de decompor a série temporal, rodamos um modelo de **Regressão Logística** sobre todos os **8,27 milhões de acidentes** para calcular o impacto isolado de cada fator na ocorrência de **óbito (sinistro fatal)**. O modelo gerou a **Razão de Chances (Odds Ratio - OR)** para cada variável ($p < 0.001$ em todas):

| Fator de Risco | Odds Ratio (OR) | Significado e Aumento nas Chances de Óbito |
| :--- | :--- | :--- |
| **🕳️ Pista com Buracos** | **2,92** | Multiplica a chance de morte no acidente por **2,92x** (aumento de **+192%**). É o fator estrutural individual mais letal. |
| **🌃 Período Noturno** | **1,92** | Multiplica a chance de morte por **1,92x** (aumento de **+92%**), refletindo riscos de visibilidade e velocidade. |
| **📅 Finais de Semana** | **1,67** | Multiplica a chance de morte por **1,67x** (aumento de **+67%**). |
| **🌧️ Tempo Adverso / Chuva** | **1,41** | Multiplica a chance de morte por **1,41x** (aumento de **+41%**). |

*Nota metodológica: Variáveis como Suspeita de Álcool e Pista Molhada apresentaram odds ratio inferior a 1 no modelo multivariado conjunto devido a forte multicolinearidade com Período Noturno, Finais de Semana e Chuva, devendo ser interpretadas em suas taxas brutas univariadas no dashboard.*

---
**Como isso ajuda no seu trabalho?** 
Ao invés de apenas mostrar um gráfico de linha sobe e desce, você pode usar esses dados exatos para provar que a queda em 2020 foi um evento "anômalo/residual" de causa externa (pandemia) e que, estruturalmente, o trânsito do Brasil está piorando (tendência em alta) com maior periculosidade sistemática no mês de Outubro, sendo o buraco na pista o maior agravante de letalidade.
