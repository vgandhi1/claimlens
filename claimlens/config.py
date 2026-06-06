"""Environment-driven configuration for ClaimLens."""

from __future__ import annotations

import os
from pathlib import Path

MODEL_PATH = Path(os.environ.get("CLAIMLENS_MODEL_PATH", "models/anomaly_clf.joblib"))
METRICS_PATH = Path(os.environ.get("CLAIMLENS_METRICS_PATH", "models/metrics.json"))
MANIFEST_PATH = Path(os.environ.get("CLAIMLENS_MANIFEST_PATH", "models/manifest.json"))
MAX_NARRATIVE_LENGTH = int(os.environ.get("CLAIMLENS_MAX_NARRATIVE_LENGTH", "8192"))
# Dev analytical: flag predictions below this confidence for human review
CONFIDENCE_REVIEW_THRESHOLD = float(os.environ.get("CLAIMLENS_CONFIDENCE_THRESHOLD", "0.55"))
ENVIRONMENT = os.environ.get("CLAIMLENS_ENVIRONMENT", "development")
API_KEY = os.environ.get("CLAIMLENS_API_KEY")  # optional; unset = open API

QUALITYMIND_BASE_URL = os.environ.get("QUALITYMIND_BASE_URL", "").rstrip("/")
QUALITYMIND_API_KEY = os.environ.get("QUALITYMIND_API_KEY", "")
