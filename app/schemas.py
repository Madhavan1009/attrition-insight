from typing import Literal

from pydantic import BaseModel, Field

Department = Literal["Engineering", "Sales", "Support", "Operations", "Finance", "HR"]


class Employee(BaseModel):
    age: int = Field(ge=18, le=65)
    department: Department
    job_level: int = Field(ge=1, le=5)
    monthly_income: int = Field(ge=10000, le=500000, description="Monthly income in INR")
    years_at_company: int = Field(ge=0, le=45)
    years_since_promotion: int = Field(ge=0, le=45)
    overtime: Literal["Yes", "No"]
    distance_km: int = Field(ge=0, le=200)
    job_satisfaction: int = Field(ge=1, le=4)
    work_life_balance: int = Field(ge=1, le=4)
    num_companies_worked: int = Field(ge=0, le=20)


class Driver(BaseModel):
    feature: str
    label: str
    value: str
    impact: float
    effect: str


class Prediction(BaseModel):
    probability: float
    risk_percent: int
    band: Literal["Low", "Medium", "High"]
    drivers: list[Driver]


class ExplainRequest(BaseModel):
    employee: Employee
    prediction: Prediction


class Explanation(BaseModel):
    summary: str
    actions: list[str]
    model: str
