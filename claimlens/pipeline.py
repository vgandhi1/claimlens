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
    part_number: Optional[str] = None,
    source_type: Optional[SourceType] = None,
) -> AnalyzedClaim:
    return AnalyzedClaim(
        claim_id=claim_id,
        narrative=narrative,
        classification=classifier.predict(narrative),
        extracted=extract_fields(
            narrative, part_number_hint=part_number, source_type=source_type
        ),
        source_type=source_type,
    )


def analyze_batch(
    records: list[dict],
    classifier: AnomalyClassifier,
) -> list[AnalyzedClaim]:
    """`records` are dicts with at least a 'narrative' key (optional 'claim_id', 'part_number')."""
    narratives = [r["narrative"] for r in records]
    # Single vectorized classification pass; extraction stays per-record (pure regex).
    classifications = classifier.predict_many(narratives)
    return [
        AnalyzedClaim(
            claim_id=r.get("claim_id"),
            narrative=r["narrative"],
            classification=classification,
            extracted=extract_fields(
                r["narrative"],
                part_number_hint=r.get("part_number"),
                source_type=r.get("source_type"),
            ),
            source_type=r.get("source_type"),
        )
        for r, classification in zip(records, classifications)
    ]
