"""
Orquestrador do Pipeline de Dados - ATNB
==========================================
Executa as camadas em ordem:
  Bronze → Silver → Gold → Parquet

Uso:
    python -m src.pipeline.pipeline
    python -m src.pipeline.pipeline --skip-heavy   # pula TipoVeiculo (310 MB)
    python -m src.pipeline.pipeline --ano 2023     # filtra por ano

Logs de progresso são exibidos no terminal com timestamp.
"""

import argparse
import logging
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"


def run_pipeline(skip_heavy: bool = False, ano_filtro: int | None = None) -> None:
    from src.pipeline import ingestion, transform, enrich, persist

    t0 = time.time()
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE DE DADOS ATNB")
    logger.info("  data_dir    : %s", DATA_DIR)
    logger.info("  processed   : %s", PROCESSED_DIR)
    logger.info("  skip_heavy  : %s", skip_heavy)
    logger.info("  ano_filtro  : %s", ano_filtro or "todos")
    logger.info("=" * 60)

    # ── BRONZE: Ingestão ──────────────────────────────────────────────────
    logger.info("[BRONZE] Ingestão dos dados brutos...")

    df_acidentes_raw = ingestion.ingest_acidentes(DATA_DIR)
    df_vitimas_raw = ingestion.ingest_vitimas(DATA_DIR)
    df_localidade_raw = ingestion.ingest_localidade(DATA_DIR)
    df_volume_raw = ingestion.ingest_volume_trafego(DATA_DIR)

    df_tipo_veiculo_raw = None
    if not skip_heavy:
        df_tipo_veiculo_raw = ingestion.ingest_tipo_veiculo(DATA_DIR)

    # ── SILVER: Transformação ─────────────────────────────────────────────
    logger.info("[SILVER] Transformação e limpeza dos dados...")

    df_acidentes = transform.transform_acidentes(df_acidentes_raw)
    del df_acidentes_raw

    df_vitimas = transform.transform_vitimas(df_vitimas_raw)
    del df_vitimas_raw

    df_localidade = transform.transform_localidade(df_localidade_raw)
    del df_localidade_raw

    df_volume = transform.transform_volume_trafego(df_volume_raw)
    del df_volume_raw

    df_tipo_veiculo = None
    if df_tipo_veiculo_raw is not None:
        df_tipo_veiculo = transform.transform_tipo_veiculo(df_tipo_veiculo_raw)
        del df_tipo_veiculo_raw

    # Filtro por ano (opcional)
    if ano_filtro:
        logger.info("  Filtrando por ano %d...", ano_filtro)
        df_acidentes = df_acidentes[df_acidentes["ano_acidente"] == ano_filtro].copy()
        df_vitimas = df_vitimas[df_vitimas["ano_acidente"] == ano_filtro].copy()
        if df_tipo_veiculo is not None:
            ids_filtrados = set(df_acidentes["num_acidente"].unique())
            df_tipo_veiculo = df_tipo_veiculo[
                df_tipo_veiculo["num_acidente"].isin(ids_filtrados)
            ].copy()

    # Persistir camada Silver
    logger.info("[SILVER] Persistindo camada Silver...")
    persist.save_localidade_silver(df_localidade, PROCESSED_DIR)
    persist.save_vitimas_silver(df_vitimas, PROCESSED_DIR)
    persist.save_volume_trafego_silver(df_volume, PROCESSED_DIR)
    if df_tipo_veiculo is not None:
        persist.save_tipo_veiculo_silver(df_tipo_veiculo, PROCESSED_DIR)

    # ── GOLD: Enriquecimento / Cruzamento ─────────────────────────────────
    logger.info("[GOLD] Cruzamento e enriquecimento dos dados...")

    # Acidente + localidade
    df_acid_enrich = enrich.enrich_acidentes_localidade(df_acidentes, df_localidade)
    del df_acidentes

    # Agregação vítimas por acidente
    df_vitimas_agg = enrich.aggregate_vitimas_por_acidente(df_vitimas)
    del df_vitimas

    # Agregação veículos por acidente
    df_veiculos_agg = None
    if df_tipo_veiculo is not None:
        df_veiculos_agg = enrich.aggregate_veiculos_por_acidente(df_tipo_veiculo)
        del df_tipo_veiculo
    else:
        # DataFrame vazio para não quebrar o gold
        import pandas as pd
        df_veiculos_agg = pd.DataFrame(
            columns=["num_acidente", "total_veiculos", "tipos_veiculos",
                     "veiculo_predominante"]
        )

    # Dataset Gold principal
    df_gold = enrich.build_acidentes_gold(df_acid_enrich, df_vitimas_agg, df_veiculos_agg)
    del df_acid_enrich, df_vitimas_agg, df_veiculos_agg

    # Datasets analíticos derivados
    df_ranking = enrich.build_ranking_locais(df_gold)
    temporal = enrich.build_analise_temporal(df_gold)
    df_correlacao = enrich.build_correlacao_frota_acidentes(df_ranking)

    # ── Persistir camada Gold ─────────────────────────────────────────────
    logger.info("[GOLD] Persistindo camada Gold...")
    persist.save_acidentes_gold(df_gold, PROCESSED_DIR)
    persist.save_ranking_locais(df_ranking, PROCESSED_DIR)
    persist.save_analise_temporal(temporal, PROCESSED_DIR)
    persist.save_correlacao_frota(df_correlacao, PROCESSED_DIR)

    elapsed = time.time() - t0
    logger.info("=" * 60)
    logger.info("PIPELINE CONCLUÍDO em %.1f segundos (%.1f min)", elapsed, elapsed / 60)
    logger.info("Arquivos salvos em: %s", PROCESSED_DIR)
    logger.info("=" * 60)

    _print_summary(df_gold, df_ranking, temporal)


def _print_summary(df_gold, df_ranking, temporal) -> None:
    """Exibe um resumo dos principais resultados no terminal."""
    logger.info("")
    logger.info("── RESUMO DOS RESULTADOS ──────────────────────────────")
    logger.info("Total de acidentes processados : %d", df_gold["qtde_acidente"].sum())
    logger.info("Total de óbitos                : %d", df_gold["qtde_obitos"].sum())
    logger.info("Municípios analisados          : %d", df_ranking["municipio"].nunique())
    logger.info("")
    logger.info("TOP 10 municípios com mais acidentes:")
    top10 = df_ranking.head(10)[
        ["ranking_geral", "municipio", "uf_acidente", "total_acidentes",
         "total_obitos", "taxa_acidente_100k"]
    ]
    for _, row in top10.iterrows():
        logger.info(
            "  %2d. %-30s (%s) | %8d acidentes | %5d óbitos | taxa: %.1f/100k",
            row["ranking_geral"], row["municipio"], row["uf_acidente"],
            row["total_acidentes"], row["total_obitos"],
            row["taxa_acidente_100k"] if row["taxa_acidente_100k"] == row["taxa_acidente_100k"] else 0,
        )

    logger.info("")
    logger.info("Distribuição por ano:")
    por_ano = temporal["por_ano"]
    for _, row in por_ano.iterrows():
        logger.info(
            "  Ano %s: %d acidentes, %d óbitos",
            int(row["ano_acidente"]), int(row["total_acidentes"]), int(row["total_obitos"]),
        )
    logger.info("──────────────────────────────────────────────────────")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline de dados ATNB")
    parser.add_argument(
        "--skip-heavy",
        action="store_true",
        help="Pula ingestão do TipoVeiculo (310 MB) para execução mais rápida",
    )
    parser.add_argument(
        "--ano",
        type=int,
        default=None,
        help="Filtra o pipeline para um ano específico (ex: 2023)",
    )
    args = parser.parse_args()
    run_pipeline(skip_heavy=args.skip_heavy, ano_filtro=args.ano)
