from claimlens.anomaly import SourceType
from claimlens.extract import extract_fields


def test_extracts_component_from_narrative():
    note = "TCU spontaneously reboots intermittently. Reflashed firmware."
    out = extract_fields(note)
    assert out.component == "Telematics Control Unit"
    assert out.failure_mode == "spontaneous reboot"
    assert out.symptom == "intermittent"
    assert out.action_taken == "firmware reflashed"


def test_handles_cloud_sync_language():
    note = "Gateway fails to sync trip data to cloud after update. No fault found."
    out = extract_fields(note)
    assert out.component == "Connectivity Gateway"
    assert out.failure_mode == "sync failure"
    assert out.action_taken == "no fault found"


def test_empty_fields_when_no_match():
    out = extract_fields("vehicle inspected and released")
    assert out.component is None
    assert out.failure_mode is None


def test_dealer_ro_recovers_action_base_path_misses():
    note = "TCU concern; R&R unit, road tested OK."
    assert extract_fields(note).action_taken is None
    out = extract_fields(note, source_type=SourceType.dealer_ro)
    assert out.action_taken == "road tested"


def test_field_log_recovers_overcycle_failure_mode():
    note = "ECU watchdog event logged during operation."
    assert extract_fields(note).failure_mode is None
    out = extract_fields(note, source_type=SourceType.field_log)
    assert out.failure_mode == "watchdog reset"


def test_source_type_does_not_change_base_matches():
    note = "Gateway fails to sync trip data to cloud. No fault found."
    base = extract_fields(note)
    typed = extract_fields(note, source_type=SourceType.dealer_ro)
    assert typed.failure_mode == base.failure_mode == "sync failure"
    assert typed.action_taken == base.action_taken == "no fault found"


def test_customer_complaint_is_default_behavior():
    note = "TCU concern; R&R unit per warranty repair."
    assert (
        extract_fields(note, source_type=SourceType.customer_complaint).action_taken
        == extract_fields(note).action_taken
    )
