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
        if ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise QualityMindClientError(
                f"QUALITYMIND_BASE_URL resolves to a disallowed address ({addr})"
            )


def post_five_why(
    handoff: RcaHandoff,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = 30.0,
    retries: int = 1,
) -> dict[str, Any]:
    """POST problem_statement to QualityMind `/quality/five-why`."""
    url_base = (base_url or QUALITYMIND_BASE_URL).rstrip("/")
    if not url_base:
        raise QualityMindClientError("QUALITYMIND_BASE_URL is not configured")

    _validate_url(url_base)

    headers: dict[str, str] = {"Content-Type": "application/json"}
    key = api_key or QUALITYMIND_API_KEY
    if key:
        headers["X-API-Key"] = key

    payload = {"problem_statement": handoff.problem_statement}
    endpoint = f"{url_base}/quality/five-why"
    # Separate connect and read budgets so a fast-connecting but slow server
    # does not consume the whole timeout on a stalled read.
    timeout_cfg = httpx.Timeout(connect=5.0, read=timeout, write=timeout, pool=5.0)

    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout_cfg) as client:
                response = client.post(endpoint, json=payload, headers=headers)
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
