"""
Rule-based extraction of structured fields from warranty narratives.

Deliberately dependency-light (regex + keyword gazetteers) so it runs anywhere
with no model download. Gazetteers are tuned for commercial-vehicle telematics /
connected-ECU field language and are easy to extend.
"""

import re
from typing import Optional

from claimlens.schema import ExtractedFields

# Part numbers like "TCU-4821", "ECU-22A", "GW-0097"
_PART_RE = re.compile(r"\b[A-Z]{2,4}-\d{2,5}[A-Z]?\b", re.ASCII)

# Acronym-dash-number codes that share the part-number shape but are not parts.
_NON_PART_PREFIXES = frozenset(
    {"VIN", "DTC", "OBD", "GPS", "LTE", "USB", "RPM", "VOC", "NFF", "PID", "CAN"}
)

_COMPONENTS = {
    "tcu": "Telematics Control Unit",
    "telematics control unit": "Telematics Control Unit",
    "gateway": "Connectivity Gateway",
    "gw": "Connectivity Gateway",
    "modem": "Cellular Modem",
    "ecu": "Electronic Control Unit",
    "infotainment": "Infotainment Head Unit",
    "head unit": "Infotainment Head Unit",
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


def _first_match(text: str, table: dict[str, str]) -> Optional[str]:
    """Return the value for the longest matching needle (most specific wins).

    Length tie-break avoids order-dependent results when a narrative contains
    several keywords (e.g. "gateway" beating the shorter alias "gw").
    """
    best_needle: Optional[str] = None
    for needle in table:
        if needle in text and (best_needle is None or len(needle) > len(best_needle)):
            best_needle = needle
    return table[best_needle] if best_needle is not None else None


def extract_fields(narrative: str, part_number_hint: Optional[str] = None) -> ExtractedFields:
    """Pull component / failure mode / symptom / action / part numbers."""
    text = narrative.lower()
    parts = sorted(
        p for p in set(_PART_RE.findall(narrative)) if p.split("-", 1)[0] not in _NON_PART_PREFIXES
    )
    if part_number_hint and part_number_hint not in parts:
        parts.insert(0, part_number_hint)
    return ExtractedFields(
        component=_first_match(text, _COMPONENTS),
        failure_mode=_first_match(text, _FAILURE_MODES),
        symptom=_first_match(text, _SYMPTOMS),
        action_taken=_first_match(text, _ACTIONS),
        part_numbers=parts,
    )
