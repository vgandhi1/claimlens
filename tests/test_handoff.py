from claimlens.handoff import build_handoff
from claimlens.pipeline import analyze_batch
from claimlens.schema import (
    AnalyzedClaim,
    ClassificationResult,
    ExtractedFields,
)


def _claim(label, component, *, needs_review=False):
    return AnalyzedClaim(
        narrative=f"{component} {label}",
        classification=ClassificationResult(
            label=label,
            label_name=label,
            confidence=0.5 if needs_review else 0.9,
            is_overcycle=True,
            needs_review=needs_review,
        ),
        extracted=ExtractedFields(component=component, failure_mode="reboot"),
    )


def test_handoff_picks_dominant_overcycle_trend(trained_classifier):
    records = [
        {"narrative": "TCU-0421 soft resets repeatedly, watchdog reboot, no power loss"},
        {"narrative": "TCU-0421 spontaneously reboots every ignition cycle, self-recovers"},
        {"narrative": "TCU-0099 soft reset overnight, firmware restarts cleanly"},
        {"narrative": "bench test passed, no fault found"},
    ]
    analyzed = analyze_batch(records, trained_classifier)
    payload = build_handoff(analyzed)

    assert payload is not None
    assert payload.anomaly_label == "soft_reset"
    assert payload.claim_count == 3
    assert payload.component == "Telematics Control Unit"
    assert "/quality/five-why" in payload.target_endpoints
    assert "soft" in payload.problem_statement.lower() or "reset" in payload.problem_statement.lower()


def test_handoff_exclude_needs_review_changes_dominant_trend():
    # Dominant raw trend is low-confidence; reviewed trend is the runner-up.
    claims = [
        _claim("soft_reset", "Telematics Control Unit", needs_review=True),
        _claim("soft_reset", "Telematics Control Unit", needs_review=True),
        _claim("soft_reset", "Telematics Control Unit", needs_review=True),
        _claim("cloud_sync", "Connectivity Gateway"),
        _claim("cloud_sync", "Connectivity Gateway"),
    ]

    raw = build_handoff(claims)
    assert raw.anomaly_label == "soft_reset"
    assert raw.claim_count == 3

    triaged = build_handoff(claims, exclude_needs_review=True)
    assert triaged.anomaly_label == "cloud_sync"
    assert triaged.component == "Connectivity Gateway"
    assert triaged.claim_count == 2
    # Share is over the surviving (reviewed) population, not the raw batch.
    assert triaged.share == 1.0


def test_handoff_exclude_needs_review_none_when_all_flagged():
    claims = [
        _claim("soft_reset", "Telematics Control Unit", needs_review=True),
        _claim("cloud_sync", "Connectivity Gateway", needs_review=True),
    ]
    assert build_handoff(claims, exclude_needs_review=True) is None
    assert build_handoff(claims) is not None


def test_handoff_none_when_no_overcycle(trained_classifier):
    records = [
        {"narrative": "no fault found, bench test passed, within spec"},
        {"narrative": "could not reproduce concern, NFF, firmware up to date"},
    ]
    analyzed = analyze_batch(records, trained_classifier)
    assert build_handoff(analyzed) is None
