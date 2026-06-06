<div align="center">

# 🔍 ClaimLens

### Warranty-Narrative NLP for Field Quality & Reliability RCA

*Turn free-text warranty claims and field notes into structured failure trends —
so the next 5-Why / 8D starts from data, not a spreadsheet search.*

### ▶ [**Live presentation**](https://vgandhi1.github.io/CLaimLens/presentation.html) · [GitHub](https://github.com/vgandhi1/CLaimLens)

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-TF--IDF%20%2B%20LogReg-F7931E?style=flat-square&logo=scikitlearn&logoColor=white)](https://scikit-learn.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Service-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-21%20passing-22C55E?style=flat-square)]()
[![Macro F1](https://img.shields.io/badge/macro%20F1-0.90-0EA5E9?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)

</div>

---

## What is ClaimLens?

In commercial-vehicle field quality, the slowest part of root-cause analysis is
reading thousands of free-text warranty claims, field-service narratives, and
equipment logs to figure out *what is actually failing and how often*. **ClaimLens**
is an NLP pipeline that does that triage automatically:

```
Free-text warranty claim ─┐
Field-service narrative  ─┼─► Extract (component / failure mode / symptom)
Equipment / fault log    ─┘        │
                                   ├─► Classify overcycle anomaly
                                   │     (Soft Reset · Cloud Sync · …)
                                   └─► Aggregate → Pareto failure trends
                                             │
                                             ▼
                                   feeds 5-Why / 8D RCA
                                   (see QualityMind-RAG)
```

It classifies each narrative into an **overcycle-anomaly** taxonomy — repeated
abnormal device-cycling events that inflate warranty returns — and separates
those from genuine hardware faults and no-fault-found returns. The structured
output rolls up into the Pareto view a field-quality engineer uses to pick which
issue to drive through formal RCA.

> **Companion project:** [QualityMind-RAG](https://github.com/vgandhi1/QualityMind-RAG)
> takes these failure trends into automated 5-Why / Ishikawa / 8D / CAPA workflows.
> ClaimLens is the *narrative → structured signal* front end; QualityMind is the
> *structured signal → corrective action* back end.

---

## Why it's data-first

Everything below is produced by `evaluate.py` on a stratified 75/25 split of
1,200 labeled narratives — **measured, not asserted**:

| Class | Precision | Recall | F1 |
|---|---|---|---|
| Soft Reset | 0.86 | 0.91 | 0.88 |
| Cloud Sync | 0.92 | 0.89 | 0.91 |
| Connectivity Loss | 0.91 | 0.96 | 0.94 |
| Power Cycle | 0.88 | 0.84 | 0.86 |
| No Fault Found | 0.92 | 0.91 | 0.91 |
| **macro avg** | **0.90** | **0.90** | **0.90** |

The synthetic corpus deliberately includes ~18% ambiguous / blended hard cases
so the score reflects real field-note messiness rather than a separable toy set.
Re-run it yourself:

```bash
python data/generate_sample_data.py     # writes data/claims.csv
python evaluate.py                       # trains + prints the table above
```

---

## Overcycle-anomaly taxonomy

| Label | Meaning | Overcycle? |
|---|---|---|
| `soft_reset` | Watchdog / firmware reboot, self-recovers, no power loss | ✅ |
| `cloud_sync` | Backend sync / OTA handshake failures | ✅ |
| `power_cycle` | Hard power loss → cold boot | ✅ |
| `connectivity_loss` | Cellular / network dropouts | — |
| `no_fault` | No fault found, within spec | — |

---

## Pipeline modules

| Module | Role |
|---|---|
| `claimlens/extract.py` | Rule-based extraction (regex + gazetteers): component, failure mode, symptom, action, part numbers — zero model download |
| `claimlens/classify.py` | `AnomalyClassifier` — TF-IDF (1–2 gram) + balanced Logistic Regression; train / predict / save / load; transformer-swappable |
| `claimlens/trends.py` | Pareto aggregation by label / component / failure mode + overcycle share |
| `claimlens/pipeline.py` | `analyze_one` / `analyze_batch` — narrative → classification + extraction |
| `claimlens/api.py` | FastAPI service (`/classify`, `/extract`, `/analyze`, `/trends`, `/handoff`, `/health`) |
| `claimlens/handoff.py` | Dominant overcycle trend → QualityMind-RAG-ready 5-Why / 8D `problem_statement` payload |
| `claimlens/schema.py` | Pydantic contracts for every input/output |
| `data/generate_sample_data.py` | PII-free synthetic labeled corpus |
| `evaluate.py` | Train + report real per-class P/R/F1 |

---

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) build the labeled corpus + train the model
python data/generate_sample_data.py
python evaluate.py                        # creates models/anomaly_clf.joblib

# 2) run the API
uvicorn claimlens.api:app --reload        # http://localhost:8000/docs
```

```bash
# classify a single field narrative
curl -X POST localhost:8000/classify \
  -H 'Content-Type: application/json' \
  -d '{"narrative": "TCU-0421 soft resets every ignition cycle, watchdog reboot, no power loss"}'
# -> {"label":"soft_reset","label_name":"Soft Reset","confidence":0.9x,"is_overcycle":true,...}

# full analysis (classification + structured extraction)
curl -X POST localhost:8000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"narrative": "Gateway GW-0097 fails to sync trip data to cloud after OTA. NFF."}'

# RCA hand-off: dominant overcycle trend -> QualityMind-ready 8D/5-Why payload
curl -X POST localhost:8000/handoff \
  -H 'Content-Type: application/json' \
  -d '[{"narrative":"TCU-0421 soft resets every ignition, watchdog reboot"},
       {"narrative":"TCU-0421 spontaneously reboots repeatedly, self-recovers"}]'
# -> {"problem_statement":"Recurring spontaneous reboot on Telematics Control Unit (Soft Reset) — 2 field claims, 100% of analyzed returns",
#     "part_number":"TCU-0421","anomaly_label":"soft_reset","target_endpoints":["/quality/five-why","/quality/draft-8d"]}
```

---

## Tests

```bash
pytest -q          # 21 tests: extraction, classifier, trends, handoff, schema, API
ruff check .
```

All tests run offline — the suite trains a small in-memory model from the
deterministic synthetic generator, so no saved model or network is required.

---

## Roadmap

- [x] Direct hand-off API into QualityMind-RAG 5-Why / 8D drafting (`/handoff`)
- [ ] DistilBERT classifier head (drop-in behind `AnomalyClassifier`)
- [ ] spaCy NER for finer component / part extraction
- [ ] Warehouse load (Postgres) for time-series recurrence + Weibull inputs
- [ ] Live POST from `/handoff` into a running QualityMind instance

---

## License

MIT — see [LICENSE](LICENSE).
