"""
Rule-based extraction of structured fields from warranty narratives.

Deliberately dependency-light (regex + keyword gazetteers) so it runs anywhere
with no model download. Outputs descriptive **component** names only — BOM /
part-number codes are engineering metadata (QualityMind DB), not customer-complaint
fields. Gazetteers are tuned for commercial-vehicle telematics / connected-ECU
field language and are easy to extend.
"""

from typing import Optional

from claimlens.anomaly import SourceType
from claimlens.schema import ExtractedFields

_COMPONENTS = {
    "tcu": "Telematics Control Unit",
    "telematics control unit": "Telematics Control Unit",
    "telematics unit": "Telematics Control Unit",
    "gateway": "Connectivity Gateway",
    "gw": "Connectivity Gateway",
    "modem": "Cellular Modem",
    "ecu": "Electronic Control Unit",
    "infotainment": "Infotainment Head Unit",
    "head unit": "Infotainment Head Unit",
    "infotainment head unit": "Infotainment Head Unit",
    "antenna": "Antenna Module",
    "sim": "SIM / eUICC",
}

_FAILURE_MODES = {
    "reboot": "spontaneous reboot",
    "reboots": "spontaneous reboot",
    "reset": "unexpected reset",
    "resets": "unexpected reset",
    "no signal": "loss of signal",
    "drops": "dropped connection",
    "dropout": "dropped connection",
    "fails to sync": "sync failure",
    "sync fail": "sync failure",
    "won't sync": "sync failure",
    "timeout": "communication timeout",
    "no power": "no power",
    "overheat": "thermal fault",
    "corrupt": "data corruption",
}

_SYMPTOMS = {
    "intermittent": "intermittent",
    "recurring": "recurring",
    "repeated": "recurring",
    "every ignition": "ignition-cycle correlated",
    "after update": "post-OTA",
    "overnight": "idle/parked",
    "highway": "in-motion",
}

_ACTIONS = {
    "replaced": "component replaced",
    "reflashed": "firmware reflashed",
    "reflash": "firmware reflashed",
    "updated firmware": "firmware updated",
    "no fault found": "no fault found",
    "nff": "no fault found",
    "rebooted": "power cycled",
    "returned": "returned to depot",
}

_DEALER_RO_ACTIONS = {
    "r&r": "removed and replaced",
    "removed and replaced": "removed and replaced",
    "swapped": "component replaced",
    "cleared codes": "DTCs cleared",
    "cleared dtc": "DTCs cleared",
    "road tested": "road tested",
    "warranty repair": "warranty repair performed",
    "recalibrated": "recalibrated",
}

_FIELD_LOG_FAILURE_MODES = {
    "watchdog": "watchdog reset",
    "watchdog reset": "watchdog reset",
    "brownout": "power brownout",
    "cold boot": "cold restart",
    "cold-boot": "cold restart",
    "power cycle": "hard power cycle",
    "sync retry": "sync retry exhausted",
    "retries exhausted": "sync retry exhausted",
    "offline": "connectivity loss",
}


def _first_match(text: str, table: dict[str, str]) -> Optional[str]:
    """Return the value for the longest matching needle (most specific wins)."""
    best_needle: Optional[str] = None
    for needle in table:
        if needle in text and (best_needle is None or len(needle) > len(best_needle)):
            best_needle = needle
    return table[best_needle] if best_needle is not None else None


def extract_fields(
    narrative: str,
    source_type: Optional[SourceType] = None,
) -> ExtractedFields:
    """Pull component / failure mode / symptom / action from free-text narratives."""
    text = narrative.lower()

    failure_mode = _first_match(text, _FAILURE_MODES)
    action_taken = _first_match(text, _ACTIONS)
    if source_type == SourceType.dealer_ro and action_taken is None:
        action_taken = _first_match(text, _DEALER_RO_ACTIONS)
    if source_type == SourceType.field_log and failure_mode is None:
        failure_mode = _first_match(text, _FIELD_LOG_FAILURE_MODES)

    return ExtractedFields(
        component=_first_match(text, _COMPONENTS),
        failure_mode=failure_mode,
        symptom=_first_match(text, _SYMPTOMS),
        action_taken=action_taken,
    )
