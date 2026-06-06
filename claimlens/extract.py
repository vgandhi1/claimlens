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
_PART_RE = re.compile(r"\b[A-Z]{2,4}-\d{2,5}[A-Z]?\b")

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
    for needle, value in table.items():
        if needle in text:
            return value
    return None


def extract_fields(narrative: str, part_number_hint: Optional[str] = None) -> ExtractedFields:
    """Pull component / failure mode / symptom / action / part numbers."""
    text = narrative.lower()
    parts = sorted(set(_PART_RE.findall(narrative)))
    if part_number_hint and part_number_hint not in parts:
        parts.insert(0, part_number_hint)
    return ExtractedFields(
        component=_first_match(text, _COMPONENTS),
        failure_mode=_first_match(text, _FAILURE_MODES),
        symptom=_first_match(text, _SYMPTOMS),
        action_taken=_first_match(text, _ACTIONS),
        part_numbers=parts,
    )
