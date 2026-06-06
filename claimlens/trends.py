"""
Failure-trend aggregation — turns a batch of analyzed claims into the Pareto
view that field-quality engineers use to pick which issue to drive through
5-Why / 8D RCA next.
"""

from collections import Counter
from typing import Iterable

from claimlens.anomaly import LABEL_NAMES, OVERCYCLE_LABELS
from claimlens.schema import AnalyzedClaim, TrendBucket, TrendReport


def _pareto(values: Iterable[str], total: int, name_map: dict[str, str] | None = None) -> list[TrendBucket]:
    counts = Counter(v for v in values if v)
    buckets = [
        TrendBucket(
            key=(name_map.get(k, k) if name_map else k),
            count=n,
            share=round(n / total, 4) if total else 0.0,
        )
        for k, n in counts.most_common()
    ]
    return buckets


def build_trend_report(claims: list[AnalyzedClaim]) -> TrendReport:
    """Aggregate analyzed claims into label / component / failure-mode Paretos."""
    total = len(claims)
    overcycle = sum(1 for c in claims if c.classification.label in OVERCYCLE_LABELS)
    return TrendReport(
        total_claims=total,
        by_label=_pareto((c.classification.label for c in claims), total, LABEL_NAMES),
        by_component=_pareto((c.extracted.component for c in claims), total),
        by_failure_mode=_pareto((c.extracted.failure_mode for c in claims), total),
        overcycle_share=round(overcycle / total, 4) if total else 0.0,
    )
