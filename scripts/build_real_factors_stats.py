import os
import sys
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = PROCESSED_DIR / "analise_temporal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_PISTA_MOLHADA = ["MOLHADA", "ESCORREGADIA"]
_COND_METEO_ADVERSA = [
    "CHUVA", "NUBLADO", "GAROACHUVISCO",
    "NEVOEIRO  NEVOA OU FUMACA", "VENTOS FORTES", "NEVE", "GRANIZO",
]

def main():
    print("Carregando base de acidentes...")
    table = pq.read_table(
        str(PROCESSED_DIR / "acidentes_gold"),
        columns=[
            "qtde_acidente", "qtde_obitos", "vitimas_com_alcool", "cond_pista",
            "cond_meteorologica", "fase_dia", "dia_semana"
        ]
    )
    df = table.to_pandas()
    print(f"Base carregada: {len(df):,} linhas.")

    # Flag de fatalidade (pelo menos 1 óbito no acidente)
    df["is_fatal"] = (df["qtde_obitos"] > 0).astype(int)
    
    # Mapeamento dos fatores
    df["is_alcool"] = (df["vitimas_com_alcool"] > 0).astype(int)
    df["is_pista_molhada"] = df["cond_pista"].isin(_PISTA_MOLHADA).astype(int)
    df["is_chuva"] = df["cond_meteorologica"].isin(_COND_METEO_ADVERSA).astype(int)
    df["is_buraco"] = (df["cond_pista"] == "COM BURACO").astype(int)
    df["is_noite"] = df["fase_dia"].isin(["NOITE", "MADRUGADA"]).astype(int)
    df["is_fim_de_semana"] = df["dia_semana"].isin(["SABADO", "DOMINGO"]).astype(int)

    features = {
        "is_alcool": "Suspeita de Alcoolismo",
        "is_pista_molhada": "Pista Molhada",
        "is_chuva": "Tempo Adverso / Chuva",
        "is_buraco": "Pista com Buracos",
        "is_noite": "Período Noturno",
        "is_fim_de_semana": "Finais de Semana"
    }

    # Estatísticas Gerais (Baseline)
    total_acidentes_geral = int(df["qtde_acidente"].sum())
    total_obitos_geral = int(df["qtde_obitos"].sum())
    total_fatais_geral = int(df["is_fatal"].sum())
    letalidade_geral = (total_fatais_geral / total_acidentes_geral) * 100

    print(f"Letalidade Geral do País: {letalidade_geral:.4f}%")

    res = []
    for var, label in features.items():
        sub_df = df[df[var] == 1]
        
        acidentes = int(sub_df["qtde_acidente"].sum())
        obitos = int(sub_df["qtde_obitos"].sum())
        fatais = int(sub_df["is_fatal"].sum())
        letalidade = (fatais / acidentes * 100) if acidentes > 0 else 0.0
        
        # Aumento em relação à média geral
        aumento_relativo = (letalidade / letalidade_geral) if letalidade_geral > 0 else 1.0

        res.append({
            "fator": label,
            "var_name": var,
            "total_acidentes": acidentes,
            "total_obitos": obitos,
            "acidentes_fatais": fatais,
            "letalidade_pct": letalidade,
            "aumento_relativo": aumento_relativo,
            # Metadados de baseline
            "total_acidentes_geral": total_acidentes_geral,
            "total_obitos_geral": total_obitos_geral,
            "total_fatais_geral": total_fatais_geral,
            "letalidade_geral_pct": letalidade_geral
        })

    summary_df = pd.DataFrame(res)
    
    # Salvar em arquivo Parquet
    output_path = OUTPUT_DIR / "real_factors_stats.parquet"
    summary_df.to_parquet(output_path, index=False)
    print(f"Resultados de dados reais salvos em: {output_path}")

if __name__ == "__main__":
    main()
