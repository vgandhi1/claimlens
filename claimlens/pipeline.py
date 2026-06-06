"""End-to-end analysis: narrative → classification + extraction → AnalyzedClaim."""

from typing import Optional

from claimlens.classify import AnomalyClassifier
from claimlens.extract import extract_fields
from claimlens.schema import AnalyzedClaim


def analyze_one(
    narrative: str,
    classifier: AnomalyClassifier,
    claim_id: Optional[str] = None,
    part_number: Optional[str] = None,
) -> AnalyzedClaim:
    return AnalyzedClaim(
        claim_id=claim_id,
        narrative=narrative,
        classification=classifier.predict(narrative),
        extracted=extract_fields(narrative, part_number_hint=part_number),
    )


def analyze_batch(
    records: list[dict],
    classifier: AnomalyClassifier,
) -> list[AnalyzedClaim]:
    """`records` are dicts with at least a 'narrative' key (optional 'claim_id', 'part_number')."""
    return [
        analyze_one(
            r["narrative"],
            classifier,
            r.get("claim_id"),
            r.get("part_number"),
        )
        for r in records
    ]
