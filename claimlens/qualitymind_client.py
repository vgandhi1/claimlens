"""HTTP client for posting RCA handoffs to a running QualityMind-RAG instance."""

from __future__ import annotations

import ipaddress
import socket
import time
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from claimlens.config import QUALITYMIND_API_KEY, QUALITYMIND_BASE_URL
from claimlens.schema import RcaHandoff

_ALLOWED_SCHEMES = {"http", "https"}
_RETRYABLE_STATUS = {502, 503, 504}

# Endpoints CLaimLens knows how to drive. target_endpoints values outside this
# set are ignored (reported as skipped) rather than blindly POSTed.
_SUPPORTED_ENDPOINTS = {"/quality/five-why", "/quality/draft-8d"}


class QualityMindClientError(Exception):
    """Raised when the QualityMind handoff request fails."""


def _validate_url(url_base: str) -> None:
    """Reject SSRF-prone targets.

    Blocks non-HTTP(S) schemes and link-local / cloud-metadata addresses
    (e.g. 169.254.169.254). Loopback and private ranges are allowed because the
    common deployment points ClaimLens at an internal QualityMind instance.
    """
    parsed = urlparse(url_base)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise QualityMindClientError(
            f"QUALITYMIND_BASE_URL scheme must be http/https, got {parsed.scheme!r}"
        )
    host = parsed.hostname
    if not host:
        raise QualityMindClientError("QUALITYMIND_BASE_URL has no host")

    try:
        resolved = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise QualityMindClientError(f"Cannot resolve QualityMind host {host!r}") from exc

    for addr in resolved:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        # Loopback is safe and required for local QualityMind. Check it first:
        # IPv6 ::1 also has is_reserved=True, so without this it would be blocked
        # by the reserved check below. Do NOT widen this to is_private — the cloud
        # metadata IP 169.254.169.254 and fe80::/10 link-local are is_private=True
        # but must stay blocked (SSRF). Private ranges (10/8, fd00::/8) already
        # pass since they are not link-local / reserved / multicast.
        if ip.is_loopback:
            continue
        if ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise QualityMindClientError(
                f"QUALITYMIND_BASE_URL resolves to a disallowed address ({addr})"
            )


def _payload_for(endpoint: str, handoff: RcaHandoff) -> Optional[dict[str, Any]]:
    """Build the request body QualityMind expects for a given endpoint.

    Returns None for endpoints CLaimLens does not know how to drive.
    """
    if endpoint == "/quality/five-why":
        # Full cross-project handoff contract (GUARDRAILS § Handoff contract):
        # component (descriptive name from extraction/trends) drives PFMEA / NCR
        # retrieval on the QualityMind side; anomaly_label keeps taxonomy traceability.
        payload: dict[str, Any] = {
            "problem_statement": handoff.problem_statement,
            "anomaly_label": handoff.anomaly_label,
            "claim_count": handoff.claim_count,
        }
        if handoff.component:
            payload["component"] = handoff.component
        return payload
    if endpoint == "/quality/draft-8d":
        # QualityMind DraftBody: problem_statement (+ optional component).
        payload = {"problem_statement": handoff.problem_statement}
        if handoff.component:
            payload["component"] = handoff.component
        return payload
    return None


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
    retries: int,
) -> dict[str, Any]:
    """POST one JSON payload with retry on transient (502/503/504) responses."""
    # Separate connect and read budgets so a fast-connecting but slow server
    # does not consume the whole timeout on a stalled read.
    timeout_cfg = httpx.Timeout(connect=5.0, read=timeout, write=timeout, pool=5.0)

    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout_cfg) as client:
                response = client.post(url, json=payload, headers=headers)
                if response.status_code in _RETRYABLE_STATUS and attempt < retries:
                    last_exc = QualityMindClientError(
                        f"QualityMind returned {response.status_code}"
                    )
                    time.sleep(0.5 * (attempt + 1))
                    continue
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise QualityMindClientError(
                f"QualityMind handoff failed with HTTP {status}"
            ) from exc
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise QualityMindClientError("QualityMind handoff request failed") from exc

    # Exhausted retries on retryable status codes.
    raise QualityMindClientError("QualityMind handoff request failed") from last_exc


def _resolve(base_url: Optional[str], api_key: Optional[str]) -> tuple[str, dict[str, str]]:
    url_base = (base_url or QUALITYMIND_BASE_URL).rstrip("/")
    if not url_base:
        raise QualityMindClientError("QUALITYMIND_BASE_URL is not configured")
    _validate_url(url_base)

    headers: dict[str, str] = {"Content-Type": "application/json"}
    key = api_key or QUALITYMIND_API_KEY
    if key:
        headers["X-API-Key"] = key
    return url_base, headers


def post_five_why(
    handoff: RcaHandoff,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = 30.0,
    retries: int = 1,
) -> dict[str, Any]:
    """POST the handoff to QualityMind `/quality/five-why` and return its response."""
    url_base, headers = _resolve(base_url, api_key)
    payload = _payload_for("/quality/five-why", handoff)
    assert payload is not None  # five-why is always supported
    return _post_json(f"{url_base}/quality/five-why", payload, headers, timeout, retries)


def execute_handoff(
    handoff: RcaHandoff,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = 30.0,
    retries: int = 1,
) -> dict[str, dict[str, Any]]:
    """Drive every endpoint in `handoff.target_endpoints`.

    Returns a per-endpoint map: each value is `{"status": "ok", "response": ...}`
    or `{"status": "error", "detail": ...}` / `{"status": "skipped", ...}`.
    Raises QualityMindClientError only when *every* supported endpoint failed,
    so a partial outage still surfaces whatever succeeded (fail-safe handoff,
    GUARDRAILS § QualityMind client).
    """
    url_base, headers = _resolve(base_url, api_key)

    # Preserve order, drop duplicates; fall back to five-why if none declared.
    endpoints = list(dict.fromkeys(handoff.target_endpoints or ["/quality/five-why"]))

    results: dict[str, dict[str, Any]] = {}
    attempted = 0
    failed = 0
    for endpoint in endpoints:
        payload = _payload_for(endpoint, handoff)
        if payload is None or endpoint not in _SUPPORTED_ENDPOINTS:
            results[endpoint] = {
                "status": "skipped",
                "detail": "unsupported target endpoint",
            }
            continue
        attempted += 1
        try:
            response = _post_json(
                f"{url_base}{endpoint}", payload, headers, timeout, retries
            )
            results[endpoint] = {"status": "ok", "response": response}
        except QualityMindClientError as exc:
            failed += 1
            results[endpoint] = {"status": "error", "detail": str(exc)}

    if attempted and failed == attempted:
        raise QualityMindClientError(
            "All QualityMind handoff endpoints failed"
        )
    return results
