from unittest.mock import MagicMock, patch

import pytest

from claimlens.qualitymind_client import QualityMindClientError, post_five_why
from claimlens.schema import RcaHandoff


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


def test_post_five_why_success():
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
        client_cls.return_value.__enter__.return_value.post.return_value = mock_response
        result = post_five_why(handoff, base_url="http://localhost:8000", api_key="k")
    assert result == {"status": "ok"}
