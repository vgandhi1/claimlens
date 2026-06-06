from claimlens.handoff import build_handoff
from claimlens.pipeline import analyze_batch


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
    assert payload.part_number == "TCU-0421"  # most common part
    assert "/quality/five-why" in payload.target_endpoints
    assert "soft" in payload.problem_statement.lower() or "reset" in payload.problem_statement.lower()


def test_handoff_none_when_no_overcycle(trained_classifier):
    records = [
        {"narrative": "no fault found, bench test passed, within spec"},
        {"narrative": "could not reproduce concern, NFF, firmware up to date"},
    ]
    analyzed = analyze_batch(records, trained_classifier)
    assert build_handoff(analyzed) is None
