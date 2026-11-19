"""Run with:  pip install -r requirements-dev.txt  then  pytest -q"""
import io
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import SAMPLES, app  # noqa: E402

client = TestClient(app)


def test_health():
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["model_version"] == "1.0"


def test_home_page():
    res = client.get("/")
    assert res.status_code == 200 and "Attrition Insight" in res.text


def test_predict_orders_samples():
    stable = client.post("/api/predict", json=SAMPLES["stable"]).json()
    at_risk = client.post("/api/predict", json=SAMPLES["at_risk"]).json()
    assert stable["band"] == "Low" and at_risk["band"] == "High"
    assert at_risk["probability"] > stable["probability"]
    assert at_risk["drivers"][0]["impact"] > 0


def test_predict_rejects_bad_input():
    bad = dict(SAMPLES["stable"], job_satisfaction=9)
    assert client.post("/api/predict", json=bad).status_code == 422


def test_explain_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pred = client.post("/api/predict", json=SAMPLES["at_risk"]).json()
    res = client.post("/api/explain", json={"employee": SAMPLES["at_risk"], "prediction": pred})
    assert res.status_code == 503


def test_batch_sample_csv():
    csv = (Path(__file__).resolve().parents[1] / "static" / "sample_team.csv").read_bytes()
    body = client.post("/api/predict-batch", files={"file": ("team.csv", io.BytesIO(csv), "text/csv")}).json()
    assert body["rows"] == 25 and sum(body["summary"].values()) == 25 and not body["errors"]


def test_batch_reports_bad_rows():
    csv = Path(__file__).resolve().parents[1] / "static" / "sample_team.csv"
    lines = csv.read_text().splitlines()
    lines[1] = lines[1].replace(",No,", ",Maybe,", 1)
    body = client.post("/api/predict-batch", files={"file": ("t.csv", "\n".join(lines).encode(), "text/csv")}).json()
    assert body["rows"] == 24 and body["errors"][0]["row"] == 2
