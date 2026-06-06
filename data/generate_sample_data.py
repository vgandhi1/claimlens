"""
Generate a synthetic, labeled warranty-narrative dataset.

No real claim data (PII-free). Narratives are templated per overcycle-anomaly
class with class-specific vocabulary plus shared filler, so the classifier has
genuine signal to learn while staying realistic for commercial-vehicle
telematics field language.

Usage:
    python data/generate_sample_data.py --n 1200 --out data/claims.csv
"""

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

from claimlens.anomaly import (
    CLOUD_SYNC,
    CONNECTIVITY_LOSS,
    NO_FAULT,
    POWER_CYCLE,
    SOFT_RESET,
)

COMPONENTS = [
    ("TCU", "TCU-{:04d}"),
    ("gateway", "GW-{:04d}"),
    ("modem", "MDM-{:03d}"),
    ("ECU", "ECU-{:03d}"),
    ("infotainment head unit", "IHU-{:04d}"),
]

# Class-conditional phrase banks (the learnable signal).
TEMPLATES = {
    SOFT_RESET: [
        "unit performs a soft reset {freq}; logs show watchdog reboot without power loss",
        "{comp} spontaneously reboots {freq}, self-recovers in seconds, no DTC stored",
        "device resets itself {freq} during operation, firmware restarts cleanly",
        "recurring soft reset on {comp}, comes back online automatically after reboot",
    ],
    CLOUD_SYNC: [
        "{comp} fails to sync with cloud backend {freq}; telematics records not uploading",
        "cloud sync timeout {freq}, data queued locally but never reaches server",
        "backend handshake fails, unit cannot sync trip data to cloud {freq}",
        "OTA/cloud synchronization error after update, sync retries exhausted",
    ],
    CONNECTIVITY_LOSS: [
        "{comp} drops cellular connection {freq}, no signal reported on dash",
        "loss of network connectivity {freq}, modem shows no carrier",
        "intermittent dropout of LTE link {freq}, antenna fault suspected",
        "vehicle goes offline {freq}, connectivity gateway reports no service",
    ],
    POWER_CYCLE: [
        "{comp} power cycles every ignition, hard power loss then restart",
        "unit loses power {freq} and cold-boots, suspected wiring/connector issue",
        "hard power cycle observed {freq}, full restart with all DTCs cleared",
        "device browns out on crank {freq}, reboots from cold start",
    ],
    NO_FAULT: [
        "customer reported issue with {comp}; bench test passed, no fault found",
        "no fault found on {comp}, unit operates normally, returned to service",
        "could not reproduce concern on {comp}, NFF, firmware up to date",
        "{comp} within spec on all checks, no anomaly detected",
    ],
}

FREQ = ["intermittently", "every ignition cycle", "overnight while parked",
        "on the highway", "repeatedly", "after the last OTA update"]

ACTIONS = ["Replaced unit.", "Reflashed firmware.", "No fault found.",
           "Updated firmware.", "Returned to depot.", "Rebooted and monitored."]

# Terse / vague field notes that carry weak class signal — the realistic hard
# cases that keep the classifier honest (it will not hit a perfect score).
AMBIGUOUS = [
    "{comp} acting up {freq}, customer not happy",
    "issue with {comp} {freq}, see attached log",
    "{comp} fault reported {freq}, investigating",
    "intermittent concern on {comp}, cannot always reproduce",
]

# Short phrases borrowed from a *different* class, appended to blur the line
# between related overcycle modes (reset/power-cycle, sync/connectivity).
CROSSTALK = {
    SOFT_RESET: "also briefly lost power once",
    POWER_CYCLE: "looked like a quick reset at first",
    CLOUD_SYNC: "network bars dropped during the attempt",
    CONNECTIVITY_LOSS: "sync also seemed delayed",
    NO_FAULT: "minor reset noted but cleared",
}


def _row(rng: random.Random, idx: int, start: date, noise: float) -> dict:
    label = rng.choice(list(TEMPLATES))
    comp_name, part_fmt = rng.choice(COMPONENTS)
    part = part_fmt.format(rng.randint(1, 999))
    if rng.random() < noise:
        template = rng.choice(AMBIGUOUS)
    else:
        template = rng.choice(TEMPLATES[label])
    narrative = template.format(comp=comp_name, freq=rng.choice(FREQ))
    if rng.random() < noise:
        narrative = f"{narrative}; {CROSSTALK[label]}"
    narrative = f"{narrative}. {rng.choice(ACTIONS)} Ref {part}."
    return {
        "claim_id": f"WC-{idx:06d}",
        "date": (start + timedelta(days=rng.randint(0, 364))).isoformat(),
        "vin": f"1FT{rng.randint(10**11, 10**12 - 1)}",
        "part_number": part,
        "component": comp_name,
        "narrative": narrative,
        "label": label,
    }


def generate(n: int, seed: int = 42, noise: float = 0.18) -> list[dict]:
    rng = random.Random(seed)
    start = date(2025, 1, 1)
    return [_row(rng, i, start, noise) for i in range(1, n + 1)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1200)
    ap.add_argument("--out", default="data/claims.csv")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--noise", type=float, default=0.18,
                    help="fraction of ambiguous/blended hard cases")
    args = ap.parse_args()

    rows = generate(args.n, args.seed, args.noise)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic warranty claims -> {out}")


if __name__ == "__main__":
    main()
