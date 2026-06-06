import pytest

from claimlens.classify import AnomalyClassifier
from data.generate_sample_data import generate


@pytest.fixture(scope="session")
def trained_classifier() -> AnomalyClassifier:
    """A classifier trained on a small deterministic synthetic set."""
    rows = generate(n=400, seed=7)
    texts = [r["narrative"] for r in rows]
    labels = [r["label"] for r in rows]
    return AnomalyClassifier().fit(texts, labels)
