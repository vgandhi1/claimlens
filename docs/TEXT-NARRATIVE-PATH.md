# Text / Narrative Path — Warranty Claims Intelligence

> **Vendored copy.** Canonical source lives at the Quality Engineering portfolio
> root (`quality-engineering/TEXT-NARRATIVE-PATH.md`). Synced into this standalone
> repo so CLaimLens is self-describing on GitHub. If the canonical doc changes,
> re-sync this copy. CLaimLens owns steps 1–3 of the path described below.

**Portfolio area:** Quality Engineering · TEXT / NARRATIVE PATH  
**Projects:** CLaimLens (this repo) → [QualityMind-RAG](https://github.com/vgandhi1/QualityMind-RAG)  
**Guardrails:** Quality Engineering AI Guardrails (`QUALITY-ENGG-GUARDRAILS.md`, portfolio-level — binding for all design and implementation)  
**Phase:** Dev / analytical models only — not production-ready  
**Last updated:** June 2026

---

## Purpose

Automotive warranty quality teams receive thousands of unstructured narratives from **customer complaints**, **dealer / service-center repair orders**, and **field-service tickets**. Today, turning that text into actionable plant and engineering insight is manual: spreadsheet searches, ad-hoc 5-Why meetings, and delayed PFMEA updates.

The **Text / Narrative Path** automates the front half of that loop:

1. **Ingest** many free-text claims and service logs in batch  
2. **Structure** each narrative (component, failure mode, anomaly class, confidence)  
3. **Aggregate** Pareto trends across the population  
4. **Escalate** the dominant issue into formal RCA (5-Why, Ishikawa, 8D, CAPA) backed by manufacturing documents and quality DB records  

CLaimLens owns steps 1–3. QualityMind-RAG owns step 4 and the closed loop back to plant/engineering artifacts.

---

## Industry context & related research

This section summarizes published industry reports and academic work that motivate the Text / Narrative Path. It is **not** proprietary OEM data — it synthesizes public research on how EV and connected-vehicle warranty teams struggle with the same unstructured narratives this path is designed to process.

### High-level narrative (what the literature describes)

Modern EV and software-defined vehicle (SDV) programs generate **three overlapping text streams** that quality teams must reconcile:

1. **Customer / owner complaints** — free-text portal submissions, NHTSA filings, and call-center transcripts describing symptoms in everyday language (“screen went blank,” “car won’t recognize key,” “update failed overnight”).
2. **Dealer / service repair orders (ROs)** — technician notes with semi-structured symptom–cause–resolution prose, often inconsistent across regions and analysts.
3. **Field / connected signals** — telematics DTCs, OTA update logs, cloud-sync timeouts, and watchdog resets that may appear **before** the customer opens a ticket.

Industry reports converge on a common pain pattern:

| Pain | What research & case studies report |
|------|-------------------------------------|
| **Volume & latency** | Warranty analysts spend **8–12 minutes per claim** manually interpreting free text and mapping to symptom/cause/part codes; coding varies by analyst and region ([Bruviti warranty claims coding case study](https://bruviti.com/use-cases/claims-coding)). |
| **Software & OTA as a new failure class** | OTA failures cluster around connectivity loss, low state-of-charge, ECU version mismatch, and user interruption during install — symptoms range from infotainment glitches to immobilization ([Virginia Tech OTA survey](https://vtechworks.lib.vt.edu/bitstreams/c79dd570-e74e-4c2f-97ee-815c7c46a40e/download); field TSB patterns on VW ID.x / Skoda Enyaq OTA failures). |
| **Infotainment as top IQS category** | Infotainment remains the **most problematic vehicle category** in J.D. Power IQS (42.6 PP100, 2025 U.S.); NEV-IQS China shows the same pattern (31 PP100) amid rapid tech churn ([J.D. Power 2025 U.S. IQS](https://www.businesswire.com/news/home/20250626729527/en/); [J.D. Power 2025 China NEV-IQS](https://china.jdpower.com/press-releases/2025-china-new-energy-vehicle-initial-quality-study-nev-iqs)). |
| **Connected data arrives before recalls** | Upstream analysis of **5,000+ U.S. recall campaigns** and **30,000+ NHTSA complaints (2020–2025)** finds **~70% of recalls** (and **~90% of EV-related recalls**) had detectable early warning signals in connected vehicle data — DTCs, voltage anomalies, thermal drift — yet OEMs still rely on fragmented, reactive investigation ([Upstream After-Sales Quality Report](https://upstream.auto/reports/after-sales-quality-report/); [Telematics Wire summary](https://telematicswire.net/upstream-report-reveals-70-of-us-recalls-could-have-been-detected-earlier-using-connected-vehicle-data/)). |
| **Vocabulary fragmentation blocks RCA** | The same physical failure is described differently in warranty MIS, PFMEA, factory defect logs, and QCR systems; investigations that require **manual correlation across two or more systems** are structurally slow ([ExLens automotive defect-ontology case study](https://exlens.ai/blog/case-study-resolving-the-quality-data-fragmentation-problem-in-high-complexity-automotive-manufacturing)). |
| **Battery warranty opacity** | Independent capacity measurement vs. BMS-reported State of Health (SOH) shows weak correlation; **93% of the worst-degraded vehicles** in one fleet audit were invisible to SOH-based warranty triggers — narrative complaints about “range loss” may not align with BMS thresholds ([arXiv: battery health reporting audit](https://arxiv.org/html/2603.21592)). |

**Representative complaint themes** (paraphrased composites from public filings and EV-owner studies — not real customer records):

> *“After the overnight software update, the center screen stays black; dealer says gateway ECU needs reprogramming. Car was charged above 50% on home Wi‑Fi.”*  
> → Maps to: **infotainment / OTA / cloud_sync** — candidate overcycle for handoff.

> *“Vehicle logged cloud sync timeout three mornings in a row; telematics portal shows repeated watchdog reset after ignition.”*  
> → Maps to: **telematics / soft_reset / cloud_sync** — batch Pareto driver.

> *“Customer reports immediate range drop after first drive; BMS shows 96% SOH but independent test suggests capacity loss.”*  
> → Maps to: **battery / powertrain** — likely **needs_review** (narrative vs. structured SOH disagreement).

These composites illustrate why the path needs **extract → classify → trend → human review → RCA**, not a single-shot LLM summary.

### Research & case studies (selected)

| Source | Method / focus | Relevance to this path |
|--------|----------------|------------------------|
| [NLP for automated vehicle diagnostics from free-text service reports (arXiv 2111.14977)](https://arxiv.org/abs/2111.14977) | Domain taxonomy + BiLSTM/CNN on call-center failure reports; validates vague claims, routes to service departments; **>18% accuracy gain** vs. technicians on validation | Validates CLaimLens **extract + classify + needs_review** on noisy customer language |
| [LLM + RAG fault retrieval for new energy vehicles (MDPI Appl. Sci. 2025)](https://www.mdpi.com/2076-3417/15/7/4034) | RAG + knowledge graph (122 fault categories); BERT for classification; ChatGLM for NER/relation extraction | Direct precedent for QualityMind **RAG + structured RCA** after CLaimLens structuring |
| [TOGG customer complaints via BERTopic (500k messages)](https://dergipark.org.tr/en/pub/vizyoner/article/1676415) | Topic modeling on EV OEM user messages; themes: **software errors, Android compatibility, delivery/logistics** | Supports **trends / Pareto** step; shows multilingual + multi-channel volume |
| [Electric car complaints BERTopic study (Ege Academic Review)](https://dergipark.org.tr/en/pub/eab/article/1668841) | One-year EV OEM complaint corpus; topic clustering for product/marketing insight | Same batch-trend use case as CLaimLens `/trends` |
| [Upstream After-Sales Quality Report 2020–2025](https://upstream.auto/reports/after-sales-quality-report/) | Recall + complaint linkage; connected-signal early detection | Motivates ingesting **field-service / telematics logs** alongside RO text |
| [AWS: Intelligent quality in the SDV era](https://aws.amazon.com/blogs/industries/driving-intelligent-quality-in-the-software-defined-vehicle-era/) | Fleet-wide behavioral monitoring; OTA log correlation; digital twin context for investigation | Aligns with **multi-source ingest** and proactive (not reactive) quality |
| [ExLens defect ontology case study](https://exlens.ai/blog/case-study-resolving-the-quality-data-fragmentation-problem-in-high-complexity-automotive-manufacturing) | Canonical “Cluster” linking warranty MIS ↔ PFMEA ↔ factory defects | QualityMind handoff goal: **one problem statement → PFMEA / NCR / CAPA citations** |
| [Logicline SDI — NLP warranty triage (machinery)](https://www.logicline.de/en/claims-and-warranty-in-machinery-triage) | NLP on technician notes + telemetry + service history; human-in-the-loop final decision | Mirrors **handoff/execute + human review** guardrails |
| [Bruviti — automated warranty claims coding](https://bruviti.com/use-cases/claims-coding) | Multi-label NLP: symptom, cause, part, resolution, severity; **75–85% auto-code** target | Industry benchmark for CLaimLens classification accuracy in dev eval |
| [Maintenance ticket NLP for RCA (HAL/Inria chapter)](https://inria.hal.science/hal-01666222) | Cluster + tag short maintenance texts for diagnosis frameworks | Academic basis for **batch clustering before 5-Why** |
| [J.D. Power 2025 U.S. IQS / China NEV-IQS](https://www.businesswire.com/news/home/20250626729527/en/) | VOC + repair data; infotainment dominant | Prioritizes **infotainment / HMI** labels in synthetic dev datasets |

### How this maps to CLaimLens → QualityMind

```text
Industry narrative streams          Text / Narrative Path step
─────────────────────────────       ───────────────────────────
Customer complaint (VOC)        →     CLaimLens POST /extract, /classify
Dealer RO / technician notes  →     CLaimLens batch + anomaly_label taxonomy
Telematics / OTA / field logs   →     CLaimLens trends (soft_reset, cloud_sync, …)
Pareto on dominant theme        →     CLaimLens POST /handoff
Cross-system RCA (PFMEA, 8D)    →     QualityMind /quality/five-why, fishbone, 8D, CAPA
Structured plant/engineering DB →     QualityMind RAG + Text-to-SQL
Low confidence / SOH mismatch   →     needs_review queue (human-in-the-loop)
```

**Dev implication:** Synthetic datasets in CLaimLens should **mirror published theme frequencies** (infotainment/OTA/cloud sync, battery range disputes, key-fob/USB edge cases) rather than generic “part failed” sentences — so `/trends` and handoff demos reflect realistic Pareto shapes from the literature above.

**Out of scope for TEXT path (documented elsewhere):** Vision/damage triage (AutoClaim-VLM), live fleet telematics ingestion pipelines, and production warranty ERP integration — see [QUALITY-ENGG-GUARDRAILS.md](QUALITY-ENGG-GUARDRAILS.md).

---

## Stakeholders & outcomes

| Role | Input they care about | Output they get |
|------|----------------------|-----------------|
| **Field quality engineer** | Warranty returns, dealer notes, telematics fault logs | Pareto by label / component / failure mode; overcycle share |
| **Manufacturing quality (plant)** | Recurring station or part failures | Evidence-linked 5-Why / fishbone pointing to process, tooling, or material causes |
| **Product / design engineering** | Component-level failure modes on connected ECU / telematics | 8D / CAPA drafts with PFMEA cross-references and NCR history |
| **Quality systems / QMS** | Audit trail for corrective action | Structured RCA JSON + citations to PFMEA, CAPA, control plans |

**Manufacturing plant insight** comes primarily from QualityMind-RAG correlating field narratives with PFMEA rows, control plans, SPC results, and NCR history — not from CLaimLens alone.

**Engineering insight** comes from the handoff problem statement plus RAG over DFMEA/PFMEA and structured defect/NCR queries.

---

## End-to-end flow (multi-claim batch)

```mermaid
flowchart TB
    subgraph sources [Data sources — dev: synthetic only]
        CC[Customer complaint text]
        SC[Service center RO / ticket notes]
        FS[Field-service / telematics logs]
    end

    subgraph claimlens [CLaimLens — narrative front end]
        IN[Batch ingest API]
        EX[extract.py — component / failure mode / part #]
        CL[classify.py — overcycle anomaly + needs_review]
        TR[trends.py — Pareto aggregation]
        HO[handoff.py — dominant trend payload]
    end

    subgraph qualitymind [QualityMind-RAG — RCA back end]
        FW[/quality/five-why]
        FB[/quality/fishbone]
        D8[/quality/draft-8d]
        CP[/quality/draft-capa]
        RAG[Document RAG — PFMEA / CAPA / 8D / QMS]
        SQL[Text-to-SQL — NCR / defects / SPC / CAPA status]
    end

    subgraph consumers [Review & action — human in the loop]
        REV[Quality engineer review]
        PLT[Plant corrective action]
        ENG[Engineering design change / PFMEA update]
    end

    CC --> IN
    SC --> IN
    FS --> IN
    IN --> EX --> CL --> TR
    TR --> REV
    TR --> HO
    HO --> FW
    HO --> D8
    FW --> RAG
    FW --> SQL
    D8 --> RAG
    CP --> RAG
    FB --> RAG
    FW --> REV
    D8 --> REV
    REV --> PLT
    REV --> ENG
```

### Per-narrative processing (CLaimLens)

Each record in a batch follows the same pipeline:

```
narrative text (+ optional claim_id, source_type)
    → extract_fields()     component, failure_mode, symptom, action_taken
    → AnomalyClassifier    label, confidence, is_overcycle, needs_review
    → AnalyzedClaim        single structured record
```

**Guardrail (CLaimLens):** Low confidence (`needs_review=true` when confidence < 0.55) must not be silently treated as ground truth — route to human review before RCA handoff.

### Batch aggregation (CLaimLens)

```
list[AnalyzedClaim]
    → build_trend_report()
        · by_label          (soft_reset, cloud_sync, …)
        · by_component      (Telematics Control Unit, Gateway, …)
        · by_failure_mode   (sync failure, spontaneous reboot, …)
        · overcycle_share   fraction of batch that is overcycle-class
```

Engineers use the Pareto view to answer: *“What is failing most often, on which component, and is it a firmware cycling issue vs hardware?”*

### RCA handoff (CLaimLens → QualityMind)

When overcycle anomalies dominate the batch, `build_handoff()` selects the top trend and emits an **`RcaHandoff`** contract:

| Field | Used by QualityMind for |
|-------|-------------------------|
| `problem_statement` | Seeds 5-Why chain and 8D D2 problem description |
| `component` | Descriptive name from extraction/trends — scopes RAG + agent context |
| `anomaly_label` | Traceability back to CLaimLens taxonomy |
| `claim_count`, `share` | Severity / priority context in RCA narrative |
| `target_endpoints` | `/quality/five-why`, `/quality/draft-8d` |

**Live integration (dev):** `POST /handoff/execute` on CLaimLens calls QualityMind `POST /quality/five-why` via `qualitymind_client.py` (SSRF allowlist per guardrails).

**Guardrail:** Handoff schema is a cross-project contract — changes require updating both repos simultaneously ([QUALITY-ENGG-GUARDRAILS.md § CLaimLens Handoff contract](QUALITY-ENGG-GUARDRAILS.md)).

---

## Mapping source types to the pipeline

| Source type | Typical narrative content | CLaimLens extraction targets | QualityMind follow-up |
|-------------|---------------------------|------------------------------|------------------------|
| **Customer complaint** | “Infotainment reboots every morning”, “OTA failed twice” | symptom, component, failure_mode | 5-Why on user-visible symptom; RAG over work instructions / known issues |
| **Service center RO / ticket** | “Replaced TCU-0420, NFF”, “Reflashed GW, sync restored” | action_taken, part_numbers, component | NCR history by part_number; CAPA status if repeat visits |
| **Field-service log** | “Watchdog reset after ignition”, “Cloud sync timeout ×3” | overcycle label (soft_reset, cloud_sync), failure_mode | Fishbone (6M) if process-related; SQL for defect counts by station/supplier |
| **Dealer warranty return** | Batch of similar narratives in one upload | Pareto `by_label` + `by_component` | Handoff on dominant overcycle trend |

### Batch sizing (dev recommendations)

| Endpoint | Purpose | Dev guidance |
|----------|---------|--------------|
| `POST /analyze` | Single narrative deep-dive | 1 record — debugging, spot check |
| `POST /trends` | Pareto over a claim population | 10–1,000 synthetic narratives per run |
| `POST /handoff` | Build RCA payload only | Same batch as `/trends`; requires ≥1 overcycle anomaly |
| `POST /handoff/execute` | Payload + call QualityMind | Same; QualityMind must be running locally |

Production batch caps and payload limits are deferred until analytical baselines are proven.

---

## How insights reach manufacturing plant vs engineering

### Manufacturing plant (process & line focus)

QualityMind-RAG supports plant-side questions once CLaimLens has identified *what* is failing:

| Question pattern | QualityMind route | Data sources |
|------------------|-------------------|--------------|
| “How many NCRs for part TCU-0420 in last 90 days?” | Text-to-SQL | `ncr`, `defects` tables |
| “What does PFMEA say about torque at Station 12?” | Document RAG + `/quality/pfmea-search` | PFMEA chunks (`doc_type=pfmea`) |
| “Is supplier X below quality rating threshold?” | Text-to-SQL | `suppliers` |
| “Cpk trend for characteristic Y on part Z?” | `/quality/spc-summary` + narrative | `inspection_results` |

**LangGraph agents** then combine retrieved evidence:

- **5-Why** — trace from field symptom (CLaimLens handoff) to plausible process root causes with `evidence_source` citations  
- **Fishbone (6M)** — structure brainstorming for shop-floor categories (Man, Machine, Method, Material, Measurement, Environment)  
- **CAPA / 8D drafts** — pre-populate corrective/preventive actions from CAPA logs and prior 8D reports  

**Plant action (human):** Review agent output + citations → work order, control plan revision, station audit, supplier SCAR. No automatic MES/ERP write in dev scope.

### Product / design engineering (component & system focus)

| Question pattern | QualityMind route | Engineering value |
|------------------|-------------------|-------------------|
| “Prior 8D reports on cloud sync failures for gateway?” | Document RAG | Avoid duplicate investigations |
| “DFMEA entries for connectivity module?” | RAG with `doc_type` filter | Design weakness identification |
| “Open CAPAs linked to this part?” | Text-to-SQL + `/quality/capa-status` | Backlog prioritization |
| “Draft 8D from CLaimLens handoff” | `/quality/draft-8d` | Accelerate formal report |

**Engineering action (human):** PFMEA/DFMEA update, firmware architecture change, design validation test plan, field fix campaign decision.

---

## Review workflow (human in the loop)

All AI outputs in this path require engineer review before plant or engineering action. Guardrails mandate validation before user-facing delivery.

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. INGEST BATCH    Service exports / warranty CSV → CLaimLens   │
│ 2. TRIAGE          Filter needs_review=true → manual queue       │
│ 3. PARETO REVIEW   Engineer confirms dominant trend is real      │
│ 4. HANDOFF         CLaimLens → QualityMind problem_statement   │
│ 5. RCA GENERATE    5-Why / 8D / fishbone with RAG + SQL evidence │
│ 6. STRUCTURE CHECK dev: structure_check on agent JSON (QM dev)  │
│ 7. ENGINEER SIGN-OFF  Citations verified; SQL approved if used   │
│ 8. ACTION          CAPA opened, PFMEA updated, bulletin issued   │
└─────────────────────────────────────────────────────────────────┘
```

| Step | Guardrail reference |
|------|---------------------|
| No real PII in dev corpus | Hard NO #1 — synthetic / anonymized only |
| SQL not auto-executed without review | QualityMind SQL HITL; `check_dangerous_sql()` |
| Agent JSON validated | `agent_validation.py`; dev `structure_check` on responses |
| Grounded citations | RAG must cite source chunks — no answer from weights alone |
| Handoff SSRF | `qualitymind_client.py` allowlisted base URL |

---

## Dev environment setup (local demo)

Per [QUALITY-ENGG-GUARDRAILS.md § Dev environment defaults](QUALITY-ENGG-GUARDRAILS.md): `ENVIRONMENT=development`, optional auth disabled locally.

### Terminal 1 — QualityMind-RAG

```bash
cd quality-engineering/QualityMind-RAG
cp .env.example .env          # OPENAI_API_KEY, PINECONE_API_KEY, DATABASE_URL
docker compose up -d          # Postgres + Redis for Text-to-SQL
uvicorn app.main:app --reload --port 8000
# Upload PFMEA / CAPA / 8D sample docs via POST /upload
```

### Terminal 2 — CLaimLens

```bash
cd quality-engineering/CLaimLens
python data/generate_sample_data.py
python evaluate.py              # models/anomaly_clf.joblib + metrics + manifest
uvicorn claimlens.api:app --reload --port 8001
export QUALITYMIND_BASE_URL=http://localhost:8000
```

### Example: multi-claim batch → insight → RCA seed

```bash
# 1) Pareto over a batch of service-center-style narratives
curl -s -X POST http://localhost:8001/trends \
  -H "Content-Type: application/json" \
  -d '[
    {"narrative": "TCU watchdog soft reset after ignition cycle", "claim_id": "WC-1001"},
    {"narrative": "Gateway fails cloud sync retries exhausted", "claim_id": "WC-1002"},
    {"narrative": "Soft reset again on telematics unit overnight", "claim_id": "WC-1003"},
    {"narrative": "No fault found bench test passed", "claim_id": "WC-1004"}
  ]' | jq .

# 2) Handoff dominant overcycle trend → QualityMind 5-Why
curl -s -X POST http://localhost:8001/handoff/execute \
  -H "Content-Type: application/json" \
  -d '[
    {"narrative": "TCU watchdog soft reset after ignition cycle"},
    {"narrative": "Soft reset again on telematics unit overnight"}
  ]' | jq .
```

Expected analytical outputs:

- **`/trends`:** `by_label` Pareto, `overcycle_share`, component/failure-mode breakdown  
- **`/handoff`:** `problem_statement`, `component`, `anomaly_label`, `claim_count`  
- **`/handoff/execute`:** above + QualityMind `five-why` analysis with `structure_check` in dev  

---

## Data model (conceptual — dev uses synthetic CSV)

CLaimLens dev corpus (`data/claims.csv`) columns map to production source fields:

| Dev column | Production analogue | Notes |
|------------|---------------------|-------|
| `narrative` | Complaint text + technician notes + DTC descriptions | Single concatenated text per claim |
| `label` | Human or verified ground truth (training only) | Not required at inference |
| `claim_id` | RO number / warranty claim ID | Use synthetic IDs in dev |
| `part_number` (API field) | ECU / module ID from BOM | Optional hint for extraction |

**Hard rule:** No real customer warranty records in repo, logs, or eval corpora until production data governance is defined.

---

## Analytical success criteria (text path only)

Before production, the narrative path should demonstrate in dev:

| Criterion | CLaimLens | QualityMind-RAG | Integration |
|-----------|-----------|-----------------|-------------|
| Batch Pareto reproducible | ✅ `evaluate.py` + `/trends` | — | — |
| Low-confidence flagged | ✅ `needs_review` | — | — |
| Handoff contract stable | ✅ `RcaHandoff` schema | ✅ consumes `problem_statement` | ✅ `/handoff/execute` |
| RCA grounded in evidence | — | ⏳ RAGAS baseline; citations on answers | ⏳ |
| Plant-relevant SQL answers | — | ⏳ Text-to-SQL on quality DB seed data | — |
| Engineer review loop documented | ✅ this doc | ✅ guardrails | — |

Track implementation status in the portfolio's Publisher → Subscriber simulation guide (Implementation review section).

---

## Planned extensions (not in scope yet)

These require explicit design + guardrail updates before implementation:

| Extension | Value | Dependencies |
|-----------|-------|--------------|
| **Scheduled batch ingest** | Nightly warranty CSV from service portal | Secure ingest pipeline; PII anonymization |
| **Multi-trend handoff queue** | Top-N Pareto items, not only #1 | QualityMind job queue; idempotent handoff |
| **Full handoff context to QualityMind** | Send `part_number`, `anomaly_label`, counts in POST body | Contract change both sides |
| **`/quality/draft-8d` execute** | Complete handoff targets both endpoints | Client + workflow orchestration |
| **Warehouse / dashboard** | Historical trend lines, recurrence detection | Postgres time-series; BI layer |
| **DistilBERT classifier** | Better messy field-note accuracy | Labeled pilot set (200–500 anonymized claims) |
| **PFMEA auto-update suggestions** | Close loop to manufacturing docs | Human approval + document versioning |

---

## Related documentation

| Document | Role |
|----------|------|
| [QUALITY-ENGG-GUARDRAILS.md](QUALITY-ENGG-GUARDRAILS.md) | Binding AI, security, and testing rules |
| [CLaimLens/README.md](CLaimLens/README.md) | NLP pipeline API reference |
| [QualityMind-RAG/README.md](QualityMind-RAG/README.md) | RAG, Text-to-SQL, LangGraph agent reference |

---

## Summary

The **Text / Narrative Path** turns high-volume automotive warranty text — customer complaints, service tickets, and field logs — into **structured, prioritized failure intelligence** (CLaimLens) and then into **evidence-backed RCA** that manufacturing and engineering teams can review and act on (QualityMind-RAG).  

CLaimLens answers *“what is failing, how often, and on which component?”* QualityMind answers *“why, according to our PFMEA/CAPA/NCR history, and what corrective action draft fits?”*  

Stay within [QUALITY-ENGG-GUARDRAILS.md](QUALITY-ENGG-GUARDRAILS.md): synthetic data in dev, human review before action, validated agent/VLM outputs, and a stable handoff contract between the two repos.
