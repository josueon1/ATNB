import sys
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
import holidays

ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

def run():
    print("Carregando acidentes_gold...")
    # Lendo acidentes_gold, precisamos apenas das datas e quantidades
    table = pq.read_table(
        str(PROCESSED_DIR / "acidentes_gold"),
        columns=["data_acidente", "qtde_acidente", "qtde_obitos"]
    )
    df = table.to_pandas()
    df["data_acidente"] = pd.to_datetime(df["data_acidente"], errors="coerce").dt.date
    df = df.dropna(subset=["data_acidente"])
    
    # Agrupar por dia para ter os totais diários no Brasil todo
    diario = df.groupby("data_acidente").agg(
        total_acidentes=("qtde_acidente", "sum"),
        total_obitos=("qtde_obitos", "sum")
    ).reset_index()
    
    # Obter anos únicos para gerar o calendário
    anos = pd.DatetimeIndex(diario["data_acidente"]).year.unique().tolist()
    br_holidays = holidays.BR(years=anos)
    
    # Vamos expandir "Feriadão" e Carnaval manualmente
    # O pacote holidays geralmente traz Carnaval, mas o período de Carnaval no trânsito (Operação Carnaval PRF) 
    # costuma ir de sexta a quarta de cinzas.
    
    def get_tipo_dia(d):
        if d in br_holidays:
            return "Feriado"
        # Mês de Férias: Dezembro, Janeiro e Julho
        if d.month in [1, 7, 12]:
            return "Férias"
        return "Normal"

    diario["tipo_dia"] = diario["data_acidente"].apply(get_tipo_dia)
    
    # Salvar o dataset analítico diário
    out_dir = PROCESSED_DIR / "analise_temporal"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "feriados_diario.parquet"
    diario.to_parquet(out_path, index=False)
    
    print(f"Salvo em {out_path} com {len(diario)} dias processados.")
    
    # Mostrar resumo
    resumo = diario.groupby("tipo_dia").agg(
        media_acidentes_dia=("total_acidentes", "mean"),
        media_obitos_dia=("total_obitos", "mean"),
        dias=("data_acidente", "count")
    )
    print("\nResumo das médias:")
    print(resumo)

if __name__ == "__main__":
    run()
