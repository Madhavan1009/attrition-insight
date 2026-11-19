"""Feature definitions shared by training (ml/train.py) and the API (app/model.py)."""

DEPARTMENTS = ["Engineering", "Sales", "Support", "Operations", "Finance", "HR"]

NUMERIC = [
    "age",
    "job_level",
    "years_at_company",
    "years_since_promotion",
    "distance_km",
    "job_satisfaction",
    "work_life_balance",
    "num_companies_worked",
]
INCOME = ["monthly_income"]          # log-scaled before the model sees it
CATEGORICAL = ["department", "overtime"]
FEATURES = NUMERIC + INCOME + CATEGORICAL
TARGET = "attrition"

LABELS = {
    "age": "Age",
    "job_level": "Job level",
    "monthly_income": "Monthly income",
    "years_at_company": "Years at company",
    "years_since_promotion": "Years since last promotion",
    "distance_km": "Distance from home",
    "job_satisfaction": "Job satisfaction",
    "work_life_balance": "Work-life balance",
    "num_companies_worked": "Companies worked before",
    "department": "Department",
    "overtime": "Works overtime",
}

SCALE_1_4 = {1: "Low", 2: "Medium", 3: "High", 4: "Very high"}


def value_text(feature, value):
    """Human-readable value for the drivers list and the AI prompt."""
    if feature == "monthly_income":
        return f"₹{int(value):,} / month"
    if feature == "distance_km":
        return f"{int(value)} km"
    if feature in ("job_satisfaction", "work_life_balance"):
        return f"{int(value)}/4 ({SCALE_1_4[int(value)]})"
    if feature in ("years_at_company", "years_since_promotion"):
        return f"{int(value)} yr" + ("" if int(value) == 1 else "s")
    if feature == "job_level":
        return f"Level {int(value)}"
    return str(value)
