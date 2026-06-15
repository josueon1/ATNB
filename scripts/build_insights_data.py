import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

PROCESSED_DIR = Path("d:/projetos/ATNB/data/processed")

def run():
    print("Carregando acidentes_gold...")
    table = pq.read_table(
        str(PROCESSED_DIR / "acidentes_gold"),
        columns=["mes_acidente", "cond_pista", "uf_acidente", "tp_acidente"]
    )
    df = table.to_pandas()
    
    df["periodo"] = df["mes_acidente"].apply(lambda x: "Outubro" if x == 10 else "Resto do Ano")
    
    # 1. Pista Molhada
    pista = df.groupby(["periodo", "cond_pista"]).size().unstack(fill_value=0)
    pista_pct = pista.div(pista.sum(axis=1), axis=0) * 100
    df_pista = pista_pct[["MOLHADA"]].reset_index().rename(columns={"MOLHADA": "pct_molhada"})
    
    # 2. Santa Catarina (SC)
    uf = df.groupby(["periodo", "uf_acidente"]).size().unstack(fill_value=0)
    uf_pct = uf.div(uf.sum(axis=1), axis=0) * 100
    df_sc = uf_pct[["SC"]].reset_index().rename(columns={"SC": "pct_sc"})
    
    # Consolidar em um dict de dataframes e salvar
    out_dir = PROCESSED_DIR / "analise_temporal"
    df_pista.to_parquet(out_dir / "insight_pista_molhada.parquet", index=False)
    df_sc.to_parquet(out_dir / "insight_uf_sc.parquet", index=False)
    
    print("Dados de insights salvos com sucesso!")

if __name__ == "__main__":
    run()
