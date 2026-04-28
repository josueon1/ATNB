"""
Módulo de Aprendizado de Máquina - ATNB
========================================
Treina e avalia classificadores para prever a gravidade de lesão
dos envolvidos em acidentes de trânsito.

Alvo: gravidade_lesao  →  SEM FERIMENTO / LEVE / GRAVE / OBITO
Features: faixa_idade, genero, tp_envolvido, equip_seguranca,
          ind_motorista, susp_alcool, mes_acidente

Modelos disponíveis:
  - DecisionTreeClassifier   (sklearn.tree)
  - MLPClassifier            (sklearn.neural_network)
  - SVC via make_pipeline    (sklearn.svm + sklearn.preprocessing)

Avaliação:
  - train_test_split
  - cross_val_score  (cv=10, somente Decision Tree — mais rápido)
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

logger = logging.getLogger(__name__)

# ── Configuração ──────────────────────────────────────────────────────────────
FEATURES = [
    "faixa_idade",
    "genero",
    "tp_envolvido",
    "equip_seguranca",
    "ind_motorista",
    "susp_alcool",
    "mes_acidente",
]
TARGET = "gravidade_lesao"

# Ordem das classes para exibição consistente
CLASS_ORDER = ["SEM FERIMENTO", "LEVE", "GRAVE", "OBITO"]


# ── Carregamento dos dados ────────────────────────────────────────────────────
def load_ml_data(
    processed_dir: Path,
    ano: int = 2023,
    sample_n: int = 30_000,
) -> pd.DataFrame:
    """
    Carrega dados do vitimas_silver para um ano e retorna uma amostra
    balanceada pronta para ML.
    """
    vitimas_dir = processed_dir / "vitimas_silver"
    logger.info("Carregando vitimas_silver (ano=%d)...", ano)

    table = pq.read_table(vitimas_dir, filters=[("ano_acidente", "=", ano)])
    df = table.to_pandas()

    # Mantém somente colunas necessárias para economizar memória
    keep = FEATURES + [TARGET]
    df = df[[c for c in keep if c in df.columns]].copy()

    # Converte category → str para LabelEncoder
    for col in df.columns:
        if hasattr(df[col], "cat"):
            df[col] = df[col].astype(str)

    df = df.dropna(subset=keep)

    if len(df) > sample_n:
        df = df.sample(n=sample_n, random_state=42)

    logger.info("  → %d amostras prontas para ML", len(df))
    return df


# ── Preparação das features ───────────────────────────────────────────────────
def prepare_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """
    Codifica features categóricas com LabelEncoder e retorna (X, y).
    """
    df = df.copy()

    encoders: dict[str, LabelEncoder] = {}
    for col in FEATURES:
        if df[col].dtype == object or str(df[col].dtype) == "category":
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    X = df[FEATURES].astype(float).values
    y = df[TARGET].astype(str).values
    return X, y


# ── Treino e avaliação dos modelos ────────────────────────────────────────────
def _base_metrics(
    clf: Any,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> dict:
    """Treina o classificador e retorna métricas básicas."""
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    return {
        "modelo": type(clf).__name__,
        "acuracia": acc,
        "y_pred_sample": y_pred[:5].tolist(),
        "report": report,
        "clf": clf,
    }


def train_decision_tree(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    cv: int = 10,
) -> dict:
    """DecisionTreeClassifier com cross_val_score."""
    logger.info("Treinando DecisionTreeClassifier...")
    clf = DecisionTreeClassifier(random_state=0)
    result = _base_metrics(clf, X_train, y_train, X_test, y_test)

    logger.info("  → Calculando cross_val_score (cv=%d)...", cv)
    cv_scores = cross_val_score(clf, X_train, y_train, cv=cv)
    result["cv_scores"] = cv_scores.tolist()
    result["cv_mean"] = float(cv_scores.mean())
    result["cv_std"] = float(cv_scores.std())

    # Importância das features
    result["feature_importances"] = dict(
        zip(FEATURES, clf.feature_importances_.tolist())
    )
    return result


def train_mlp(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> dict:
    """MLPClassifier com parâmetros idênticos às imagens de referência."""
    logger.info("Treinando MLPClassifier...")
    clf = MLPClassifier(random_state=1, max_iter=300)
    result = _base_metrics(clf, X_train, y_train, X_test, y_test)

    # Previsão detalhada (probabilidade) para as 3 primeiras amostras
    if hasattr(clf, "predict_proba"):
        result["proba_sample"] = clf.predict_proba(X_test[:3]).tolist()
    return result


def train_svc(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> dict:
    """SVC dentro de make_pipeline com StandardScaler."""
    logger.info("Treinando SVC (make_pipeline + StandardScaler)...")
    clf = make_pipeline(StandardScaler(), SVC(gamma="auto"))
    result = _base_metrics(clf, X_train, y_train, X_test, y_test)
    result["modelo"] = "SVC"
    return result


# ── Orquestrador principal ────────────────────────────────────────────────────
def run_ml_pipeline(
    processed_dir: Path,
    ano: int = 2023,
    sample_n: int = 30_000,
    models: list[str] | None = None,
) -> dict:
    """
    Executa o pipeline completo de ML e retorna resultados de todos os modelos.

    Args:
        processed_dir: Diretório de dados processados.
        ano: Ano dos dados a utilizar.
        sample_n: Número de amostras para treino+teste.
        models: Lista de modelos a treinar ("dt", "mlp", "svc").
                Por padrão: ["dt", "mlp", "svc"].

    Returns:
        Dicionário com resultados por modelo.
    """
    if models is None:
        models = ["dt", "mlp", "svc"]

    df = load_ml_data(processed_dir, ano=ano, sample_n=sample_n)
    X, y = prepare_features(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    logger.info(
        "Split: %d treino / %d teste | classes: %s",
        len(X_train),
        len(X_test),
        list(np.unique(y)),
    )

    results: dict[str, dict] = {}

    if "dt" in models:
        results["dt"] = train_decision_tree(X_train, y_train, X_test, y_test)

    if "mlp" in models:
        results["mlp"] = train_mlp(X_train, y_train, X_test, y_test)

    if "svc" in models:
        results["svc"] = train_svc(X_train, y_train, X_test, y_test)

    return results
