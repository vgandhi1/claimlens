"""Environment-driven configuration for ClaimLens."""

from __future__ import annotations

import os
from pathlib import Path

MODEL_PATH = Path(os.environ.get("CLAIMLENS_MODEL_PATH", "models/anomaly_clf.joblib"))
MAX_NARRATIVE_LENGTH = int(os.environ.get("CLAIMLENS_MAX_NARRATIVE_LENGTH", "8192"))
API_KEY = os.environ.get("CLAIMLENS_API_KEY")  # optional; unset = open API

QUALITYMIND_BASE_URL = os.environ.get("QUALITYMIND_BASE_URL", "").rstrip("/")
QUALITYMIND_API_KEY = os.environ.get("QUALITYMIND_API_KEY", "")
