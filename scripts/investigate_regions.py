import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

PROCESSED_DIR = Path("d:/projetos/ATNB/data/processed")

# Mapeamento de UFs para Regiões
uf_to_regiao = {
    'AC': 'Norte', 'AP': 'Norte', 'AM': 'Norte', 'PA': 'Norte', 'RO': 'Norte', 'RR': 'Norte', 'TO': 'Norte',
    'AL': 'Nordeste', 'BA': 'Nordeste', 'CE': 'Nordeste', 'MA': 'Nordeste', 'PB': 'Nordeste', 'PE': 'Nordeste', 'PI': 'Nordeste', 'RN': 'Nordeste', 'SE': 'Nordeste',
    'DF': 'Centro-Oeste', 'GO': 'Centro-Oeste', 'MT': 'Centro-Oeste', 'MS': 'Centro-Oeste',
    'ES': 'Sudeste', 'MG': 'Sudeste', 'RJ': 'Sudeste', 'SP': 'Sudeste',
    'PR': 'Sul', 'RS': 'Sul', 'SC': 'Sul'
}

def investigate_regions():
    print("Carregando dados regionais...")
    table = pq.read_table(
        str(PROCESSED_DIR / "acidentes_gold"),
        columns=["uf_acidente", "mes_acidente", "cond_meteorologica", "cond_pista", "tp_acidente"]
    )
    df = table.to_pandas()
    df["regiao"] = df["uf_acidente"].map(uf_to_regiao)
    
    # Descobrir o mês de pico por região
    print("\n--- Mês de Pico por Região ---")
    picos = {}
    for regiao in df["regiao"].dropna().unique():
        df_reg = df[df["regiao"] == regiao]
        meses = df_reg["mes_acidente"].value_counts().sort_index()
        mes_pico = meses.idxmax()
        total_pico = meses.max()
        picos[regiao] = mes_pico
        print(f"Região: {regiao} -> Mês de Pico: {mes_pico} ({total_pico} acidentes)")
        
        # Comparar fator no mês de pico vs resto do ano para a região
        df_reg_pico = df_reg[df_reg["mes_acidente"] == mes_pico]
        df_reg_resto = df_reg[df_reg["mes_acidente"] != mes_pico]
        
        # Cond. Meteorologica
        chuva_pico = (df_reg_pico["cond_meteorologica"] == "CHUVA").mean() * 100
        chuva_resto = (df_reg_resto["cond_meteorologica"] == "CHUVA").mean() * 100
        
        # Cond. Pista
        molhada_pico = (df_reg_pico["cond_pista"] == "MOLHADA").mean() * 100
        molhada_resto = (df_reg_resto["cond_pista"] == "MOLHADA").mean() * 100
        
        # Colisão
        tp_top = df_reg_pico["tp_acidente"].value_counts(normalize=True).index[0]
        tp_pico = (df_reg_pico["tp_acidente"] == tp_top).mean() * 100
        tp_resto = (df_reg_resto["tp_acidente"] == tp_top).mean() * 100
        
        print(f"  Fatores no Pico vs Resto do ano:")
        print(f"    Chuva: {chuva_pico:.1f}% vs {chuva_resto:.1f}%")
        print(f"    Pista Molhada: {molhada_pico:.1f}% vs {molhada_resto:.1f}%")
        print(f"    Tipo Principal ({tp_top}): {tp_pico:.1f}% vs {tp_resto:.1f}%")

if __name__ == "__main__":
    investigate_regions()
