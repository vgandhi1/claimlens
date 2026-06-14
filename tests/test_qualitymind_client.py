from unittest.mock import MagicMock, patch

import pytest

from claimlens.qualitymind_client import (
    QualityMindClientError,
    _validate_url,
    execute_handoff,
    post_five_why,
)
from claimlens.schema import RcaHandoff


def _handoff(**overrides) -> RcaHandoff:
    base = dict(
        problem_statement="Recurring sync failure",
        component="Telematics Control Unit",
        anomaly_label="cloud_sync",
        claim_count=3,
        share=0.5,
        target_endpoints=["/quality/five-why", "/quality/draft-8d"],
    )
    base.update(overrides)
    return RcaHandoff(**base)


def test_post_five_why_requires_base_url():
    handoff = RcaHandoff(
        problem_statement="Recurring sync failure",
        anomaly_label="cloud_sync",
        claim_count=3,
        share=0.5,
        target_endpoints=["/quality/five-why"],
    )
    with pytest.raises(QualityMindClientError):
        post_five_why(handoff, base_url="")


def test_post_five_why_success_sends_full_contract():
    handoff = RcaHandoff(
        problem_statement="Recurring sync failure",
        component="Telematics Control Unit",
        anomaly_label="cloud_sync",
        claim_count=3,
        share=0.5,
        target_endpoints=["/quality/five-why"],
    )
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ok"}
    mock_response.raise_for_status = MagicMock()

    with patch("claimlens.qualitymind_client.httpx.Client") as client_cls:
        post = client_cls.return_value.__enter__.return_value.post
        post.return_value = mock_response
        result = post_five_why(handoff, base_url="http://localhost:8000", api_key="k")

    assert result == {"status": "ok"}
    sent = post.call_args.kwargs["json"]
    assert sent == {
        "problem_statement": "Recurring sync failure",
        "anomaly_label": "cloud_sync",
        "claim_count": 3,
        "component": "Telematics Control Unit",
    }


def test_post_five_why_omits_absent_component():
    handoff = RcaHandoff(
        problem_statement="Recurring sync failure",
        anomaly_label="cloud_sync",
        claim_count=3,
        share=0.5,
        target_endpoints=["/quality/five-why"],
    )
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ok"}
    mock_response.raise_for_status = MagicMock()

    with patch("claimlens.qualitymind_client.httpx.Client") as client_cls:
        post = client_cls.return_value.__enter__.return_value.post
        post.return_value = mock_response
        post_five_why(handoff, base_url="http://localhost:8000", api_key="k")

    sent = post.call_args.kwargs["json"]
    assert "component" not in sent
    assert sent["anomaly_label"] == "cloud_sync"


def test_execute_handoff_drives_all_target_endpoints():
    def fake_post(url, payload, headers, timeout, retries):
        return {"echo": url.rsplit("/", 1)[-1], "payload": payload}

    with patch("claimlens.qualitymind_client._post_json", side_effect=fake_post) as pj:
        results = execute_handoff(_handoff(), base_url="http://localhost:8000")

    assert set(results) == {"/quality/five-why", "/quality/draft-8d"}
    assert results["/quality/five-why"]["status"] == "ok"
    assert results["/quality/draft-8d"]["status"] == "ok"
    five_why_body = results["/quality/five-why"]["response"]["payload"]
    assert five_why_body["anomaly_label"] == "cloud_sync"
    assert five_why_body["claim_count"] == 3
    draft_body = results["/quality/draft-8d"]["response"]["payload"]
    assert draft_body == {
        "problem_statement": "Recurring sync failure",
        "component": "Telematics Control Unit",
    }
    assert pj.call_count == 2


def test_execute_handoff_partial_failure_keeps_successes():
    def fake_post(url, payload, headers, timeout, retries):
        if url.endswith("/quality/draft-8d"):
            raise QualityMindClientError("draft-8d down")
        return {"ok": True}

    with patch("claimlens.qualitymind_client._post_json", side_effect=fake_post):
        results = execute_handoff(_handoff(), base_url="http://localhost:8000")

    assert results["/quality/five-why"]["status"] == "ok"
    assert results["/quality/draft-8d"]["status"] == "error"
    assert "draft-8d down" in results["/quality/draft-8d"]["detail"]


def test_execute_handoff_raises_when_all_fail():
    def fake_post(url, payload, headers, timeout, retries):
        raise QualityMindClientError("down")

    with patch("claimlens.qualitymind_client._post_json", side_effect=fake_post):
        with pytest.raises(QualityMindClientError):
            execute_handoff(_handoff(), base_url="http://localhost:8000")


def test_execute_handoff_skips_unknown_endpoint():
    def fake_post(url, payload, headers, timeout, retries):
        return {"ok": True}

    handoff = _handoff(target_endpoints=["/quality/five-why", "/quality/bogus"])
    with patch("claimlens.qualitymind_client._post_json", side_effect=fake_post):
        results = execute_handoff(handoff, base_url="http://localhost:8000")

    assert results["/quality/five-why"]["status"] == "ok"
    assert results["/quality/bogus"]["status"] == "skipped"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000",
        "http://[::1]:8000",
        "http://10.0.0.5:8000",
        "http://[fd00::1]:8000",
    ],
)
def test_validate_url_allows_loopback_and_private(url):
    _validate_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/",
        "http://[fe80::1]/",
        "http://[ff02::1]/",
        "ftp://127.0.0.1/",
    ],
)
def test_validate_url_blocks_ssrf_targets(url):
    with pytest.raises(QualityMindClientError):
        _validate_url(url)
