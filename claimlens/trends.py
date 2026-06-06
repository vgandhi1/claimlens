"""
Failure-trend aggregation — turns a batch of analyzed claims into the Pareto
view that field-quality engineers use to pick which issue to drive through
5-Why / 8D RCA next.
"""

from collections import Counter
from typing import Iterable

from claimlens.anomaly import LABEL_NAMES, OVERCYCLE_LABELS
from claimlens.schema import AnalyzedClaim, TrendBucket, TrendReport

_UNKNOWN = "__unknown__"


def _pareto(
    values: Iterable[str],
    total: int,
    name_map: dict[str, str] | None = None,
    include_unknown: bool = False,
) -> list[TrendBucket]:
    if include_unknown:
        # Count missing extractions as "Unknown" so shares sum to 1.0.
        counts = Counter(v if v else _UNKNOWN for v in values)
    else:
        counts = Counter(v for v in values if v)

    def _label(k: str) -> str:
        if k == _UNKNOWN:
            return "Unknown"
        return name_map.get(k, k) if name_map else k

    return [
        TrendBucket(
            key=_label(k),
            count=n,
            share=round(n / total, 4) if total else 0.0,
        )
        for k, n in counts.most_common()
    ]


def build_trend_report(claims: list[AnalyzedClaim]) -> TrendReport:
    """Aggregate analyzed claims into label / component / failure-mode Paretos."""
    total = len(claims)
    overcycle = sum(1 for c in claims if c.classification.label in OVERCYCLE_LABELS)
    return TrendReport(
        total_claims=total,
        by_label=_pareto((c.classification.label for c in claims), total, LABEL_NAMES),
        by_component=_pareto(
            (c.extracted.component for c in claims), total, include_unknown=True
        ),
        by_failure_mode=_pareto(
            (c.extracted.failure_mode for c in claims), total, include_unknown=True
        ),
        overcycle_share=round(overcycle / total, 4) if total else 0.0,
    )
