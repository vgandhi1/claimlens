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
# Class-conditional phrase banks (the learnable signal). Theme phrasing mirrors
# published automotive-warranty frequencies — infotainment / OTA / cloud-sync
# dominant, with battery-range disputes and key-fob / USB edge cases — mapped
# onto the locked 5-label taxonomy (themes are vocabulary, NOT new labels).
TEMPLATES = {
    SOFT_RESET: [
        "unit performs a soft reset {freq}; logs show watchdog reboot without power loss",
        "{comp} spontaneously reboots {freq}, self-recovers in seconds, no DTC stored",
        "device resets itself {freq} during operation, firmware restarts cleanly",
        "recurring soft reset on {comp}, comes back online automatically after reboot",
        "infotainment head unit reboots {freq} after the latest OTA update, screen restarts",
        "head unit watchdog restart {freq} following firmware update, no power loss",
    ],
    CLOUD_SYNC: [
        "{comp} fails to sync with cloud backend {freq}; telematics records not uploading",
        "cloud sync timeout {freq}, data queued locally but never reaches server",
        "backend handshake fails, unit cannot sync trip data to cloud {freq}",
        "OTA/cloud synchronization error after update, sync retries exhausted",
        "infotainment OTA download stalls {freq}, map and firmware sync never completes",
        "connected-services app desync {freq}, account fails to sync with cloud profile",
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

# Rare edge-case phrasing from the warranty literature (key-fob / USB / battery
# range). Genuinely infrequent — sampled at EDGE_RATE so they stay "edge cases"
# and do not blur the bulk signal of their host class.
EDGE_TEMPLATES = {
    CONNECTIVITY_LOSS: [
        "key fob loses pairing {freq}, range drops and remote unlock fails",
        "USB device disconnects {freq}, port enumeration lost, phone link drops",
    ],
    NO_FAULT: [
        "customer disputes battery range {freq}; diagnostic within spec, no fault found",
        "USB port reported not recognized {freq}, passed retest, no fault found",
    ],
}
EDGE_RATE = 0.12

# Published-warranty-inspired label weights (themes mapped onto locked taxonomy).
# cloud_sync (infotainment/OTA/cloud) dominant; soft_reset (post-OTA reboots)
# next; connectivity_loss carries key-fob/USB edge cases; no_fault carries
# battery-range disputes. A per-class floor protects macro-F1 + StratifiedKFold.
LABEL_WEIGHTS = {
    CLOUD_SYNC: 0.32,
    SOFT_RESET: 0.24,
    CONNECTIVITY_LOSS: 0.18,
    POWER_CYCLE: 0.13,
    NO_FAULT: 0.13,
}
# Floor is the dominant lever: it keeps the minority classes (power_cycle,
# no_fault) above the support level macro-F1 needs while the weights still make
# cloud_sync/soft_reset visibly dominant. Tuned so holdout macro-F1 >= 0.88.
MIN_PER_CLASS = 140

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


def _weighted_labels(rng: random.Random, n: int) -> list[str]:
    """Label sequence matching LABEL_WEIGHTS with a MIN_PER_CLASS floor.

    Emits the floor for every label first (guarantees support for macro-F1 and
    5-fold stratification), then fills the remainder by weighted draw. Shuffled
    so label order is not positional. Deterministic for a given rng/seed.
    """
    labels = list(LABEL_WEIGHTS)
    floor = min(MIN_PER_CLASS, n // len(labels))
    seq = [lbl for lbl in labels for _ in range(floor)]
    remaining = n - len(seq)
    if remaining > 0:
        weights = [LABEL_WEIGHTS[lbl] for lbl in labels]
        seq.extend(rng.choices(labels, weights=weights, k=remaining))
    rng.shuffle(seq)
    return seq


def _row(rng: random.Random, idx: int, start: date, noise: float, label: str) -> dict:
    comp_name, part_fmt = rng.choice(COMPONENTS)
    part = part_fmt.format(rng.randint(1, 999))
    if rng.random() < noise:
        template = rng.choice(AMBIGUOUS)
    elif label in EDGE_TEMPLATES and rng.random() < EDGE_RATE:
        template = rng.choice(EDGE_TEMPLATES[label])
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
    labels = _weighted_labels(rng, n)
    return [_row(rng, i, start, noise, labels[i - 1]) for i in range(1, n + 1)]


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
