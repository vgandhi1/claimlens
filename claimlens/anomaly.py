"""
Overcycle anomaly taxonomy for commercial-vehicle telematics warranty claims.

These are the field-narrative classes the classifier predicts. "Overcycle"
anomalies are repeated/abnormal device cycling events that inflate warranty
returns; correctly separating them from genuine hardware faults is the first
triage step in field root-cause analysis.
"""

from enum import Enum
from typing import Final


class SourceType(str, Enum):
    """Upstream stream a warranty narrative arrived from.

    Drives the by-source Pareto breakdown and stream-conditional extraction
    emphasis. `str` base keeps JSON output as the plain value.
    """

    customer_complaint = "customer_complaint"
    dealer_ro = "dealer_ro"
    field_log = "field_log"


# Canonical labels (stable string ids used in data, models, and the API).
SOFT_RESET: Final = "soft_reset"
CLOUD_SYNC: Final = "cloud_sync"
CONNECTIVITY_LOSS: Final = "connectivity_loss"
POWER_CYCLE: Final = "power_cycle"
NO_FAULT: Final = "no_fault"

LABELS: Final = [SOFT_RESET, CLOUD_SYNC, CONNECTIVITY_LOSS, POWER_CYCLE, NO_FAULT]

# Human-readable names for reports/UI.
LABEL_NAMES: Final = {
    SOFT_RESET: "Soft Reset",
    CLOUD_SYNC: "Cloud Sync",
    CONNECTIVITY_LOSS: "Connectivity Loss",
    POWER_CYCLE: "Power Cycle",
    NO_FAULT: "No Fault Found",
}

# Anomalies that count as "overcycle" (vs genuine fault / no-fault).
OVERCYCLE_LABELS: Final = {SOFT_RESET, CLOUD_SYNC, POWER_CYCLE}
