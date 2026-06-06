from claimlens.pipeline import analyze_batch
from claimlens.trends import build_trend_report


def test_trend_report_aggregates(trained_classifier):
    records = [
        {"narrative": "TCU-0001 soft reset repeatedly, watchdog reboot", "claim_id": "A"},
        {"narrative": "TCU-0002 spontaneously reboots every ignition cycle", "claim_id": "B"},
        {"narrative": "gateway fails to sync to cloud, retries exhausted", "claim_id": "C"},
        {"narrative": "bench test passed, no fault found", "claim_id": "D"},
    ]
    analyzed = analyze_batch(records, trained_classifier)
    report = build_trend_report(analyzed)

    assert report.total_claims == 4
    # Three of four narratives are overcycle anomalies.
    assert report.overcycle_share == 0.75
    # by_label is sorted descending by count.
    counts = [b.count for b in report.by_label]
    assert counts == sorted(counts, reverse=True)
    assert abs(sum(b.share for b in report.by_label) - 1.0) < 1e-6


def test_empty_report_is_safe():
    report = build_trend_report([])
    assert report.total_claims == 0
    assert report.overcycle_share == 0.0
    assert report.by_label == []
