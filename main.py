"""PROITBRIDGE Attrition Insight - FastAPI app (Cloud Run entrypoint: uvicorn main:app)."""
import io
import logging
import time

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app import ai, model, storage
from app.config import MAX_BATCH_ROWS, MAX_UPLOAD_BYTES, STATIC_DIR
from app.features import FEATURES
from app.schemas import Employee, ExplainRequest, Explanation, Prediction

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("attrition")

app = FastAPI(title="PROITBRIDGE Attrition Insight", version="1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

SAMPLES = {
    "stable": {"age": 36, "department": "Engineering", "job_level": 3, "monthly_income": 82000, "years_at_company": 6,
               "years_since_promotion": 1, "overtime": "No", "distance_km": 12, "job_satisfaction": 3,
               "work_life_balance": 3, "num_companies_worked": 2},
    "at_risk": {"age": 27, "department": "Sales", "job_level": 2, "monthly_income": 36000, "years_at_company": 2,
                "years_since_promotion": 2, "overtime": "Yes", "distance_km": 26, "job_satisfaction": 2,
                "work_life_balance": 2, "num_companies_worked": 3},
}

model.bundle()        # load the model at start-up, not on the first request
model.model_card()
if storage.enabled():
    log.info("storage on: team uploads are saved to %s", storage.config.DATA_DIR)
else:
    log.info("storage off: %s not found, team uploads are not saved", storage.config.DATA_DIR)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "model_version": model.model_card()["version"], "ai_enabled": ai.ai_enabled()}


@app.get("/api/model-card")
def model_card():
    return model.model_card()


@app.get("/api/storage")
def storage_status():
    return {"enabled": storage.enabled(), "files": storage.recent()}


@app.get("/api/samples")
def samples():
    return SAMPLES


@app.post("/api/predict", response_model=Prediction)
def predict(employee: Employee):
    started = time.perf_counter()
    result = model.predict([employee.model_dump()])[0]
    log.info("predict band=%s ms=%.0f", result["band"], (time.perf_counter() - started) * 1000)
    return result


@app.post("/api/explain", response_model=Explanation)
def explain(body: ExplainRequest):
    try:
        return ai.explain(body.employee.model_dump(), body.prediction.model_dump())
    except ai.AIUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error))
    except Exception as error:
        log.warning("explain failed: %s", type(error).__name__)
        raise HTTPException(status_code=502, detail="The AI summary could not be created. Please try again.")


@app.post("/api/predict-batch")
async def predict_batch(file: UploadFile = File(...)):
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The file is larger than 1 MB.")
    try:
        frame = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read the file. Upload a CSV file.")
    frame.columns = [c.strip() for c in frame.columns]
    missing = [f for f in FEATURES if f not in frame.columns]
    if missing:
        raise HTTPException(status_code=400, detail="Missing columns: " + ", ".join(missing))
    if len(frame) == 0:
        raise HTTPException(status_code=400, detail="The file has no rows.")
    if len(frame) > MAX_BATCH_ROWS:
        raise HTTPException(status_code=400, detail=f"Up to {MAX_BATCH_ROWS} rows per file.")

    valid, ids, errors = [], [], []
    for index, row in frame.iterrows():
        values = {f: row[f].strip() for f in FEATURES}
        try:
            valid.append(Employee(**values).model_dump())
            ids.append(row.get("employee_id", "").strip() or f"Row {index + 2}")
        except ValidationError as error:
            first = error.errors()[0]
            errors.append({"row": int(index) + 2, "message": f"{first['loc'][0]}: {first['msg']}"})

    results = model.predict(valid) if valid else []
    out = [{"employee_id": i, "department": e["department"], "risk_percent": r["risk_percent"], "band": r["band"],
            "top_driver": next((d["label"] for d in r["drivers"] if d["impact"] > 0), "-")}
           for i, e, r in zip(ids, valid, results)]
    out.sort(key=lambda r: r["risk_percent"], reverse=True)
    summary = {b: sum(1 for r in out if r["band"] == b) for b in ("High", "Medium", "Low")}
    saved = storage.save(raw, out) if out else {"saved": False, "files": [], "message": "No valid rows, so nothing was saved."}
    log.info("batch rows=%d errors=%d saved=%s", len(out), len(errors), saved["saved"])
    return {"rows": len(out), "summary": summary, "results": out, "errors": errors[:20], "storage": saved}
