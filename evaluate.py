"""
Train + evaluate the overcycle-anomaly classifier and write real metrics.

Produces a stratified train/test split, fits the TF-IDF + LogReg pipeline,
reports per-class precision / recall / F1 + macro-F1, and persists both the
model and a metrics JSON. Numbers in the README come from this script.

Usage:
    python data/generate_sample_data.py        # if data/claims.csv is missing
    python evaluate.py
"""

import csv
import json
from pathlib import Path

from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from claimlens.anomaly import LABEL_NAMES, LABELS
from claimlens.classify import AnomalyClassifier

DATA = Path("data/claims.csv")
MODEL_OUT = Path("models/anomaly_clf.joblib")
METRICS_OUT = Path("models/metrics.json")


def load_data(path: Path) -> tuple[list[str], list[str]]:
    if not path.exists():
        raise SystemExit(
            f"{path} not found. Run: python data/generate_sample_data.py"
        )
    texts, labels = [], []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            texts.append(row["narrative"])
            labels.append(row["label"])
    return texts, labels


def main() -> None:
    texts, labels = load_data(DATA)
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.25, random_state=42, stratify=labels
    )

    clf = AnomalyClassifier().fit(X_train, y_train)
    y_pred = clf.predict_batch(X_test)

    report = classification_report(
        y_test, y_pred, labels=LABELS, output_dict=True, zero_division=0
    )

    clf.save(MODEL_OUT)
    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.write_text(json.dumps(report, indent=2))

    print(f"\nTrained on {len(X_train)} / tested on {len(X_test)} narratives\n")
    print(f"{'Class':<22}{'precision':>10}{'recall':>9}{'f1':>8}{'support':>9}")
    for label in LABELS:
        m = report[label]
        print(f"{LABEL_NAMES[label]:<22}{m['precision']:>10.3f}"
              f"{m['recall']:>9.3f}{m['f1-score']:>8.3f}{int(m['support']):>9}")
    macro = report["macro avg"]
    print(f"\n{'macro avg':<22}{macro['precision']:>10.3f}"
          f"{macro['recall']:>9.3f}{macro['f1-score']:>8.3f}")
    print(f"{'accuracy':<22}{report['accuracy']:>27.3f}")
    print(f"\nModel  -> {MODEL_OUT}\nMetrics -> {METRICS_OUT}")


if __name__ == "__main__":
    main()
