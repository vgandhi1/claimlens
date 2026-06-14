"""Pydantic contracts for ClaimLens inputs and structured outputs."""

from typing import Optional

from pydantic import BaseModel, Field

from claimlens.anomaly import SourceType
from claimlens.config import MAX_NARRATIVE_LENGTH


class ClaimNarrative(BaseModel):
    """A single free-text warranty / field-service narrative to analyze."""

    narrative: str = Field(
        ...,
        min_length=3,
        max_length=MAX_NARRATIVE_LENGTH,
        description="Free-text claim or field note",
    )
    claim_id: Optional[str] = None
    source_type: Optional[SourceType] = Field(
        default=None,
        description="Upstream stream (customer_complaint|dealer_ro|field_log)",
    )


class ExtractedFields(BaseModel):
    """Structured fields pulled from a narrative by rule-based extraction."""

    component: Optional[str] = None
    failure_mode: Optional[str] = None
    symptom: Optional[str] = None
    action_taken: Optional[str] = None


class ClassificationResult(BaseModel):
    """Overcycle-anomaly classification for a narrative."""

    label: str
    label_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_overcycle: bool
    needs_review: bool = False
    scores: dict[str, float] = Field(default_factory=dict)


class AnalyzedClaim(BaseModel):
    """Full analysis record = classification + extraction for one narrative."""

    claim_id: Optional[str] = None
    narrative: str
    classification: ClassificationResult
    extracted: ExtractedFields
    source_type: Optional[SourceType] = None


class TrendBucket(BaseModel):
    key: str
    count: int
    share: float = Field(..., ge=0.0, le=1.0)


class TrendReport(BaseModel):
    """Pareto-style aggregation that hands off to 5-Why / 8D RCA."""

    total_claims: int
    by_label: list[TrendBucket]
    by_component: list[TrendBucket]
    by_failure_mode: list[TrendBucket]
    by_source: list[TrendBucket] = Field(default_factory=list)
    overcycle_share: float = Field(..., ge=0.0, le=1.0)


class RcaHandoff(BaseModel):
    """QualityMind-RAG-ready payload for the dominant overcycle trend."""

    problem_statement: str
    component: Optional[str] = None
    anomaly_label: str
    claim_count: int
    share: float = Field(..., ge=0.0, le=1.0)
    target_endpoints: list[str] = Field(default_factory=list)


class RcaHandoffResponse(RcaHandoff):
    """Handoff payload optionally enriched with a live QualityMind response."""

    qualitymind_response: Optional[dict] = None
