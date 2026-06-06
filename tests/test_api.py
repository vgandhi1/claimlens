from fastapi.testclient import TestClient

import claimlens.api as api_module
from claimlens.api import app


def setup_module(_):
    """Inject a trained classifier so endpoints don't need a saved model file."""
    from claimlens.classify import AnomalyClassifier
    from data.generate_sample_data import generate

    rows = generate(n=400, seed=7)
    clf = AnomalyClassifier().fit(
        [r["narrative"] for r in rows], [r["label"] for r in rows]
    )
    api_module._classifier = clf


def teardown_module(_):
    api_module._classifier = None


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_classify_endpoint():
    r = client.post("/classify", json={"narrative": "soft reset repeatedly, watchdog reboot"})
    assert r.status_code == 200
    body = r.json()
    assert body["label"] == "soft_reset"
    assert body["is_overcycle"] is True


def test_analyze_endpoint_returns_extraction():
    r = client.post("/analyze", json={
        "narrative": "TCU-0420 fails to sync to cloud after update",
        "claim_id": "WC-1",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["classification"]["label"] == "cloud_sync"
    assert body["extracted"]["component"] == "Telematics Control Unit"


def test_extract_endpoint():
    r = client.post("/extract", json={
        "narrative": "gateway fails to sync",
        "part_number": "GW-0099",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["component"] == "Connectivity Gateway"
    assert "GW-0099" in body["part_numbers"]


def test_trends_endpoint():
    payload = [
        {"narrative": "soft reset repeatedly watchdog reboot"},
        {"narrative": "gateway fails to sync to cloud retries exhausted"},
        {"narrative": "no fault found, bench test passed"},
    ]
    r = client.post("/trends", json=payload)
    assert r.status_code == 200
    assert r.json()["total_claims"] == 3


def test_trends_rejects_empty():
    assert client.post("/trends", json=[]).status_code == 400


def test_handoff_returns_payload():
    payload = [
        {"narrative": "soft reset repeatedly watchdog reboot"},
        {"narrative": "soft reset again after ignition cycle"},
    ]
    r = client.post("/handoff", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["anomaly_label"] == "soft_reset"
    assert "/quality/five-why" in body["target_endpoints"]


def test_handoff_no_overcycle_returns_404():
    payload = [{"narrative": "no fault found, bench test passed"}]
    assert client.post("/handoff", json=payload).status_code == 404


def test_model_missing_returns_503(monkeypatch):
    from pathlib import Path

    import claimlens.config as config_module

    api_module._classifier = None
    monkeypatch.setattr(config_module, "MODEL_PATH", Path("models/does_not_exist.joblib"))
    monkeypatch.setattr(api_module, "MODEL_PATH", Path("models/does_not_exist.joblib"))
    r = client.post("/classify", json={"narrative": "soft reset repeatedly"})
    assert r.status_code == 503


def test_handoff_execute_requires_qualitymind_url(monkeypatch):
    monkeypatch.setattr("claimlens.config.QUALITYMIND_BASE_URL", "")
    payload = [{"narrative": "soft reset repeatedly watchdog reboot"}]
    r = client.post("/handoff/execute", json=payload)
    assert r.status_code == 502
