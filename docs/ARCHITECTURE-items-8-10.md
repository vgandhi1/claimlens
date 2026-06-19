# CLaimLens — Architecture / Implementation Plan: Review Items #8–#10

**Status:** ✅ IMPLEMENTED 2026-06-13 — plan executed as written (one addition: `EDGE_TEMPLATES`, see §10).
**Companion:** `REQUIREMENTS-items-8-10.md`.
**Workflow source:** [`TEXT-NARRATIVE-PATH.md`](TEXT-NARRATIVE-PATH.md) (CLaimLens owns steps 1–3; #8 `source_type` = its three intake streams).
**Date:** 2026-06-13

Concrete, file-level plan. Each change is additive and offline-testable. The plan
below was followed during implementation; deviations are flagged inline and
summarized at the end.

---

## Current shape (verified against repo)

```
claimlens/
  schema.py     ClaimNarrative, ExtractedFields, ClassificationResult,
                AnalyzedClaim, TrendBucket, TrendReport, RcaHandoff(+Response)
  anomaly.py    LABELS, LABEL_NAMES, OVERCYCLE_LABELS = {soft_reset, cloud_sync, power_cycle}
  extract.py    extract_fields(narrative, source_type) — gazetteers → component name
  classify.py   AnomalyClassifier (TF-IDF + LogReg)
  pipeline.py   analyze_one / analyze_batch (record dicts -> AnalyzedClaim)
  trends.py     build_trend_report -> by_label / by_component / by_failure_mode
  api.py        /classify /extract /analyze /trends /handoff /handoff/execute
  handoff.py    build_handoff (consumes AnalyzedClaim; RcaHandoff contract)
data/generate_sample_data.py   templated synthetic corpus, seed=42
evaluate.py                    train + metrics.json + manifest.json
tests/  test_{schema,extract,classify,trends,api,handoff,...}.py (28 total)
```

Data flow for #8:
`ClaimNarrative` → api builds record dict → `analyze_batch` → `AnalyzedClaim` →
`build_trend_report`. `source_type` must ride this whole path to reach `by_source`.

---

## Item #8 — Source-typed intake

### 8.1 `anomaly.py` (or new `sources.py`) — define the enum source of truth
Add a `str`-`Enum` so it serializes as the plain string and is import-shareable:

```python
from enum import Enum

class SourceType(str, Enum):
    customer_complaint = "customer_complaint"
    dealer_ro = "dealer_ro"
    field_log = "field_log"
```
Place beside the taxonomy constants (parallel to `LABELS`). Keep it in one module so
schema, extract, and tests import the same enum.

### 8.2 `schema.py` — thread the field
- `ClaimNarrative`: add `source_type: Optional[SourceType] = None`.
- `AnalyzedClaim`: add `source_type: Optional[SourceType] = None` (so trends can read it
  off the analyzed record — the record dict in api/pipeline is the carrier).
- `TrendReport`: add `by_source: list[TrendBucket] = Field(default_factory=list)`.

`Optional[...] = None` keeps every existing payload valid. Enum gives free 422 on bad
input. `str` base keeps JSON output unchanged for downstream.

### 8.3 `pipeline.py` — carry source_type onto AnalyzedClaim
- `analyze_one(...)`: add `source_type: Optional[SourceType] = None` param, pass to both
  `AnalyzedClaim(source_type=...)` and to `extract_fields(... source_type=...)`.
- `analyze_batch(records, ...)`: read `r.get("source_type")` per record, set on
  `AnalyzedClaim`, and pass into `extract_fields`.

### 8.4 `api.py` — populate the record dict
In `/analyze`, `/trends`, `/handoff` the record dict already carries
`narrative/claim_id/source_type`. `/handoff` passes descriptive `component` only.
it through `analyze_batch` but `build_handoff` ignores it → handoff payload unchanged
(contract preserved). `/classify` and `/extract` need no source routing unless emphasis
is wanted on the single-shot `/extract`; recommend also passing
`source_type=claim.source_type` into `/extract`'s `extract_fields` call for consistency.

### 8.5 `extract.py` — per-stream emphasis (regex-first, deterministic)
Signature: `extract_fields(narrative, source_type=None)`.

- **dealer_ro → emphasize `action_taken`:** when `source_type == dealer_ro` and the base
  `_first_match(text, _ACTIONS)` returns `None`, apply an extended dealer-RO action
  gazetteer (e.g. "r&r", "swapped", "cleared codes", "road tested", "warranty repair")
  before giving up. Pure dict lookup; no LLM. Keeps default path byte-identical when
  source_type is None.
- **field_log → emphasize overcycle signal:** field logs are terse machine text. Bias
  the existing `_FAILURE_MODES`/symptom matching with a field-log supplement keyed to
  overcycle vocabulary (reset/reboot/watchdog/power-cycle/sync-retry) so reset/sync/
  power evidence is captured. This stays in extraction (failure_mode/symptom) — it does
  **not** alter classification labels (taxonomy locked).
- **customer_complaint / None:** unchanged.

Implementation pattern: keep base gazetteers as today; add small
`_DEALER_RO_ACTIONS` and `_FIELD_LOG_FAILURE_MODES` supplements consulted only for the
matching source_type. Determinism preserved (still longest-match dict lookup).

### 8.6 `trends.py` — by_source Pareto
Add to `build_trend_report`:
```python
by_source=_pareto(
    (c.source_type.value if c.source_type else None for c in claims),
    total, include_unknown=True,
),
```
Reuses existing `_pareto(... include_unknown=True)` so `None` → `Unknown` and shares sum
to 1.0, consistent with `by_component`/`by_failure_mode`.

### 8.7 Tests (new logic = new test)
- `test_schema.py`: ClaimNarrative accepts valid enum, rejects junk (422-equivalent
  ValidationError), defaults None.
- `test_extract.py`: dealer_ro recovers an `action_taken` the None path misses; field_log
  surfaces overcycle failure_mode; None path output unchanged (regression guard).
- `test_trends.py`: `by_source` present, Unknown bucket appears for mixed input, shares
  sum ≈ 1.0.
- `test_api.py`: `/trends` with mixed source_type returns by_source; `/analyze` echoes
  source_type; `/handoff` payload unchanged with vs without source_type (contract test).

---

## Item #9 — Classifier eval artifacts

### 9.1 `evaluate.py` — extend the metrics payload (additive)
After the existing `classification_report(... output_dict=True)`:
```python
from sklearn.metrics import confusion_matrix
cm = confusion_matrix(y_test, y_pred, labels=LABELS)
report["confusion_matrix"] = {
    "labels": LABELS,
    "rows_true_cols_pred": cm.tolist(),
}
report["per_label_recall"] = {lbl: round(report[lbl]["recall"], 4) for lbl in LABELS}
overcycle = [SOFT_RESET, CLOUD_SYNC, POWER_CYCLE]   # import from anomaly
report["overcycle_recall"] = {
    "labels": overcycle,
    "macro": round(sum(report[l]["recall"] for l in overcycle) / len(overcycle), 4),
    "per_label": {l: round(report[l]["recall"], 4) for l in overcycle},
}
```
Existing `report["cv_macro_f1"]`, `macro avg`, per-class blocks, and the manifest stay
untouched. `metrics.json` write is the same `json.dumps(report, ...)`.

Import note: `evaluate.py` already imports `LABELS, LABEL_NAMES` from `claimlens.anomaly`;
add `OVERCYCLE_LABELS` (or the three constants) from the same module — single source of
truth, no hard-coded label strings.

### 9.2 Optional console line
Print `overcycle_recall["macro"]` alongside the existing macro-F1 line for quick read.

### 9.3 Test
`evaluate.py` is analytical (runs outside pytest). To honor "new logic = new test"
without invoking training, **extract the metric-assembly into a small pure helper**, e.g.
`build_eval_artifacts(y_test, y_pred) -> dict`, and unit-test it on a tiny fixed
`y_test/y_pred` array: assert confusion-matrix shape (5×5), label order, recall values,
and overcycle macro. Helper lives in `evaluate.py` or a thin `claimlens/eval_metrics.py`
if you prefer it importable. Keep `main()` calling the helper.

---

## Item #10 — Literature-weighted synthetic data

### 10.1 `generate_sample_data.py` — weighted label sampling + theme banks
Replace the uniform `label = rng.choice(list(TEMPLATES))` with a weighted draw plus a
per-class floor.

```python
# Published-warranty-inspired weights (themes mapped onto locked taxonomy).
LABEL_WEIGHTS = {
    CLOUD_SYNC: 0.34,          # infotainment / OTA / cloud-sync dominant
    SOFT_RESET: 0.24,          # post-OTA reboots
    CONNECTIVITY_LOSS: 0.18,   # incl. key-fob / USB connectivity edge cases
    POWER_CYCLE: 0.12,
    NO_FAULT: 0.12,            # incl. battery-range disputes (bench-pass)
}
MIN_PER_CLASS = 60   # floor so macro-F1 + StratifiedKFold(5) stay valid
```
Algorithm: first emit `MIN_PER_CLASS` rows per label (guarantees support + stratifiable),
then fill the remaining `n - 5*MIN_PER_CLASS` rows by weighted `rng.choices(...)`. Keeps
the skew at scale while protecting minority classes from collapsing macro-F1. Seed/CLI
unchanged → still deterministic.

### 10.2 Theme vocabulary (PII-free) under existing labels
Extend `TEMPLATES`/`AMBIGUOUS` with mapped phrasing (no new labels):
- `cloud_sync`: infotainment OTA download stalls, app/cloud account desync, map/firmware
  OTA sync failures.
- `soft_reset`: head-unit reboot after OTA, infotainment watchdog restart.
- `connectivity_loss`: key-fob pairing/range loss, USB device drop / port enumeration
  loss, BT/phone-link disconnect.
- `no_fault`: battery-range-dispute concern (customer reports low range, bench/diagnostic
  within spec, NFF), USB "device not recognized" that passes retest.

All synthetic; keep the existing fake-VIN/part formatting (already PII-safe pattern).

### 10.3 Regression handling (the critical part)
- After implementing, run `python data/generate_sample_data.py` then `python evaluate.py`.
- Confirm `macro avg f1 ≥ 0.88` **and** `overcycle_recall.macro` acceptable.
- If below 0.88: raise `MIN_PER_CLASS`, soften extreme weights, or enrich minority-class
  phrase banks — do **not** lower the gate.
- Update any F1/label-count assertions in tests and README numbers to the new
  distribution **in the same change**.

### 10.4 Tests
- `test_generate` (offline, fast, small n): label distribution is non-uniform and matches
  weights within tolerance; every label ≥ `MIN_PER_CLASS`; determinism (same seed → same
  rows); narratives contain no VIN-like PII beyond the existing synthetic pattern.
- Update existing data/F1-dependent tests to the new baseline.

---

## Build order & verification gate
1. **#8** schema/pipeline/api/extract/trends + tests → `ruff` + full pytest green.
2. **#9** evaluate.py helper + metrics keys + helper unit test → `python evaluate.py`,
   confirm `metrics.json` has confusion_matrix/per_label_recall/overcycle_recall,
   macro-F1 ≥ 0.88.
3. **#10** weighted generator + theme banks → regenerate, re-run `evaluate.py`, confirm
   macro-F1 ≥ 0.88, update F1 assertions + README, full pytest green.

## Guardrail compliance checklist (verified at implementation)
- [x] Taxonomy unchanged (5 labels) — themes mapped, not added.
- [x] macro-F1 ≥ 0.88 re-verified after #10 (holdout 0.896; CV 0.8785, see Requirements caveat).
- [x] `needs_review` threshold (0.55) untouched.
- [x] `extract.py` still offline / regex-first (no API calls).
- [x] Pydantic at all boundaries (enum on `ClaimNarrative`).
- [x] `/handoff` `RcaHandoff` contract byte-identical → QualityMind-RAG untouched (test enforces).
- [x] `models/anomaly_clf.joblib`, `data/claims.csv`, `metrics.json` not committed (confirmed gitignored).
- [x] New logic covered by offline unit tests; `ruff check` clean (58 tests pass).
- [x] No PII; synthetic data only; seed fixed.

## Implementation deviations from this plan
1. **Enum location:** `SourceType` placed in `claimlens/anomaly.py` (not a new
   `sources.py`) — beside the taxonomy constants, single import source.
2. **#10 `EDGE_TEMPLATES`:** the key-fob / USB / battery edge phrasing was split into a
   separate low-probability bank (`EDGE_RATE = 0.12`) instead of living inline in
   `TEMPLATES`. Reason: at equal weight the edge phrasing appeared ~1/3 of the time for
   its host class and blurred `connectivity_loss` ↔ `no_fault`, dropping holdout macro-F1
   to 0.84. Making edge cases genuinely rare both matches "edge case" semantics and
   restored the gate. `LABEL_WEIGHTS` softened (cloud 0.32) + `MIN_PER_CLASS=140` floor.
3. **Pre-existing test fix:** `test_classify.py` score-sum tolerance `1e-6 → 1e-3`
   (rounded 4-dp scores cannot sum to exactly 1.0; new model exposed it).
4. **Run note:** generator needs `PYTHONPATH=.` to import `claimlens.*`.

## Files touched (summary)
| File | #8 | #9 | #10 |
|---|---|---|---|
| `claimlens/anomaly.py` (or new `sources.py`) | enum | — | — |
| `claimlens/schema.py` | +source_type, +by_source | — | — |
| `claimlens/pipeline.py` | carry source_type | — | — |
| `claimlens/api.py` | populate source_type | — | — |
| `claimlens/extract.py` | per-stream emphasis | — | — |
| `claimlens/trends.py` | by_source Pareto | — | — |
| `evaluate.py` (+opt `eval_metrics.py`) | — | confusion matrix + recalls | re-verify |
| `data/generate_sample_data.py` | — | — | weighted + theme banks |
| `tests/*` | new + regression | helper test | distribution + F1 update |
