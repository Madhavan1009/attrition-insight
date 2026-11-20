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


def _upload(csv_bytes):
    return client.post("/api/predict-batch", files={"file": ("team.csv", io.BytesIO(csv_bytes), "text/csv")}).json()


SAMPLE_CSV = Path(__file__).resolve().parents[1] / "static" / "sample_team.csv"


def test_storage_off_without_folder(monkeypatch, tmp_path):
    from app import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "not-mounted")
    assert client.get("/api/storage").json() == {"enabled": False, "files": []}
    body = _upload(SAMPLE_CSV.read_bytes())
    assert body["rows"] == 25 and body["storage"]["saved"] is False


def test_storage_saves_upload_and_scores(monkeypatch, tmp_path):
    from app import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    raw = SAMPLE_CSV.read_bytes()
    body = _upload(raw)
    original, scored = body["storage"]["files"]
    assert body["storage"]["saved"] is True
    assert (tmp_path / original).read_bytes() == raw
    lines = (tmp_path / scored).read_text().splitlines()
    assert lines[0] == "employee_id,department,risk_percent,band,top_driver" and len(lines) == 26
    listed = [f["name"] for f in client.get("/api/storage").json()["files"]]
    assert set(listed) == {original, scored}


def test_storage_failure_keeps_scoring(monkeypatch, tmp_path):
    from app import config

    def fail(*args, **kwargs):
        raise PermissionError("no permission")

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(type(tmp_path), "write_bytes", fail)   # the bucket refuses the write
    body = _upload(SAMPLE_CSV.read_bytes())
    assert body["rows"] == 25 and body["storage"]["saved"] is False
    assert "permission" in body["storage"]["message"]
