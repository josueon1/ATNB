import pyarrow.parquet as pq
import pandas as pd
from pathlib import Path
import os

print("Lendo vitimas_silver...")
# vitimas_silver tem num_acidente, qtde_obitos, ano_acidente, mes_acidente
t = pq.read_table(
    'data/processed/vitimas_silver',
    columns=['num_acidente', 'qtde_obitos', 'ano_acidente', 'mes_acidente']
)
df = t.to_pandas()

print("Agregando por acidente...")
# Cada acidente pode ter múltiplas vítimas, mas o num_acidente é único por acidente
# A quantidade de óbitos por acidente é o máximo de qtde_obitos associado àquele acidente ou a soma de flag_obito?
# Na verdade qtde_obitos já é repetido em todas as linhas daquele acidente.
# Vamos agrupar por num_acidente primeiro para não duplicar acidentes
df_acid = df.groupby('num_acidente', as_index=False).agg({
    'ano_acidente': 'first',
    'mes_acidente': 'first',
    'qtde_obitos': 'first'
})

print("Agregando por ano e mes...")
# Agora agrupamos por ano e mes
agg = df_acid.groupby(['ano_acidente', 'mes_acidente']).agg(
    total_acidentes=('num_acidente', 'count'),
    total_obitos=('qtde_obitos', 'sum')
).reset_index()

# Ordenar cronologicamente
agg = agg.sort_values(['ano_acidente', 'mes_acidente']).reset_index(drop=True)

# Criar coluna de data para facilitar o index temporal
agg['data'] = pd.to_datetime(agg['ano_acidente'].astype(str) + '-' + agg['mes_acidente'].astype(str).str.zfill(2) + '-01')

print("Salvando...")
os.makedirs('data/processed/analise_temporal', exist_ok=True)
agg.to_parquet('data/processed/analise_temporal/por_ano_mes.parquet')
print("Salvo em data/processed/analise_temporal/por_ano_mes.parquet com sucesso!")
print(agg.head())
