"""
Pure metric-assembly helpers for the classifier eval harness.

Kept out of `evaluate.py`'s `main()` so the artifact shape (confusion matrix,
per-label recall, overcycle recall) is unit-testable offline without training a
model. `evaluate.py` calls `build_eval_artifacts` and adds CV results on top.
"""

from __future__ import annotations

from sklearn.metrics import classification_report, confusion_matrix

from claimlens.anomaly import LABELS, OVERCYCLE_LABELS


def build_eval_artifacts(
    y_true: list[str],
    y_pred: list[str],
    labels: list[str] = LABELS,
    overcycle_labels: set[str] = OVERCYCLE_LABELS,
) -> dict:
    """Assemble the holdout metrics payload written to metrics.json.

    Returns the sklearn `classification_report` dict augmented with:
      - `confusion_matrix`: {labels, rows_true_cols_pred} (self-describing)
      - `per_label_recall`: recall keyed by every canonical label
      - `overcycle_recall`: macro + per-label recall over overcycle labels
    """
    report = classification_report(
        y_true, y_pred, labels=labels, output_dict=True, zero_division=0
    )

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    report["confusion_matrix"] = {
        "labels": list(labels),
        "rows_true_cols_pred": cm.tolist(),
    }

    report["per_label_recall"] = {
        lbl: round(float(report[lbl]["recall"]), 4) for lbl in labels
    }

    overcycle = [lbl for lbl in labels if lbl in overcycle_labels]
    report["overcycle_recall"] = {
        "labels": overcycle,
        "per_label": {
            lbl: round(float(report[lbl]["recall"]), 4) for lbl in overcycle
        },
        "macro": round(
            sum(float(report[lbl]["recall"]) for lbl in overcycle) / len(overcycle), 4
        )
        if overcycle
        else 0.0,
    }
    return report
