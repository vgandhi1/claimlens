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
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

from claimlens.anomaly import LABEL_NAMES, LABELS
from claimlens.classify import AnomalyClassifier, build_pipeline
from claimlens.config import CONFIDENCE_REVIEW_THRESHOLD, MANIFEST_PATH, METRICS_PATH, MODEL_PATH
from claimlens.eval_metrics import build_eval_artifacts

DATA = Path("data/claims.csv")


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

    # Holdout report + confusion matrix + per-label / overcycle recall.
    report = build_eval_artifacts(y_test, y_pred)

    # Stratified 5-fold CV on the full dataset gives a less optimistic estimate
    # than a single holdout (important since the corpus is template-generated).
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_macro_f1 = cross_val_score(
        build_pipeline(), texts, labels, cv=skf, scoring="f1_macro"
    )
    report["cv_macro_f1"] = {
        "mean": round(float(np.mean(cv_macro_f1)), 4),
        "std": round(float(np.std(cv_macro_f1)), 4),
        "folds": [round(float(s), 4) for s in cv_macro_f1],
    }

    macro = report["macro avg"]
    cv = report["cv_macro_f1"]

    clf.save(MODEL_PATH)
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(report, indent=2))

    data_bytes = DATA.read_bytes()
    manifest = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "environment": "development",
        "model_path": str(MODEL_PATH),
        "data_path": str(DATA),
        "data_sha256": hashlib.sha256(data_bytes).hexdigest(),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "labels": LABELS,
        "sklearn_version": __import__("sklearn").__version__,
        "joblib_version": joblib.__version__,
        "holdout_macro_f1": round(float(macro["f1-score"]), 4),
        "cv_macro_f1_mean": cv["mean"],
        "cv_macro_f1_std": cv["std"],
        "confidence_review_threshold": CONFIDENCE_REVIEW_THRESHOLD,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))

    print(f"\nTrained on {len(X_train)} / tested on {len(X_test)} narratives\n")
    print(f"{'Class':<22}{'precision':>10}{'recall':>9}{'f1':>8}{'support':>9}")
    for label in LABELS:
        m = report[label]
        print(f"{LABEL_NAMES[label]:<22}{m['precision']:>10.3f}"
              f"{m['recall']:>9.3f}{m['f1-score']:>8.3f}{int(m['support']):>9}")
    print(f"\n{'macro avg':<22}{macro['precision']:>10.3f}"
          f"{macro['recall']:>9.3f}{macro['f1-score']:>8.3f}")
    print(f"{'accuracy':<22}{report['accuracy']:>27.3f}")
    print(f"\n{'5-fold macro-F1':<22}{cv['mean']:>10.3f} ± {cv['std']:.3f}")
    print(f"{'overcycle recall':<22}{report['overcycle_recall']['macro']:>10.3f}")
    print(f"\nModel   -> {MODEL_PATH}")
    print(f"Metrics -> {METRICS_PATH}")
    print(f"Manifest -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
