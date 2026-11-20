"""Loads the trained model once and turns its output into a risk score with explained drivers."""
import json
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from app.config import MODEL_CARD_PATH, MODEL_PATH
from app.features import FEATURES, LABELS, value_text

# job level and income work together (pay below the level's normal range raises risk),
# so we show them as one driver
GROUP = {"job_level": "pay", "monthly_income": "pay"}
GROUP_LABEL = {"pay": "Pay for the job level"}


@lru_cache
def bundle():
    return joblib.load(MODEL_PATH)


@lru_cache
def model_card():
    return json.loads(MODEL_CARD_PATH.read_text(encoding="utf-8"))


@lru_cache
def _columns():
    """Original feature name for every column the model sees after preprocessing."""
    names = bundle()["pipeline"].named_steps["pre"].get_feature_names_out()
    out = []
    for name in names:
        raw = name.split("__", 1)[1]
        out.append(next(f for f in FEATURES if raw == f or raw.startswith(f + "_")))
    return out


def band(probability):
    bands = bundle()["bands"]
    if probability >= bands["high_from"]:
        return "High"
    if probability >= bands["medium_from"]:
        return "Medium"
    return "Low"


def _drivers(frame):
    """Per-employee contribution of each feature, compared with the average employee."""
    pipe = bundle()["pipeline"]
    z = pipe.named_steps["pre"].transform(frame)
    contrib = (z - bundle()["baseline"]) * pipe.named_steps["clf"].coef_[0]
    cols = _columns()
    results = []
    for row_index in range(len(frame)):
        totals = {}
        for col_index, feature in enumerate(cols):
            key = GROUP.get(feature, feature)
            totals[key] = totals.get(key, 0.0) + float(contrib[row_index, col_index])
        row = frame.iloc[row_index]
        drivers = []
        for key, impact in totals.items():
            if key == "pay":
                label = GROUP_LABEL[key]
                text = f"{value_text('monthly_income', row['monthly_income'])} at {value_text('job_level', row['job_level'])}"
            else:
                label = LABELS[key]
                text = value_text(key, row[key])
            drivers.append({"feature": key, "label": label, "value": text, "impact": round(impact, 3),
                            "effect": "raises risk" if impact > 0 else "lowers risk"})
        drivers.sort(key=lambda d: abs(d["impact"]), reverse=True)
        results.append(drivers)
    return results


def predict(rows):
    """rows: list of dicts with the FEATURES keys. Returns one result per row."""
    frame = pd.DataFrame(rows)[FEATURES]
    probabilities = bundle()["pipeline"].predict_proba(frame)[:, 1]
    drivers = _drivers(frame)
    out = []
    for p, d in zip(probabilities, drivers):
        percent = int(np.rint(p * 100))
        # band from the shown percent, so "40%" is always High (40% and above), never Medium
        out.append({"probability": round(float(p), 4), "risk_percent": percent, "band": band(percent / 100), "drivers": d})
    return out
