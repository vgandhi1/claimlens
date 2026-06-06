"""
ClaimLens FastAPI service.

Endpoints:
  GET  /health      — service + model status
  POST /classify    — narrative -> overcycle-anomaly label + confidence
  POST /extract     — narrative -> structured fields
  POST /analyze     — narrative -> classification + extraction
  POST /trends      — batch of narratives -> Pareto failure-trend report
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException

from claimlens import __version__
from claimlens.classify import AnomalyClassifier
from claimlens.extract import extract_fields
from claimlens.handoff import build_handoff
from claimlens.pipeline import analyze_batch, analyze_one
from claimlens.schema import (
    AnalyzedClaim,
    ClaimNarrative,
    ClassificationResult,
    ExtractedFields,
    RcaHandoff,
    TrendReport,
)
from claimlens.trends import build_trend_report

MODEL_PATH = Path("models/anomaly_clf.joblib")

app = FastAPI(title="ClaimLens", version=__version__,
              description="Warranty-narrative NLP for field quality RCA")

_classifier: Optional[AnomalyClassifier] = None


def get_classifier() -> AnomalyClassifier:
    global _classifier
    if _classifier is None:
        if not MODEL_PATH.exists():
            raise HTTPException(
                status_code=503,
                detail="Model not trained. Run `python evaluate.py` to create "
                       f"{MODEL_PATH}.",
            )
        _classifier = AnomalyClassifier.load(MODEL_PATH)
    return _classifier


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "model_loaded": _classifier is not None or MODEL_PATH.exists(),
    }


@app.post("/classify", response_model=ClassificationResult)
def classify(claim: ClaimNarrative) -> ClassificationResult:
    return get_classifier().predict(claim.narrative)


@app.post("/extract", response_model=ExtractedFields)
def extract(claim: ClaimNarrative) -> ExtractedFields:
    return extract_fields(claim.narrative)


@app.post("/analyze", response_model=AnalyzedClaim)
def analyze(claim: ClaimNarrative) -> AnalyzedClaim:
    return analyze_one(claim.narrative, get_classifier(), claim.claim_id)


@app.post("/trends", response_model=TrendReport)
def trends(claims: list[ClaimNarrative]) -> TrendReport:
    if not claims:
        raise HTTPException(status_code=400, detail="Provide at least one narrative.")
    records = [{"narrative": c.narrative, "claim_id": c.claim_id} for c in claims]
    analyzed = analyze_batch(records, get_classifier())
    return build_trend_report(analyzed)


@app.post("/handoff", response_model=RcaHandoff)
def handoff(claims: list[ClaimNarrative]) -> RcaHandoff:
    """Dominant overcycle trend -> QualityMind-RAG-ready 5-Why / 8D payload."""
    if not claims:
        raise HTTPException(status_code=400, detail="Provide at least one narrative.")
    records = [{"narrative": c.narrative, "claim_id": c.claim_id} for c in claims]
    analyzed = analyze_batch(records, get_classifier())
    payload = build_handoff(analyzed)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail="No overcycle anomalies in this batch to escalate to RCA.",
        )
    return payload
