import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import statsmodels.api as sm

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
            "qtde_obitos", "vitimas_com_alcool", "cond_pista",
            "cond_meteorologica", "fase_dia", "dia_semana"
        ]
    )
    df = table.to_pandas()
    print(f"Base carregada: {len(df):,} linhas.")

    print("Codificando variaveis binarias...")
    df["is_fatal"] = (df["qtde_obitos"] > 0).astype(int)
    df["is_alcool"] = (df["vitimas_com_alcool"] > 0).astype(int)
    df["is_pista_molhada"] = df["cond_pista"].isin(_PISTA_MOLHADA).astype(int)
    df["is_chuva"] = df["cond_meteorologica"].isin(_COND_METEO_ADVERSA).astype(int)
    df["is_buraco"] = (df["cond_pista"] == "COM BURACO").astype(int)
    df["is_noite"] = df["fase_dia"].isin(["NOITE", "MADRUGADA"]).astype(int)
    df["is_fim_de_semana"] = df["dia_semana"].isin(["SABADO", "DOMINGO"]).astype(int)

    features = [
        "is_alcool", "is_pista_molhada", "is_chuva",
        "is_buraco", "is_noite", "is_fim_de_semana"
    ]

    # Remover linhas com valores ausentes
    df_clean = df[["is_fatal"] + features].dropna()
    print(f"Dados limpos para modelagem: {len(df_clean):,} linhas.")

    X = df_clean[features].astype(float)
    y = df_clean["is_fatal"].astype(float)

    # Adicionar constante para o intercepto
    X = sm.add_constant(X)

    print("Ajustando modelo de Regressao Logistica...")
    model = sm.Logit(y, X)
    results = model.fit()

    print(results.summary())

    # Extrair coeficientes e estatisticas
    coef = results.params
    std_err = results.bse
    p_values = results.pvalues
    conf_int = results.conf_int()

    summary_df = pd.DataFrame({
        "var_name": coef.index,
        "coef": coef.values,
        "std_err": std_err.values,
        "p_value": p_values.values,
        "ci_lower": conf_int[0].values,
        "ci_upper": conf_int[1].values
    })

    # Calcular Odds Ratio e seus intervalos de confianca
    summary_df["odds_ratio"] = np.exp(summary_df["coef"])
    summary_df["or_ci_lower"] = np.exp(summary_df["ci_lower"])
    summary_df["or_ci_upper"] = np.exp(summary_df["ci_upper"])

    # Salvar metadados gerais do modelo
    summary_df["pseudo_r2"] = results.prsquared
    summary_df["llf"] = results.llf
    summary_df["llnull"] = results.llnull
    summary_df["nobs"] = results.nobs

    # Salvar em arquivo Parquet
    output_path = OUTPUT_DIR / "regression_results.parquet"
    summary_df.to_parquet(output_path, index=False)
    print(f"Resultados salvos com sucesso em: {output_path}")

if __name__ == "__main__":
    main()
