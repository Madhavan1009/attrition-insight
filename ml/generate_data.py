"""Create the synthetic employee dataset used to train the attrition model.

The data is synthetic (no real people). Each column follows a realistic range, and the
chance of leaving is driven by well-known attrition factors: overtime, low satisfaction,
poor work-life balance, pay below the level's normal range, long commutes, a long wait
since the last promotion and job hopping. Run from the project folder:

    python ml/generate_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROWS = 6000
SEED = 42
OUT = Path(__file__).resolve().parents[1] / "data" / "employees.csv"

DEPARTMENTS = ["Engineering", "Sales", "Support", "Operations", "Finance", "HR"]
DEPT_SHARE = [0.34, 0.20, 0.16, 0.14, 0.09, 0.07]
DEPT_EFFECT = {"Engineering": -0.10, "Sales": 0.35, "Support": 0.30, "Operations": 0.10, "Finance": -0.15, "HR": 0.0}
LEVEL_PAY = {1: 28000, 2: 45000, 3: 75000, 4: 120000, 5: 190000}  # typical monthly pay in INR


def main():
    rng = np.random.default_rng(SEED)
    age = np.clip(rng.normal(33, 7.5, ROWS).round(), 21, 60).astype(int)
    department = rng.choice(DEPARTMENTS, size=ROWS, p=DEPT_SHARE)

    level_raw = 1 + (age - 21) / 9 + rng.normal(0, 0.8, ROWS)
    job_level = np.clip(level_raw.round(), 1, 5).astype(int)

    typical_pay = np.array([LEVEL_PAY[level] for level in job_level])
    monthly_income = np.clip(typical_pay * rng.lognormal(0, 0.22, ROWS), 15000, 300000)
    monthly_income = (monthly_income / 500).round() * 500

    max_tenure = np.maximum(age - 21, 0)
    years_at_company = np.minimum(rng.gamma(2.0, 2.6, ROWS).round(), max_tenure).astype(int)
    years_since_promotion = np.minimum(rng.gamma(1.6, 1.5, ROWS).round(), years_at_company).astype(int)
    num_companies_worked = np.clip(rng.poisson(np.maximum(age - 22, 0) / 6), 0, 9).astype(int)

    overtime = (rng.random(ROWS) < 0.28).astype(int)
    distance_km = np.clip(rng.gamma(2.0, 5.5, ROWS).round(), 1, 60).astype(int)
    job_satisfaction = rng.choice([1, 2, 3, 4], size=ROWS, p=[0.18, 0.20, 0.31, 0.31])
    work_life_balance = rng.choice([1, 2, 3, 4], size=ROWS, p=[0.07, 0.23, 0.58, 0.12])

    logit = (
        -2.75
        + 1.60 * overtime
        + 0.62 * (2.6 - job_satisfaction)
        + 0.55 * (2.8 - work_life_balance)
        + 0.035 * (distance_km - 10)
        + 0.24 * (num_companies_worked - 2)
        + 0.13 * (years_since_promotion - 2)
        - 0.07 * (years_at_company - 5)
        - 0.040 * (age - 33)
        - 1.50 * np.log(monthly_income / typical_pay)
        + np.array([DEPT_EFFECT[d] for d in department])
        + rng.normal(0, 0.20, ROWS)
    )
    attrition = (rng.random(ROWS) < 1 / (1 + np.exp(-logit))).astype(int)

    df = pd.DataFrame({
        "employee_id": [f"PIB-E{1000 + i}" for i in range(ROWS)],
        "age": age,
        "department": department,
        "job_level": job_level,
        "monthly_income": monthly_income.astype(int),
        "years_at_company": years_at_company,
        "years_since_promotion": years_since_promotion,
        "overtime": np.where(overtime == 1, "Yes", "No"),
        "distance_km": distance_km,
        "job_satisfaction": job_satisfaction,
        "work_life_balance": work_life_balance,
        "num_companies_worked": num_companies_worked,
        "attrition": attrition,
    })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Saved {len(df)} rows to {OUT.relative_to(OUT.parents[1])} - attrition rate {df.attrition.mean():.1%}")


if __name__ == "__main__":
    main()
