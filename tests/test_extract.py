from claimlens.extract import extract_fields


def test_extracts_component_and_part_numbers():
    note = "TCU-0421 spontaneously reboots intermittently. Reflashed firmware. Ref TCU-0421."
    out = extract_fields(note)
    assert out.component == "Telematics Control Unit"
    assert "TCU-0421" in out.part_numbers
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
    assert out.part_numbers == []


def test_part_numbers_deduplicated_and_sorted():
    out = extract_fields("ECU-12 and ECU-12 plus GW-0007 noted")
    assert out.part_numbers == ["ECU-12", "GW-0007"]
