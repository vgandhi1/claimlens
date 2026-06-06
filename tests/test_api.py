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
