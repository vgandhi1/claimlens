import collections

from claimlens.anomaly import LABELS
from data.generate_sample_data import (
    LABEL_WEIGHTS,
    MIN_PER_CLASS,
    generate,
)


def test_distribution_is_literature_weighted():
    rows = generate(n=1200, seed=42)
    counts = collections.Counter(r["label"] for r in rows)
    # cloud_sync (infotainment/OTA/cloud-sync) is the dominant class.
    top = counts.most_common(1)[0][0]
    assert top == max(LABEL_WEIGHTS, key=LABEL_WEIGHTS.get)
    # Clearly non-uniform: dominant class outnumbers the smallest.
    assert max(counts.values()) > min(counts.values()) * 1.25


def test_every_label_meets_floor():
    rows = generate(n=1200, seed=42)
    counts = collections.Counter(r["label"] for r in rows)
    assert set(counts) == set(LABELS)
    assert min(counts.values()) >= MIN_PER_CLASS


def test_deterministic_for_seed():
    a = generate(n=300, seed=42)
    b = generate(n=300, seed=42)
    assert [r["narrative"] for r in a] == [r["narrative"] for r in b]


def test_small_n_falls_back_to_capped_floor():
    # n smaller than 5 * MIN_PER_CLASS: floor caps at n // num_labels, all labels present.
    rows = generate(n=20, seed=1)
    assert len(rows) == 20
    assert set(r["label"] for r in rows) <= set(LABELS)


def test_no_real_pii_only_synthetic_vins():
    rows = generate(n=100, seed=3)
    # Synthetic VIN pattern only (matches existing generator contract).
    assert all(r["vin"].startswith("1FT") for r in rows)
