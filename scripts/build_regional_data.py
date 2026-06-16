import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

PROCESSED_DIR = Path("d:/projetos/ATNB/data/processed")

uf_to_regiao = {
    'AC': 'Norte', 'AP': 'Norte', 'AM': 'Norte', 'PA': 'Norte', 'RO': 'Norte', 'RR': 'Norte', 'TO': 'Norte',
    'AL': 'Nordeste', 'BA': 'Nordeste', 'CE': 'Nordeste', 'MA': 'Nordeste', 'PB': 'Nordeste', 'PE': 'Nordeste', 'PI': 'Nordeste', 'RN': 'Nordeste', 'SE': 'Nordeste',
    'DF': 'Centro-Oeste', 'GO': 'Centro-Oeste', 'MT': 'Centro-Oeste', 'MS': 'Centro-Oeste',
    'ES': 'Sudeste', 'MG': 'Sudeste', 'RJ': 'Sudeste', 'SP': 'Sudeste',
    'PR': 'Sul', 'RS': 'Sul', 'SC': 'Sul'
}

def run():
    print("Carregando acidentes_gold...")
    table = pq.read_table(
        str(PROCESSED_DIR / "acidentes_gold"),
        columns=["uf_acidente", "mes_acidente", "qtde_acidente", "qtde_obitos"]
    )
    df = table.to_pandas()
    df["regiao"] = df["uf_acidente"].map(uf_to_regiao)
    
    # Agrupar por Regiao e Mes
    agg = df.groupby(["regiao", "mes_acidente"]).agg(
        acidentes=("qtde_acidente", "sum"),
        obitos=("qtde_obitos", "sum")
    ).reset_index()
    
    # Calcular o percentual que cada mês representa no total daquele ano para a região
    # Assim normalizamos o gráfico (evita que o Sudeste esmague as outras regiões visualmente)
    total_regiao = agg.groupby("regiao")["acidentes"].transform("sum")
    agg["pct_acidentes"] = (agg["acidentes"] / total_regiao) * 100
    
    out_dir = PROCESSED_DIR / "analise_temporal"
    out_dir.mkdir(parents=True, exist_ok=True)
    agg.to_parquet(out_dir / "regional_seasonality.parquet", index=False)
    print("Dados regionais salvos com sucesso!")

if __name__ == "__main__":
    run()
