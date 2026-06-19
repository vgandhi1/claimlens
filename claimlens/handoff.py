"""
RCA hand-off: turn the dominant failure trend in a batch of analyzed claims
into a QualityMind-RAG-ready payload.

This is the "feeding Pareto failure analysis directly into 5-Why/8D" step —
ClaimLens picks the top overcycle trend and emits the exact `problem_statement`
(+ descriptive `component` from upstream extraction) that QualityMind's
`/quality/five-why` and `/quality/draft-8d` endpoints consume.
"""

from collections import Counter
from typing import Optional

from claimlens.anomaly import LABEL_NAMES, OVERCYCLE_LABELS
from claimlens.schema import AnalyzedClaim, RcaHandoff


def _top(values, default: Optional[str] = None) -> Optional[str]:
    counts = Counter(v for v in values if v)
    return counts.most_common(1)[0][0] if counts else default


def build_handoff(
    claims: list[AnalyzedClaim],
    exclude_needs_review: bool = False,
) -> Optional[RcaHandoff]:
    """Pick the dominant overcycle trend → QualityMind-ready RCA payload.

    Returns None when there are no overcycle anomalies to escalate.

    When ``exclude_needs_review`` is True, low-confidence claims flagged
    ``classification.needs_review`` are dropped before trend selection — the
    guardrail "triage before RCA" so unreviewed claims do not skew the Pareto
    or seed a 5-Why/8D on a mislabeled trend.
    """
    candidates = claims
    if exclude_needs_review:
        candidates = [c for c in claims if not c.classification.needs_review]

    overcycle = [c for c in candidates if c.classification.label in OVERCYCLE_LABELS]
    if not overcycle:
        return None

    top_label = _top(c.classification.label for c in overcycle)
    in_label = [c for c in overcycle if c.classification.label == top_label]

    component = _top((c.extracted.component for c in in_label), "telematics unit")
    failure_mode = _top((c.extracted.failure_mode for c in in_label), "anomaly")

    count = len(in_label)
    share = round(count / len(candidates), 4)
    label_name = LABEL_NAMES.get(top_label, top_label)

    problem_statement = (
        f"Recurring {failure_mode} on {component} "
        f"({label_name}) — {count} field claims, "
        f"{share:.0%} of analyzed returns"
    )

    return RcaHandoff(
        problem_statement=problem_statement,
        component=component,
        anomaly_label=top_label,
        claim_count=count,
        share=share,
        target_endpoints=["/quality/five-why", "/quality/draft-8d"],
    )
