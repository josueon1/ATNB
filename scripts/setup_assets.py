"""
Baixa e prepara assets estáticos necessários ao dashboard.

Uso:
    python scripts/setup_assets.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
GEOJSON_PATH = ROOT / "data" / "geojson" / "br_states.json"

GEOJSON_URL = (
    "https://raw.githubusercontent.com/codeforgermany/click_that_hood"
    "/master/public/data/brazil-states.geojson"
)


def fetch_br_states_geojson() -> dict:
    """Baixa GeoJSON dos estados e normaliza a propriedade SIGLA."""
    response = requests.get(GEOJSON_URL, timeout=120)
    response.raise_for_status()
    geojson = response.json()

    for feature in geojson.get("features", []):
        props = feature.setdefault("properties", {})
        sigla = props.get("SIGLA") or props.get("sigla") or props.get("abbrev")
        if sigla:
            props["SIGLA"] = str(sigla).upper()

    features = [f for f in geojson.get("features", []) if f["properties"].get("SIGLA")]
    if len(features) < 27:
        raise RuntimeError(f"GeoJSON incompleto: apenas {len(features)} estados com SIGLA")

    geojson["features"] = features
    return geojson


def main() -> None:
    GEOJSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Baixando GeoJSON dos estados para {GEOJSON_PATH}")
    geojson = fetch_br_states_geojson()
    with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"OK: {len(geojson['features'])} estados salvos.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)
