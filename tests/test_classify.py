from claimlens.anomaly import CLOUD_SYNC, NO_FAULT, SOFT_RESET
from claimlens.classify import AnomalyClassifier


def test_predicts_soft_reset(trained_classifier):
    res = trained_classifier.predict(
        "unit performs a soft reset repeatedly, watchdog reboot without power loss"
    )
    assert res.label == SOFT_RESET
    assert res.is_overcycle is True
    assert 0.0 <= res.confidence <= 1.0
    # scores are rounded to 4 dp for display, so allow rounding-scale slack.
    assert abs(sum(res.scores.values()) - 1.0) < 1e-3


def test_predicts_cloud_sync(trained_classifier):
    res = trained_classifier.predict(
        "gateway fails to sync trip data to cloud backend, sync retries exhausted"
    )
    assert res.label == CLOUD_SYNC
    assert res.is_overcycle is True


def test_no_fault_is_not_overcycle(trained_classifier):
    res = trained_classifier.predict(
        "bench test passed, no fault found, unit operates normally"
    )
    assert res.label == NO_FAULT
    assert res.is_overcycle is False


def test_predict_before_fit_raises():
    with __import__("pytest").raises(RuntimeError):
        AnomalyClassifier().predict("anything")


def test_save_and_load_roundtrip(trained_classifier, tmp_path):
    p = tmp_path / "clf.joblib"
    trained_classifier.save(p)
    loaded = AnomalyClassifier.load(p)
    text = "device power cycles every ignition, cold boot restart"
    assert loaded.predict(text).label == trained_classifier.predict(text).label
