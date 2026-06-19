"""End-to-end analysis: narrative → classification + extraction → AnalyzedClaim."""

from typing import Optional

from claimlens.anomaly import SourceType
from claimlens.classify import AnomalyClassifier
from claimlens.extract import extract_fields
from claimlens.schema import AnalyzedClaim


def analyze_one(
    narrative: str,
    classifier: AnomalyClassifier,
    claim_id: Optional[str] = None,
    source_type: Optional[SourceType] = None,
) -> AnalyzedClaim:
    return AnalyzedClaim(
        claim_id=claim_id,
        narrative=narrative,
        classification=classifier.predict(narrative),
        extracted=extract_fields(narrative, source_type=source_type),
        source_type=source_type,
    )


def analyze_batch(
    records: list[dict],
    classifier: AnomalyClassifier,
) -> list[AnalyzedClaim]:
    """`records` are dicts with at least a 'narrative' key (optional 'claim_id', 'source_type')."""
    narratives = [r["narrative"] for r in records]
    classifications = classifier.predict_many(narratives)
    return [
        AnalyzedClaim(
            claim_id=r.get("claim_id"),
            narrative=r["narrative"],
            classification=classification,
            extracted=extract_fields(r["narrative"], source_type=r.get("source_type")),
            source_type=r.get("source_type"),
        )
        for r, classification in zip(records, classifications)
    ]
