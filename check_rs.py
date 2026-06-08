import pandas as pd

df = pd.read_parquet('data/processed/acidentes_gold')
rs = df[df['uf_acidente'] == 'RS']
print(f"RS Acidentes: {rs['qtde_acidente'].sum()}")
print(f"RS Obitos: {rs['qtde_obitos'].sum()}")
print(f"Letalidade: {(rs['qtde_obitos'].sum() / rs['qtde_acidente'].sum()) * 100:.2f}%")
