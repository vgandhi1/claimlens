"""
ClaimLens FastAPI service.

Endpoints:
  GET  /health      — service + model status
  POST /classify    — narrative -> overcycle-anomaly label + confidence
  POST /extract     — narrative -> structured fields
  POST /analyze     — narrative -> classification + extraction
  POST /trends      — batch of narratives -> Pareto failure-trend report
  POST /handoff     — dominant overcycle trend -> QualityMind-ready payload
  POST /handoff/execute — handoff + live POST to QualityMind /quality/five-why
"""

import hmac
from typing import Optional

from fastapi import FastAPI, HTTPException, Request

from claimlens import __version__
from claimlens.classify import AnomalyClassifier
from claimlens.config import API_KEY, MODEL_PATH
from claimlens.extract import extract_fields
from claimlens.handoff import build_handoff
from claimlens.pipeline import analyze_batch, analyze_one
from claimlens.qualitymind_client import QualityMindClientError, execute_handoff
from claimlens.schema import (
    AnalyzedClaim,
    ClaimNarrative,
    ClassificationResult,
    ExtractedFields,
    RcaHandoff,
    RcaHandoffResponse,
    TrendReport,
)
from claimlens.trends import build_trend_report

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


@app.middleware("http")
async def optional_api_key_guard(request: Request, call_next):
    if not API_KEY:
        return await call_next(request)
    if request.url.path in {"/health", "/docs", "/redoc", "/openapi.json"}:
        return await call_next(request)
    provided = request.headers.get("X-API-Key")
    # Constant-time compare to avoid leaking the key via a timing side-channel.
    if not provided or not hmac.compare_digest(provided, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return await call_next(request)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        # Reflect actual in-memory load state; a present-but-corrupt file would
        # still fail on first /classify, so don't claim loaded on file existence.
        "model_loaded": _classifier is not None,
        "model_file_present": MODEL_PATH.exists(),
    }


@app.post("/classify", response_model=ClassificationResult)
def classify(claim: ClaimNarrative) -> ClassificationResult:
    return get_classifier().predict(claim.narrative)


@app.post("/extract", response_model=ExtractedFields)
def extract(claim: ClaimNarrative) -> ExtractedFields:
    return extract_fields(claim.narrative, part_number_hint=claim.part_number)


@app.post("/analyze", response_model=AnalyzedClaim)
def analyze(claim: ClaimNarrative) -> AnalyzedClaim:
    return analyze_one(
        claim.narrative,
        get_classifier(),
        claim.claim_id,
        claim.part_number,
    )


@app.post("/trends", response_model=TrendReport)
def trends(claims: list[ClaimNarrative]) -> TrendReport:
    if not claims:
        raise HTTPException(status_code=400, detail="Provide at least one narrative.")
    records = [
        {
            "narrative": c.narrative,
            "claim_id": c.claim_id,
            "part_number": c.part_number,
        }
        for c in claims
    ]
    analyzed = analyze_batch(records, get_classifier())
    return build_trend_report(analyzed)


@app.post("/handoff", response_model=RcaHandoff)
def handoff(claims: list[ClaimNarrative]) -> RcaHandoff:
    """Dominant overcycle trend -> QualityMind-RAG-ready 5-Why / 8D payload."""
    if not claims:
        raise HTTPException(status_code=400, detail="Provide at least one narrative.")
    records = [
        {
            "narrative": c.narrative,
            "claim_id": c.claim_id,
            "part_number": c.part_number,
        }
        for c in claims
    ]
    analyzed = analyze_batch(records, get_classifier())
    payload = build_handoff(analyzed)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail="No overcycle anomalies in this batch to escalate to RCA.",
        )
    return payload


@app.post("/handoff/execute", response_model=RcaHandoffResponse)
def handoff_execute(claims: list[ClaimNarrative]) -> RcaHandoffResponse:
    """Build handoff payload and POST to every target endpoint on QualityMind-RAG.

    Drives all `target_endpoints` (e.g. /quality/five-why + /quality/draft-8d).
    Returns a per-endpoint result map; only 502s if all endpoints fail.
    """
    payload = handoff(claims)
    try:
        qm_responses = execute_handoff(payload)
    except QualityMindClientError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
    return RcaHandoffResponse(**payload.model_dump(), qualitymind_response=qm_responses)
