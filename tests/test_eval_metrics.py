from claimlens.anomaly import LABELS
from claimlens.eval_metrics import build_eval_artifacts


def _fixture():
    # Small fixed holdout: every label present; one cloud_sync mispredicted as
    # connectivity_loss so recall < 1.0 for an overcycle label.
    y_true = [
        "soft_reset", "soft_reset",
        "cloud_sync", "cloud_sync",
        "connectivity_loss",
        "power_cycle",
        "no_fault",
    ]
    y_pred = [
        "soft_reset", "soft_reset",
        "cloud_sync", "connectivity_loss",   # one cloud_sync miss
        "connectivity_loss",
        "power_cycle",
        "no_fault",
    ]
    return y_true, y_pred


def test_confusion_matrix_shape_and_label_order():
    art = build_eval_artifacts(*_fixture())
    cm = art["confusion_matrix"]
    assert cm["labels"] == LABELS
    assert len(cm["rows_true_cols_pred"]) == len(LABELS)
    assert all(len(row) == len(LABELS) for row in cm["rows_true_cols_pred"])


def test_per_label_recall_has_every_label():
    art = build_eval_artifacts(*_fixture())
    assert set(art["per_label_recall"]) == set(LABELS)
    assert art["per_label_recall"]["soft_reset"] == 1.0
    # 1 of 2 cloud_sync correct.
    assert art["per_label_recall"]["cloud_sync"] == 0.5


def test_overcycle_recall_block():
    art = build_eval_artifacts(*_fixture())
    oc = art["overcycle_recall"]
    assert set(oc["labels"]) == {"soft_reset", "cloud_sync", "power_cycle"}
    # macro over (1.0 + 0.5 + 1.0) / 3
    assert oc["macro"] == round((1.0 + 0.5 + 1.0) / 3, 4)


def test_report_keeps_classification_report_keys():
    art = build_eval_artifacts(*_fixture())
    assert "macro avg" in art
    assert "accuracy" in art
