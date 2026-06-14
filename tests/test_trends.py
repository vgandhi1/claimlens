from claimlens.anomaly import SourceType
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
    assert report.by_source == []


def test_by_source_breakdown_with_unknown_bucket(trained_classifier):
    records = [
        {"narrative": "soft reset repeatedly, watchdog reboot",
         "source_type": SourceType.field_log},
        {"narrative": "gateway fails to sync to cloud, retries exhausted",
         "source_type": SourceType.field_log},
        {"narrative": "customer says screen reboots", "source_type": SourceType.customer_complaint},
        {"narrative": "bench test passed, no fault found"},  # no source_type -> Unknown
    ]
    analyzed = analyze_batch(records, trained_classifier)
    report = build_trend_report(analyzed)

    keys = {b.key: b.count for b in report.by_source}
    assert keys["field_log"] == 2
    assert keys["customer_complaint"] == 1
    assert keys["Unknown"] == 1
    # Shares (incl. Unknown) sum to 1.0.
    assert abs(sum(b.share for b in report.by_source) - 1.0) < 1e-6
