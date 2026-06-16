import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

PROCESSED_DIR = Path("d:/projetos/ATNB/data/processed")

def investigate_october():
    print("Carregando acidentes_gold...")
    # Lendo colunas relevantes para entender a causa
    table = pq.read_table(
        str(PROCESSED_DIR / "acidentes_gold"),
        columns=[
            "mes_acidente", "qtde_acidente", "qtde_obitos",
            "cond_meteorologica", "cond_pista", "tp_acidente",
            "dia_semana", "uf_acidente"
        ]
    )
    df = table.to_pandas()
    
    print("\n--- Volume Total por Mês ---")
    meses = df.groupby("mes_acidente")["qtde_acidente"].sum().sort_index()
    print(meses)

    print("\n--- Analisando o Mês de Outubro (Mês 10) vs Restante do Ano ---")
    df["is_october"] = df["mes_acidente"] == 10
    
    def print_proportions(col):
        print(f"\nProporção de {col}:")
        prop_oct = df[df["is_october"]][col].value_counts(normalize=True).head(5) * 100
        prop_other = df[~df["is_october"]][col].value_counts(normalize=True).head(5) * 100
        
        comp = pd.DataFrame({"Outubro (%)": prop_oct, "Outros Meses (%)": prop_other})
        comp["Diferença (%)"] = comp["Outubro (%)"] - comp["Outros Meses (%)"]
        print(comp.sort_values("Diferença (%)", ascending=False))

    print_proportions("cond_meteorologica")
    print_proportions("cond_pista")
    print_proportions("tp_acidente")
    print_proportions("dia_semana")
    print_proportions("uf_acidente")
    
if __name__ == "__main__":
    investigate_october()
