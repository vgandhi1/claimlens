"""
Overcycle-anomaly text classifier.

A TF-IDF + multinomial Logistic Regression baseline: fast, fully reproducible
(fixed seed), small on disk, and strong on short field narratives. Kept behind a
thin class so a transformer head can be swapped in later without touching callers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from claimlens.anomaly import LABEL_NAMES, OVERCYCLE_LABELS
from claimlens.config import CONFIDENCE_REVIEW_THRESHOLD
from claimlens.schema import ClassificationResult

_RANDOM_STATE = 42


def build_pipeline() -> Pipeline:
    """TF-IDF (1–2 grams) → logistic regression."""
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
            stop_words="english",
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            C=4.0,
            class_weight="balanced",
            random_state=_RANDOM_STATE,
        )),
    ])


class AnomalyClassifier:
    """Train / persist / predict overcycle-anomaly labels for narratives."""

    def __init__(self, pipeline: Optional[Pipeline] = None):
        self.pipeline = pipeline or build_pipeline()
        self._fitted = pipeline is not None

    def fit(self, texts: list[str], labels: list[str]) -> "AnomalyClassifier":
        self.pipeline.fit(texts, labels)
        self._fitted = True
        return self

    def _result_from_proba(self, proba, classes: list[str]) -> ClassificationResult:
        scores = {c: round(float(p), 4) for c, p in zip(classes, proba)}
        best_idx = max(range(len(proba)), key=lambda i: proba[i])
        label = classes[best_idx]
        return ClassificationResult(
            label=label,
            label_name=LABEL_NAMES.get(label, label),
            confidence=round(float(proba[best_idx]), 4),
            is_overcycle=label in OVERCYCLE_LABELS,
            needs_review=float(proba[best_idx]) < CONFIDENCE_REVIEW_THRESHOLD,
            scores=scores,
        )

    def predict(self, text: str) -> ClassificationResult:
        return self.predict_many([text])[0]

    def predict_many(self, texts: list[str]) -> list[ClassificationResult]:
        """Vectorized scoring: one TF-IDF transform + predict_proba for the batch."""
        if not self._fitted:
            raise RuntimeError("Classifier is not trained. Call fit() or load() first.")
        if not texts:
            return []
        classes = list(self.pipeline.classes_)
        probas = self.pipeline.predict_proba(texts)
        return [self._result_from_proba(proba, classes) for proba in probas]

    def predict_batch(self, texts: list[str]) -> list[str]:
        if not self._fitted:
            raise RuntimeError("Classifier is not trained. Call fit() or load() first.")
        return list(self.pipeline.predict(texts))

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, path)

    @classmethod
    def load(cls, path: str | Path) -> "AnomalyClassifier":
        return cls(pipeline=joblib.load(path))
