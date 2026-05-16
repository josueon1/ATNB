"""Verifica integridade dos dados e dependencias do dashboard ATNB."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline.persist import load_parquet

PROCESSED = ROOT / "data" / "processed"
GEOJSON = ROOT / "data" / "geojson" / "br_states.json"

OK = "\033[32mOK\033[0m"
ERR = "\033[31mERRO\033[0m"
WARN = "\033[33mAVISO\033[0m"

results = []

def check(label, fn):
    try:
        msg = fn()
        results.append((True, label, msg))
        print(f"  [{OK}]  {label:<40} {msg}")
    except Exception as e:
        results.append((False, label, str(e)))
        print(f"  [{ERR}] {label:<40} {e}")

# 1. acidentes_gold
check("acidentes_gold (2023/SP sample)", lambda: (
    lambda df: f"{df.shape[0]:,} rows | cols: {list(df.columns[:6])}"
)(load_parquet(PROCESSED / "acidentes_gold",
    filters=[("ano_acidente", "=", 2023), ("uf_acidente", "in", ["SP"])])))

# 2. analise_temporal
for name in ["por_ano", "por_mes", "por_hora", "por_dia_semana"]:
    n = name
    check(f"analise_temporal/{n}.parquet", lambda n=n: (
        lambda df: f"{df.shape}"
    )(load_parquet(PROCESSED / "analise_temporal" / f"{n}.parquet")))

# 3. vitimas_silver
check("vitimas_silver (2023 sample)", lambda: (
    lambda df: f"{df.shape[0]:,} rows"
)(load_parquet(PROCESSED / "vitimas_silver", filters=[("ano_acidente", "=", 2023)])))

# 4. geojson
def check_geojson():
    with open(GEOJSON, encoding="utf-8") as f:
        gj = json.load(f)
    n = len(gj["features"])
    siglas = [ft["properties"]["SIGLA"] for ft in gj["features"][:3]]
    return f"{n} estados | ex: {siglas}"
check("geojson br_states.json", check_geojson)

# 5. Arquivos opcionais
for name in ["ranking_locais", "correlacao_frota_acidentes"]:
    p = PROCESSED / f"{name}.parquet"
    if p.exists():
        n = name
        check(f"{n}.parquet", lambda n=n: (
            lambda df: f"{df.shape}"
        )(load_parquet(PROCESSED / f"{n}.parquet")))
    else:
        print(f"  [{WARN}] {name}.parquet{'':<28} nao existe (tabs podem estar limitadas)")

# 6. Importacoes Python
def check_imports():
    import streamlit, plotly, pyarrow, sklearn, numpy, pandas
    return (f"streamlit={streamlit.__version__} plotly={plotly.__version__} "
            f"pyarrow={pyarrow.__version__} sklearn={sklearn.__version__}")
check("imports principais", check_imports)

# Resumo
total = len(results)
passed = sum(1 for r in results if r[0])
failed = total - passed
print()
print(f"  Resultado: {passed}/{total} OK", "" if failed == 0 else f"| {failed} ERRO(S)")
sys.exit(0 if failed == 0 else 1)
