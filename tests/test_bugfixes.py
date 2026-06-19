"""Regression tests for review bug-fixes (extraction, trends, SSRF guard)."""

import pytest

from claimlens.extract import extract_fields
from claimlens.qualitymind_client import QualityMindClientError, post_five_why
from claimlens.schema import RcaHandoff


def _handoff():
    return RcaHandoff(
        problem_statement="Recurring sync failure",
        anomaly_label="cloud_sync",
        claim_count=3,
        share=0.5,
        target_endpoints=["/quality/five-why"],
    )


def test_longest_needle_wins_over_alias():
    # "gateway" (specific) should win over the shorter alias "gw".
    fields = extract_fields("gateway gw module fault")
    assert fields.component == "Connectivity Gateway"


def test_validate_url_rejects_bad_scheme():
    with pytest.raises(QualityMindClientError):
        post_five_why(_handoff(), base_url="file:///etc/passwd")


def test_validate_url_rejects_link_local_metadata():
    # AWS metadata endpoint must be blocked.
    with pytest.raises(QualityMindClientError):
        post_five_why(_handoff(), base_url="http://169.254.169.254")
