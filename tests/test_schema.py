import pytest
from pydantic import ValidationError

from claimlens.schema import ClaimNarrative, ClassificationResult


def test_narrative_requires_min_length():
    with pytest.raises(ValidationError):
        ClaimNarrative(narrative="ab")


def test_classification_confidence_bounded():
    with pytest.raises(ValidationError):
        ClassificationResult(
            label="soft_reset", label_name="Soft Reset",
            confidence=1.5, is_overcycle=True,
        )


def test_valid_classification():
    r = ClassificationResult(
        label="cloud_sync", label_name="Cloud Sync",
        confidence=0.9, is_overcycle=True, scores={"cloud_sync": 0.9},
    )
    assert r.is_overcycle is True
