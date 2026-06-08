# Relatório Executivo: Decomposição Sazonal do Trânsito Brasileiro

Este relatório traduz os cálculos estatísticos complexos do modelo STL (Seasonal-Trend Decomposition) em *insights* de negócios diretos, usando **os dados reais que estão processados no projeto ATNB**.

> [!NOTE]
> O modelo matemático desmonta o volume total de acidentes de cada mês em três componentes isolados: **Tendência** (crescimento/queda estrutural), **Sazonalidade** (efeito fixo dos meses do ano) e **Resíduos** (eventos atípicos imprevisíveis).

---

## 1. Tendência Histórica (O quadro geral)

A tendência ignora se é época de férias ou chuva; ela mostra o movimento "estrutural" do trânsito.

- **Ponto de Partida (Meados de 2018):** O patamar basal era de aproximadamente **62.900 acidentes/mês**.
- **Cenário Atual (Início de 2025):** A tendência subiu de forma alarmante, alcançando um patamar basal de **98.300 acidentes/mês**.

> [!CAUTION]
> **Conclusão de Tendência:** Há um forte e constante agravamento na segurança viária nacional. Independentemente da época do ano, o volume base de acidentes aumentou em mais de 50% entre 2018 e 2025.

---

## 2. A Sazonalidade (O DNA do Trânsito Anual)

O algoritmo calculou com exatidão o "peso" de cada mês na quantidade de acidentes. Mesmo se o trânsito parar de piorar em sua tendência, os meses do ano sempre aplicarão os seguintes "bônus" ou "descontos":

### 🔴 Os Meses de Maior Risco (Picos Sazonais)
Estes meses adicionam milhares de acidentes a mais do que o "normal":
1. **Outubro:** O pior mês estatisticamente. O mero fato de estarmos em Outubro adiciona **+4.384 acidentes** à conta nacional.
2. **Dezembro:** Devido às festas de fim de ano, adiciona **+3.933 acidentes**.
3. **Agosto:** Adiciona **+2.978 acidentes**.

### 🟢 Os Meses de Menor Risco (Vales Sazonais)
1. **Janeiro:** Historicamente, retira **-4.449 acidentes** da média.
2. **Abril:** Retira **-3.927 acidentes**.
3. **Fevereiro:** Retira **-2.921 acidentes**.

---

## 3. Anomalias (Resíduos Extremos)

Os resíduos são a diferença que sobrou depois que descontamos a Tendência e a Sazonalidade. Quando um resíduo é enorme (anomalia), significa que **algum evento histórico extremo aconteceu naquele mês**.

A inteligência estatística identificou anomalias gravíssimas no seu banco de dados:

* **Fevereiro de 2020 (+11.412 acidentes extras):** Uma explosão anormal de acidentes que não era esperada pela tendência nem pela sazonalidade. *(Hipótese: Último grande Carnaval pré-pandemia com recorde de viagens)*.
* **Abril de 2020 (-21.347 acidentes da média):** A maior queda de toda a série histórica. 
* **Maio de 2020 (-13.634 acidentes da média):** Continuação da queda.

> [!TIP]
> O modelo detectou perfeitamente e isolou matematicamente o **Efeito dos Lockdowns da COVID-19**. O mês de Abril de 2020 não caiu apenas porque Abril é um mês calmo; a estatística prova que houve uma anomalia externa colossal que retirou mais de 21 mil acidentes das estradas além do normal.

---
**Como isso ajuda no seu trabalho?** 
Ao invés de apenas mostrar um gráfico de linha sobe e desce, você pode usar esses dados exatos para provar que a queda em 2020 foi um evento "anômalo/residual" de causa externa (pandemia) e que, estruturalmente, o trânsito do Brasil está piorando (tendência em alta) com maior periculosidade sistemática no mês de Outubro.
