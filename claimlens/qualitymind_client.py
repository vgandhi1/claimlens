"""HTTP client for posting RCA handoffs to a running QualityMind-RAG instance."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from claimlens.config import QUALITYMIND_API_KEY, QUALITYMIND_BASE_URL
from claimlens.schema import RcaHandoff


class QualityMindClientError(Exception):
    """Raised when the QualityMind handoff request fails."""


def post_five_why(
    handoff: RcaHandoff,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """POST problem_statement to QualityMind `/quality/five-why`."""
    url_base = (base_url or QUALITYMIND_BASE_URL).rstrip("/")
    if not url_base:
        raise QualityMindClientError(
            "QUALITYMIND_BASE_URL is not configured"
        )

    headers: dict[str, str] = {"Content-Type": "application/json"}
    key = api_key or QUALITYMIND_API_KEY
    if key:
        headers["X-API-Key"] = key

    payload = {"problem_statement": handoff.problem_statement}
    endpoint = f"{url_base}/quality/five-why"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise QualityMindClientError("QualityMind handoff request failed") from exc
